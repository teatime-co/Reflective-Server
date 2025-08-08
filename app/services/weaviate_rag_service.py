import weaviate
from weaviate.embedded import EmbeddedOptions
import numpy as np
from typing import List, Dict, Optional
import os
from datetime import datetime
import requests
from app.utils.uuid_utils import format_uuid_for_weaviate

class WeaviateRAGService:
    def __init__(self, persistence_dir: str = "./weaviate-data", use_embedded: bool = True):
        """Initialize Weaviate RAG service"""
        print(f"\n[DEBUG] Initializing WeaviateRAGService:")
        print(f"[DEBUG] Persistence dir: {persistence_dir}")
        print(f"[DEBUG] Using embedded mode: {use_embedded}")
        
        if use_embedded:
            print("[DEBUG] Setting up embedded Weaviate client...")
            embedded_options = EmbeddedOptions(
                persistence_data_path=persistence_dir,
                additional_env_vars={
                    "AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED": "true",
                    "PERSISTENCE_DATA_PATH": persistence_dir,
                    "DEFAULT_VECTORIZER_MODULE": "none",
                    "ENABLE_MODULES": "",
                    "DISK_USE_WARNING_PERCENTAGE": "95",
                    "DISK_USE_READONLY_PERCENTAGE": "98",
                    # Explicitly disable all modules
                    "TRANSFORMERS_INFERENCE_API": "",
                    "OPENAI_APIKEY": "",
                    "COHERE_APIKEY": "",
                    "AZURE_APIKEY": "",
                    "PALM_APIKEY": "",
                    "HUGGINGFACE_APIKEY": "",
                    "CONTEXTIONARY_URL": "",
                    "QNA_INFERENCE_API": "",
                    "NER_INFERENCE_API": "",
                    "SPELLCHECK_INFERENCE_API": "",
                    "SUM_INFERENCE_API": "",
                    "TEXT_INFERENCE_API": "",
                    "IMAGE_INFERENCE_API": "",
                    "AUDIO_INFERENCE_API": "",
                    "MULTI2VEC_BIND_INFERENCE_API": "",
                    "MULTI2VEC_CLIP_INFERENCE_API": "",
                    "MULTI2VEC_PALM_INFERENCE_API": "",
                    "RERANKER_INFERENCE_API": "",
                    "GENERATIVE_COHERE_INFERENCE_API": "",
                    "GENERATIVE_OPENAI_INFERENCE_API": "",
                    "GENERATIVE_PALM_INFERENCE_API": "",
                    "GENERATIVE_AWS_INFERENCE_API": ""
                }
            )
            
            self.client = weaviate.Client(
                embedded_options=embedded_options
            )
            print("[DEBUG] Embedded client setup complete")
        else:
            # Default to localhost if not using embedded
            weaviate_url = os.getenv("WEAVIATE_URL", "http://localhost:8080")
            print(f"[DEBUG] Setting up external Weaviate client at {weaviate_url}")
            self.client = weaviate.Client(
                url=weaviate_url,
                additional_headers={
                    "X-OpenAI-Api-Key": "",  # Explicitly set to empty to disable OpenAI
                    "X-Cohere-Api-Key": "",   # Explicitly set to empty to disable Cohere
                }
            )
            print("[DEBUG] External client setup complete")
            
        self.log_class = "Log"
        self.query_class = "Query"
        self.debug = True  # Enable debug logging
        
        print("[DEBUG] Ensuring schema exists...")
        self._ensure_schema()
        print("[DEBUG] Initialization complete")

    def _get_embeddings(self, text: str) -> List[float]:
        """Get embeddings from Ollama API"""
        if self.debug:
            print(f"\n[DEBUG] Getting embeddings for text: {text[:100]}...")
        
        response = requests.post(
            "http://localhost:11434/api/embeddings",
            json={
                "model": "snowflake-arctic-embed2",
                "prompt": text
            }
        )
        if response.status_code == 200:
            embedding = response.json()["embedding"]
            if self.debug:
                print(f"[DEBUG] Embedding generated successfully. Dimension: {len(embedding)}")
                print(f"[DEBUG] First 5 values: {embedding[:5]}")
            return embedding
        else:
            print(f"[ERROR] Failed to get embeddings. Status: {response.status_code}")
            print(f"[ERROR] Response: {response.text}")
            raise Exception(f"Failed to get embeddings: {response.text}")

    def _ensure_schema(self):
        """Ensure the required schema exists in Weaviate without unnecessary deletion"""
        # Log schema
        log_schema = {
            "class": self.log_class,
            "description": "A log entry with content and tags",
            "vectorIndexConfig": {
                "distance": "cosine"
            },
            "vectorizer": "none",
            "properties": [
                {
                    "name": "content",
                    "dataType": ["text"],
                    "description": "The main content of the log entry"
                },
                {
                    "name": "tags",
                    "dataType": ["string[]"],
                    "description": "Tags associated with the log entry"
                }
            ]
        }

        # Query schema
        query_schema = {
            "class": self.query_class,
            "description": "A search query with metadata",
            "vectorIndexConfig": {
                "distance": "cosine"
            },
            "vectorizer": "none",
            "properties": [
                {
                    "name": "query_text",
                    "dataType": ["text"],
                    "description": "The search query text"
                },
                {
                    "name": "created_at",
                    "dataType": ["date"],
                    "description": "When the query was made"
                },
                {
                    "name": "result_count",
                    "dataType": ["int"],
                    "description": "Number of results returned"
                },
                {
                    "name": "execution_time",
                    "dataType": ["number"],
                    "description": "Time taken to execute the query"
                },
                {
                    "name": "sql_id",
                    "dataType": ["string"],
                    "description": "Reference to SQL database ID"
                }
            ]
        }

        # Check and create schemas only if they don't exist
        for schema in [log_schema, query_schema]:
            class_name = schema["class"]
            try:
                print(f"[DEBUG] Checking if schema exists for class: {class_name}")
                # Try to get the schema first
                try:
                    existing_schema = self.client.schema.get(class_name)
                    print(f"[DEBUG] Schema already exists for {class_name}")
                    if self.debug:
                        print(f"[DEBUG] Existing schema: {existing_schema}")
                    
                    # Validate that existing schema has required properties
                    existing_props = {prop['name'] for prop in existing_schema.get('properties', [])}
                    required_props = {prop['name'] for prop in schema['properties']}
                    
                    if required_props.issubset(existing_props):
                        print(f"[DEBUG] Schema for {class_name} is valid, skipping recreation")
                        continue
                    else:
                        print(f"[DEBUG] Schema for {class_name} is missing properties, will recreate")
                        print(f"[DEBUG] Missing: {required_props - existing_props}")
                        # Delete and recreate if schema is incomplete
                        self.client.schema.delete_class(class_name)
                        
                except weaviate.exceptions.UnexpectedStatusCodeException:
                    print(f"[DEBUG] No existing schema found for {class_name}")
                
                # Create new schema
                print(f"[DEBUG] Creating schema for {class_name}")
                self.client.schema.create_class(schema)
                print(f"[DEBUG] Successfully created schema for {class_name}")
                
            except Exception as e:
                print(f"[ERROR] Failed to handle schema for {class_name}:")
                print(f"Error type: {type(e).__name__}")
                print(f"Error message: {str(e)}")
                import traceback
                traceback.print_exc()
                raise

    def add_log(self, content: str, tags: List[str] = None) -> str:
        """Add a log entry to Weaviate"""
        if self.debug:
            print(f"\n[DEBUG] Adding log to Weaviate:")
            print(f"Content: {content[:100]}...")
            print(f"Tags: {tags}")
        
        # Get embeddings from Ollama
        try:
            print("[DEBUG] Getting embeddings from Ollama...")
            vector = self._get_embeddings(content)
            print(f"[DEBUG] Got embedding vector of length: {len(vector)}")
        except Exception as e:
            print(f"[ERROR] Failed to generate embeddings:")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            import traceback
            print("Traceback:")
            traceback.print_exc()
            return None
        
        # Prepare data object with only essential fields
        data_object = {
            "content": content,
            "tags": tags or []
        }

        # Add to Weaviate with vector
        try:
            print("[DEBUG] Attempting to create object in Weaviate...")
            print(f"[DEBUG] Data object: {data_object}")
            print(f"[DEBUG] Vector length: {len(vector)}")
            result = self.client.data_object.create(
                data_object=data_object,
                class_name=self.log_class,
                vector=vector
            )
            if self.debug:
                print(f"[DEBUG] Successfully added log to Weaviate with ID: {result}")
                try:
                    # Verify the log was stored
                    stored_obj = self.client.data_object.get_by_id(result, self.log_class, ["content", "tags"])
                    print(f"[DEBUG] Verified stored log:")
                    print(f"Stored content: {stored_obj['properties']['content'][:100]}...")
                    print(f"Stored tags: {stored_obj['properties'].get('tags', [])}")
                except Exception as verify_e:
                    print(f"[WARN] Could not verify stored object: {str(verify_e)}")
            return result
        except Exception as e:
            print(f"[ERROR] Failed to add log to Weaviate:")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            import traceback
            print("Traceback:")
            traceback.print_exc()
            return None

    def semantic_search(self, query: str, limit: int = 5) -> List[Dict]:
        """Perform semantic search on logs"""
        if self.debug:
            print(f"\n[DEBUG] Performing semantic search:")
            print(f"Query: {query}")
            print(f"Limit: {limit}")
        
        try:
            # Get query vector from Ollama
            query_vector = self._get_embeddings(query)
            print(f"[DEBUG] Generated query vector of length: {len(query_vector)}")
            
            # Perform hybrid search combining vector and text search
            result = (
                self.client.query
                .get(self.log_class, ["content", "tags"])
                .with_additional(["id", "certainty", "vector"])
                .with_near_vector({
                    "vector": query_vector,
                    "certainty": 0.5  # Lower threshold to catch more semantic matches
                })
                .with_limit(limit * 2)  # Get more results initially to filter
                .do()
            )

            print(f"\n[DEBUG] Raw search result: {result}")

            # Extract and format results
            if result and "data" in result and "Get" in result["data"]:
                objects = result["data"]["Get"][self.log_class]
                if self.debug:
                    print(f"\n[DEBUG] Search results:")
                    print(f"Found {len(objects)} results")
                    for idx, obj in enumerate(objects):
                        print(f"\nResult {idx + 1}:")
                        print(f"Content: {obj['content'][:100]}...")
                        print(f"Tags: {obj.get('tags', [])}")
                        print(f"Certainty: {obj['_additional']['certainty']:.4f}")
                
                # Process results with improved snippet creation
                formatted_results = []
                for obj in objects:
                    content = obj["content"]
                    
                    # Find the most relevant section based on query terms
                    query_terms = set(query.lower().split())
                    best_snippet_score = 0
                    best_snippet = ""
                    best_start = 0
                    best_end = 0
                    
                    # Split content into sentences or chunks
                    chunks = [s.strip() for s in content.split('.') if s.strip()]
                    window_size = 3  # Number of sentences to include in snippet
                    
                    for i in range(len(chunks) - window_size + 1):
                        window = '. '.join(chunks[i:i + window_size])
                        window_lower = window.lower()
                        
                        # Score this window based on query term matches
                        score = sum(1 for term in query_terms if term in window_lower)
                        
                        if score > best_snippet_score:
                            best_snippet_score = score
                            best_snippet = window
                            best_start = len('. '.join(chunks[:i]))
                            best_end = len('. '.join(chunks[:i + window_size]))
                    
                    # If no good snippet found, fall back to middle of content
                    if not best_snippet:
                        best_start = max(0, len(content) // 2 - 100)
                        best_end = min(len(content), len(content) // 2 + 100)
                        best_snippet = content[best_start:best_end]
                    
                    formatted_results.append({
                        "content": content,
                        "tags": obj.get("tags", []),
                        "id": obj["_additional"]["id"],
                        "relevance_score": float(obj["_additional"]["certainty"]),
                        "snippet_text": best_snippet,
                        "snippet_start_index": best_start,
                        "snippet_end_index": best_end
                    })
                
                # Sort by relevance score and limit results
                formatted_results.sort(key=lambda x: x["relevance_score"], reverse=True)
                return formatted_results[:limit]
            
            if self.debug:
                print("[DEBUG] No results found in semantic search")
            return []
            
        except Exception as e:
            print(f"[ERROR] Semantic search failed: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def update_log(self, log_id: str, content: str, tags: List[str] = None) -> bool:
        """Update a log entry in Weaviate"""
        # Get new embeddings from Ollama
        vector = self._get_embeddings(content)
        
        # Prepare update object with only essential fields
        data_object = {
            "content": content,
            "tags": tags if tags is not None else []
        }

        try:
            self.client.data_object.update(
                uuid=log_id,
                data_object=data_object,
                class_name=self.log_class,
                vector=vector  # Pass the vector explicitly
            )
            return True
        except Exception as e:
            print(f"Error updating log in Weaviate: {e}")
            return False

    def delete_log(self, log_id: str) -> bool:
        """Delete a log entry from Weaviate"""
        try:
            self.client.data_object.delete(
                uuid=log_id,
                class_name=self.log_class
            )
            return True
        except Exception as e:
            print(f"Error deleting log from Weaviate: {e}")
            return False

    def get_logs_by_tag(self, tag: str, limit: int = 100) -> List[Dict]:
        """Get logs with specific tag"""
        try:
            print(f"Searching for tag: {tag}")  # Debug log
            result = (
                self.client.query
                .get(self.log_class, ["content", "tags"])
                .with_additional(["id"])
                .with_where({
                    "path": ["tags"],
                    "operator": "ContainsAny",
                    "valueStringArray": [tag]
                })
                .with_limit(limit)
                .do()
            )

            print(f"Raw result: {result}")  # Debug log

            if (result and 
                isinstance(result, dict) and 
                "data" in result and 
                "Get" in result["data"] and 
                self.log_class in result["data"]["Get"] and
                result["data"]["Get"][self.log_class] is not None):
                
                objects = result["data"]["Get"][self.log_class]
                print(f"Found {len(objects)} objects with tag {tag}")  # Debug log
                return [{
                    "content": obj["content"],
                    "tags": obj.get("tags", []),
                    "id": obj["_additional"]["id"]
                } for obj in objects]
            
            print(f"No results found for tag {tag}")  # Debug log
            return []
            
        except Exception as e:
            print(f"Error in get_logs_by_tag: {str(e)}")
            return []

    def batch_add_logs(self, logs: List[Dict[str, any]]) -> List[str]:
        """Batch add multiple logs to Weaviate"""
        results = []
        for log in logs:
            content = log["content"]
            tags = log.get("tags", [])
            result = self.add_log(content, tags)
            if result:
                results.append(result)
        return results 

    def find_existing_query(self, query_text: str) -> Optional[Dict]:
        """Find an existing query with the exact same text"""
        try:
            if self.debug:
                print(f"\n[DEBUG] Checking for existing query: {query_text}")
            
            result = (
                self.client.query
                .get(self.query_class, [
                    "query_text",
                    "created_at",
                    "result_count",
                    "execution_time",
                    "sql_id"
                ])
                .with_additional(["id"])
                .with_where({
                    "path": ["query_text"],
                    "operator": "Equal",
                    "valueText": query_text
                })
                .with_limit(1)
                .do()
            )

            if result and "data" in result and "Get" in result["data"]:
                objects = result["data"]["Get"].get(self.query_class, [])
                if objects:
                    existing_query = objects[0]
                    if self.debug:
                        print(f"[DEBUG] Found existing query with ID: {existing_query['_additional']['id']}")
                        print(f"[DEBUG] SQL ID: {existing_query.get('sql_id')}")
                    return {
                        "weaviate_id": existing_query["_additional"]["id"],
                        "query_text": existing_query["query_text"],
                        "created_at": existing_query["created_at"],
                        "result_count": existing_query["result_count"],
                        "execution_time": existing_query.get("execution_time"),
                        "sql_id": existing_query["sql_id"]
                    }
            
            if self.debug:
                print("[DEBUG] No existing query found")
            return None
            
        except Exception as e:
            print(f"[ERROR] Error finding existing query: {e}")
            import traceback
            traceback.print_exc()
            return None

    def update_query_metadata(self, weaviate_id: str, result_count: int, execution_time: float) -> bool:
        """Update metadata for an existing query"""
        try:
            if self.debug:
                print(f"[DEBUG] Updating query metadata for Weaviate ID: {weaviate_id}")
                print(f"[DEBUG] New result count: {result_count}, execution time: {execution_time}")
            
            # Get current query data
            current_data = self.client.data_object.get_by_id(
                weaviate_id, 
                class_name=self.query_class,
                with_vector=False
            )
            
            if not current_data:
                print(f"[ERROR] Query with ID {weaviate_id} not found")
                return False
            
            # Update with new metadata while preserving other fields
            updated_data = {
                "query_text": current_data["properties"]["query_text"],
                "created_at": current_data["properties"]["created_at"],
                "sql_id": current_data["properties"]["sql_id"],
                "result_count": result_count,
                "execution_time": execution_time
            }
            
            # Get current vector to preserve it
            vector = self._get_embeddings(current_data["properties"]["query_text"])
            
            self.client.data_object.update(
                uuid=weaviate_id,
                data_object=updated_data,
                class_name=self.query_class,
                vector=vector
            )
            
            if self.debug:
                print(f"[DEBUG] Successfully updated query metadata")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to update query metadata: {e}")
            import traceback
            traceback.print_exc()
            return False

    def add_query(self, query_text: str, sql_id: str, result_count: int, execution_time: float, update_if_exists: bool = True) -> str:
        """Add a query to Weaviate with its embedding (always create new, no duplicate checking)"""
        
        # Always create new query entry
        if self.debug:
            print(f"[DEBUG] Creating new query entry for: {query_text}")
        
        vector = self._get_embeddings(query_text)
        
        # Format datetime in RFC3339 format without microseconds
        created_at = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        
        data_object = {
            "query_text": query_text,
            "created_at": created_at,
            "result_count": result_count,
            "execution_time": execution_time,
            "sql_id": str(sql_id)  # Store UUID as string
        }

        try:
            if self.debug:
                print(f"[DEBUG] Adding query to Weaviate:")
                print(f"Query text: {query_text}")
                print(f"Created at: {created_at}")
                print(f"SQL ID: {sql_id}")
            
            result = self.client.data_object.create(
                data_object=data_object,
                class_name=self.query_class,
                vector=vector
            )
            if self.debug:
                print(f"[DEBUG] Successfully created new query with Weaviate ID: {result}")
            return result
        except Exception as e:
            print(f"[ERROR] Failed to add query to Weaviate: {e}")
            return None

    def get_similar_queries(self, query_text: str, limit: int = 5, min_certainty: float = 0.7) -> List[Dict]:
        """Find similar previous queries"""
        try:
            if self.debug:
                print(f"\n[DEBUG] Finding similar queries for: {query_text}")
                print(f"Limit: {limit}, Min certainty: {min_certainty}")
            
            query_vector = self._get_embeddings(query_text)
            
            result = (
                self.client.query
                .get(self.query_class, [
                    "query_text",
                    "result_count",
                    "created_at",
                    "sql_id",
                    "execution_time"
                ])
                .with_additional(["id", "certainty"])
                .with_near_vector({
                    "vector": query_vector,
                    "certainty": min_certainty
                })
                .with_limit(limit * 2)  # Get more results to ensure we have enough after filtering
                .do()
            )

            if result and "data" in result and "Get" in result["data"]:
                objects = result["data"]["Get"][self.query_class]
                if self.debug:
                    print(f"[DEBUG] Found {len(objects)} potential matches")
                
                # Process and filter results
                processed_results = []
                for obj in objects:
                    certainty = obj["_additional"]["certainty"]
                    if certainty >= min_certainty:
                        processed_results.append({
                            "query_text": obj["query_text"],
                            "result_count": obj["result_count"],
                            "created_at": obj["created_at"],
                            "sql_id": obj["sql_id"],
                            "execution_time": obj.get("execution_time"),
                            "relevance_score": certainty
                        })
                
                # Sort by relevance score and limit results
                processed_results.sort(key=lambda x: x["relevance_score"], reverse=True)
                return processed_results[:limit]
            
            if self.debug:
                print("[DEBUG] No similar queries found")
            return []
        except Exception as e:
            print(f"[ERROR] Error finding similar queries: {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_query_suggestions(self, partial_query: str, limit: int = 5) -> List[Dict]:
        """Get query suggestions based on partial input"""
        try:
            if self.debug:
                print(f"\n[DEBUG] Getting suggestions for partial query: {partial_query}")
            
            # Convert partial query to lowercase for case-insensitive matching
            partial_lower = partial_query.lower()
            
            # Use vector search to find semantically similar queries
            query_vector = self._get_embeddings(partial_lower)
            
            result = (
                self.client.query
                .get(self.query_class, [
                    "query_text",
                    "result_count",
                    "created_at",
                    "sql_id",
                    "execution_time"
                ])
                .with_additional(["id", "certainty"])
                .with_near_vector({
                    "vector": query_vector,
                    "certainty": 0.5  # Lower threshold for suggestions
                })
                .with_limit(limit * 3)  # Get more results to filter
                .do()
            )

            if result and "data" in result and "Get" in result["data"]:
                objects = result["data"]["Get"][self.query_class]
                if self.debug:
                    print(f"[DEBUG] Found {len(objects)} potential suggestions")
                
                # Process and filter matches
                matches = []
                seen_queries = set()  # To avoid duplicates
                
                for obj in objects:
                    query_text = obj["query_text"]
                    query_lower = query_text.lower()
                    
                    # Check if this query starts with the partial input
                    # or contains all words from the partial input
                    partial_words = set(partial_lower.split())
                    query_words = set(query_lower.split())
                    
                    if (query_lower.startswith(partial_lower) or 
                        partial_words.issubset(query_words)):
                        
                        # Avoid duplicates
                        if query_lower not in seen_queries:
                            seen_queries.add(query_lower)
                            matches.append({
                                "query_text": query_text,  # Keep original case
                                "result_count": obj["result_count"],
                                "created_at": obj["created_at"],
                                "sql_id": obj["sql_id"],
                                "execution_time": obj.get("execution_time")
                            })
                
                # Sort suggestions:
                # 1. Exact prefix matches first
                # 2. Then by length (shorter matches first)
                # 3. Then by result count (more results first)
                matches.sort(key=lambda x: (
                    not x["query_text"].lower().startswith(partial_lower),
                    len(x["query_text"]),
                    -x["result_count"]
                ))
                
                if self.debug:
                    print(f"[DEBUG] Returning {min(len(matches), limit)} suggestions")
                return matches[:limit]
            
            if self.debug:
                print("[DEBUG] No suggestions found")
            return []
        except Exception as e:
            print(f"[ERROR] Error getting query suggestions: {e}")
            import traceback
            traceback.print_exc()
            return [] 