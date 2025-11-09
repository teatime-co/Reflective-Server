from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from typing import List
import time
import traceback

from app.database import get_db
from app.models.models import Log, Query as QueryModel, QueryResult as QueryResultModel, log_theme_association
from app.services.weaviate_rag_service import WeaviateRAGService
from app.schemas.query import SearchResult, QueryWithScore, SearchRequest
from app.api.auth import get_current_user
from app.schemas.user import UserResponse
from datetime import datetime

router = APIRouter(prefix="/search", tags=["search"])
rag_service = WeaviateRAGService()

@router.post("", response_model=List[SearchResult], status_code=status.HTTP_200_OK)
async def semantic_search(
    request: SearchRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Perform semantic search on logs and return full log details with search metadata"""
    start_time = time.time()

    try:
        query = request.query
        top_k = request.top_k

        print(f"[DEBUG] Creating new query record for: {query}")
        query_record = QueryModel(
            user_id=current_user.id,
            query_text=query,
            created_at=datetime.utcnow()
        )
        db.add(query_record)

        print(f"[DEBUG] Performing semantic search with top_k={top_k}")
        search_results = rag_service.semantic_search(query, top_k)
        print(f"[DEBUG] Got {len(search_results) if search_results else 0} results from Weaviate")
        if search_results:
            print(f"[DEBUG] First result structure: {search_results[0]}")

        weaviate_ids = [result["id"] for result in search_results]
        print(f"[DEBUG] Looking up logs with Weaviate IDs: {weaviate_ids}")
        logs = db.query(Log).options(
            joinedload(Log.tags),
            joinedload(Log.themes),
            joinedload(Log.linguistic_metrics),
            joinedload(Log.revisions)
        ).filter(
            Log.weaviate_id.in_(weaviate_ids),
            Log.user_id == current_user.id  # Filter by user_id
        ).all()
        print(f"[DEBUG] Found {len(logs)} matching logs in SQL database")
        log_map = {log.weaviate_id: log for log in logs}

        combined_results = []
        for rank, result in enumerate(search_results, 1):  # Start rank at 1
            log = log_map.get(result["id"])
            if not log:
                print(f"[WARN] No SQL log found for Weaviate ID: {result['id']}")
                continue

            print(f"[DEBUG] Processing result {rank} with Weaviate ID: {result['id']}")
            search_metadata = {
                "relevance_score": result.get("relevance_score", 0.0),
                "snippet_text": result.get("snippet_text", ""),
                "snippet_start_index": result.get("snippet_start_index", 0),
                "snippet_end_index": result.get("snippet_end_index", 0),
                "context_before": result.get("context_before"),
                "context_after": result.get("context_after"),
                "rank": rank
            }

            try:
                db.add(QueryResultModel(
                    query=query_record,
                    log=log,
                    **search_metadata
                ))

                print(f"[DEBUG] Creating SearchResult for log ID: {log.id}")
                log_dict = log.__dict__.copy()
                log_dict.pop('_sa_instance_state', None)

                log_dict['tags'] = [
                    {
                        "id": tag.id,
                        "name": tag.name,
                        "color": tag.color,
                        "created_at": tag.created_at
                    } for tag in log.tags
                ]

                theme_data = []
                if log.themes:
                    theme_associations = db.query(log_theme_association).filter(
                        log_theme_association.c.log_id == log.id
                    ).all()

                    association_map = {
                        assoc.theme_id: {
                            "confidence_score": assoc.confidence_score,
                            "detected_at": assoc.detected_at
                        } for assoc in theme_associations
                    }

                    for theme in log.themes:
                        theme_info = {
                            "id": theme.id,
                            "name": theme.name,
                            "description": theme.description,
                            "confidence_threshold": theme.confidence_threshold,
                            "created_at": theme.created_at,
                            "updated_at": theme.updated_at
                        }

                        if theme.id in association_map:
                            theme_info.update(association_map[theme.id])
                        else:
                            theme_info["confidence_score"] = 0.0
                            theme_info["detected_at"] = theme.created_at

                        theme_data.append(theme_info)

                log_dict['themes'] = theme_data

                metrics = log.linguistic_metrics
                log_dict['linguistic_metrics'] = {
                    "id": metrics.id,
                    "log_id": metrics.log_id,
                    "vocabulary_diversity_score": metrics.vocabulary_diversity_score,
                    "sentiment_score": metrics.sentiment_score,
                    "complexity_score": metrics.complexity_score,
                    "readability_level": metrics.readability_level,
                    "emotion_scores": metrics.emotion_scores,
                    "writing_style_metrics": metrics.writing_style_metrics,
                    "processed_at": metrics.processed_at
                } if metrics else None

                log_dict['revisions'] = [
                    {
                        "id": rev.id,
                        "log_id": rev.log_id,
                        "revision_number": rev.revision_number,
                        "content_delta": rev.content_delta,
                        "revision_type": rev.revision_type,
                        "created_at": rev.created_at
                    } for rev in log.revisions
                ] if log.revisions else []

                response_obj = SearchResult(
                    **log_dict,
                    **search_metadata
                )
                combined_results.append(response_obj)
            except Exception as inner_e:
                print(f"[ERROR] Failed to process result {rank}:")
                print(f"Log data: {log.__dict__}")
                print(f"Search metadata: {search_metadata}")
                print(f"Error: {str(inner_e)}")
                traceback.print_exc()
                continue

        execution_time = time.time() - start_time
        result_count = len(combined_results)

        query_record.execution_time = execution_time
        query_record.result_count = result_count

        db.commit()

        print(f"[DEBUG] Storing/checking query in Weaviate with ID: {query_record.id}")
        weaviate_id = rag_service.add_query(
            query_text=query,
            sql_id=str(query_record.id),
            result_count=result_count,
            execution_time=execution_time
        )

        if weaviate_id:
            print(f"[DEBUG] Query stored in Weaviate with ID: {weaviate_id}")
        else:
            print(f"[WARN] Failed to store query in Weaviate")

        return combined_results

    except Exception as e:
        print(f"[ERROR] Semantic search failed:")
        print(f"Query: {query}")
        print(f"Error: {str(e)}")
        print("Traceback:")
        traceback.print_exc()
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}\n{traceback.format_exc()}")

@router.get("/similar", response_model=List[QueryWithScore], status_code=status.HTTP_200_OK)
async def get_similar_queries(
    query: str = Query(..., min_length=1),
    limit: int = Query(default=5, ge=1, le=20),
    min_certainty: float = Query(default=0.7, ge=0.0, le=1.0),
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get similar previous queries"""
    try:
        similar_queries = rag_service.get_similar_queries(query, limit, min_certainty)

        return [
            QueryWithScore(
                id=q["sql_id"],
                query_text=q["query_text"],
                created_at=q["created_at"],
                result_count=q["result_count"],
                relevance_score=q["relevance_score"]
            ) for q in similar_queries
            if db.query(QueryModel).filter(
                QueryModel.id == q["sql_id"],
                QueryModel.user_id == current_user.id
            ).first()
        ]
    except ValueError as e:
        print(f"[ERROR] Failed to convert UUID: {e}")
        raise HTTPException(status_code=500, detail=f"Invalid UUID format: {str(e)}")
    except Exception as e:
        print(f"[ERROR] Failed to get similar queries: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get similar queries: {str(e)}")

@router.get("/suggest", response_model=List[QueryWithScore], status_code=status.HTTP_200_OK)
async def get_query_suggestions(
    partial_query: str = Query(..., min_length=1),
    limit: int = Query(default=5, ge=1, le=20),
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get query suggestions based on partial input"""
    try:
        suggestions = rag_service.get_query_suggestions(partial_query, limit)

        return [
            QueryWithScore(
                id=q["sql_id"],
                query_text=q["query_text"],
                created_at=q["created_at"],
                result_count=q["result_count"]
            ) for q in suggestions
            if db.query(QueryModel).filter(
                QueryModel.id == q["sql_id"],
                QueryModel.user_id == current_user.id
            ).first()
        ]
    except ValueError as e:
        print(f"[ERROR] Failed to convert UUID: {e}")
        raise HTTPException(status_code=500, detail=f"Invalid UUID format: {str(e)}")
    except Exception as e:
        print(f"[ERROR] Failed to get query suggestions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get query suggestions: {str(e)}")
