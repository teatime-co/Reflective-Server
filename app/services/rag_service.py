from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Tuple
import pickle
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.models import Log, Query, QueryResult

class RAGService:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.embedding_version = "v1.0.0"  # Update this when changing embedding models
        self.chunk_size = 500  # words per chunk

    def _get_embedding(self, text: str) -> bytes:
        """Generate embedding for text and return as bytes"""
        embedding = self.model.encode([text])[0]
        return pickle.dumps(embedding)

    def _bytes_to_array(self, embedding_bytes: bytes) -> np.ndarray:
        """Convert embedding bytes back to numpy array"""
        return pickle.loads(embedding_bytes)

    def process_log(self, db: Session, log: Log) -> bool:
        """Process a log entry to generate and store its embedding"""
        try:
            # Generate embedding for the content
            embedding = self._get_embedding(log.content)
            
            # Update log with embedding and metadata
            log.embedding = embedding
            log.embedding_version = self.embedding_version
            log.word_count = len(log.content.split())
            log.processing_status = "processed"
            
            db.commit()
            return True
        except Exception as e:
            print(f"Error processing log {log.id}: {str(e)}")
            log.processing_status = "failed"
            db.commit()
            return False

    def semantic_search(self, db: Session, query_text: str, top_k: int = 5) -> List[QueryResult]:
        """Perform semantic search on logs"""
        start_time = datetime.utcnow()
        
        # Create query record
        query = Query(
            query_text=query_text,
            embedding=self._get_embedding(query_text)
        )
        db.add(query)
        
        # Get all processed logs with embeddings
        logs = db.query(Log).filter(
            Log.embedding.isnot(None),
            Log.processing_status == "processed"
        ).all()
        
        if not logs:
            query.result_count = 0
            query.execution_time = (datetime.utcnow() - start_time).total_seconds()
            db.commit()
            return []
        
        # Convert query embedding to numpy array
        query_embedding = self._bytes_to_array(query.embedding)
        
        # Calculate similarities and get top results
        results = []
        for log in logs:
            log_embedding = self._bytes_to_array(log.embedding)
            similarity = np.dot(query_embedding, log_embedding)
            results.append((log, similarity))
        
        # Sort by similarity and take top_k
        results.sort(key=lambda x: x[1], reverse=True)
        top_results = results[:top_k]
        
        # Create QueryResult records
        query_results = []
        for rank, (log, similarity) in enumerate(top_results):
            # Create snippet from log content
            content = log.content
            # Simple snippet creation - could be more sophisticated
            snippet_start = max(0, len(content) // 2 - 100)
            snippet_end = min(len(content), len(content) // 2 + 100)
            snippet = content[snippet_start:snippet_end]
            
            result = QueryResult(
                query=query,
                log=log,
                relevance_score=float(similarity),
                snippet_text=snippet,
                snippet_start_index=snippet_start,
                snippet_end_index=snippet_end,
                rank=rank
            )
            db.add(result)
            query_results.append(result)
        
        # Update query metadata
        query.result_count = len(query_results)
        query.execution_time = (datetime.utcnow() - start_time).total_seconds()
        
        db.commit()
        return query_results

    def process_pending_logs(self, db: Session) -> Tuple[int, int]:
        """Process all pending logs"""
        pending_logs = db.query(Log).filter(
            Log.processing_status.in_(["pending", None])
        ).all()
        
        success_count = 0
        fail_count = 0
        
        for log in pending_logs:
            if self.process_log(db, log):
                success_count += 1
            else:
                fail_count += 1
        
        return success_count, fail_count 