import weaviate
from weaviate.embedded import EmbeddedOptions
import numpy as np
from typing import List, Dict, Optional
import os
from datetime import datetime
import requests
from app.utils.uuid_helpers import format_uuid_for_weaviate

class WeaviateRAGService:
    def __init__(self, persistence_dir: str = "./weaviate-data", use_embedded: bool = True):
        """Initialize Weaviate RAG service"""
        print(f"\n[DEBUG] Initializing WeaviateRAGService:")
        print(f"[DEBUG] Persistence dir: {persistence_dir}")
        print(f"[DEBUG] Using embedded mode: {use_embedded}")
        
        if use_embedded:
            print("[DEBUG] Setting up embedded Weaviate client...")
            self.client = weaviate.Client(
                embedded_options=EmbeddedOptions(
                    persistence_data_path=persistence_dir,
                    additional_env_vars={
                        "AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED": "true",
                        "PERSISTENCE_DATA_PATH": persistence_dir,
                        "DEFAULT_VECTORIZER_MODULE": "none",  # We'll handle vectorization ourselves
                        "ENABLE_MODULES": "",  # Disable all modules since we'll do vectorization
                        "DISK_USE_WARNING_PERCENTAGE": "95",  # Increase disk usage threshold
                        "DISK_USE_READONLY_PERCENTAGE": "98"  # Increase readonly threshold
                    }
                )
            )
            print("[DEBUG] Embedded client setup complete")
        else:
            # Default to localhost if not using embedded
            weaviate_url = os.getenv("WEAVIATE_URL", "http://localhost:8080")
            print(f"[DEBUG] Setting up external Weaviate client at {weaviate_url}")
            self.client = weaviate.Client(url=weaviate_url)
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
        """Ensure the required schema exists in Weaviate"""
        # Log schema
        log_schema = {
            "class": self.log_class,
            "vectorizer": "none",  # We'll handle vectorization ourselves
            "properties": [
                {
                    "name": "content",
                    "dataType": ["text"],
                },
                {
                    "name": "tags",
                    "dataType": ["string[]"],
                }
            ]
        }

        # Query schema
        query_schema = {
            "class": self.query_class,
            "vectorizer": "none",
            "properties": [
                {
                    "name": "query_text",
                    "dataType": ["text"],
                },
                {
                    "name": "created_at",
                    "dataType": ["date"],
                },
                {
                    "name": "result_count",
                    "dataType": ["int"],
                },
                {
                    "name": "execution_time",
                    "dataType": ["number"],
                },
                {
                    "name": "sql_id",  # Reference to SQL database ID
                    "dataType": ["string"],
                }
            ]
        }

        # Check and create schemas
        for schema in [log_schema, query_schema]:
            class_name = schema["class"]
            try:
                print(f"[DEBUG] Checking if schema exists for class: {class_name}")
                existing_schema = self.client.schema.get(class_name)
                print(f"[DEBUG] Schema exists for {class_name}")
                if self.debug:
                    print(f"[DEBUG] Existing schema: {existing_schema}")
            except weaviate.exceptions.UnexpectedStatusCodeException as e:
                print(f"[DEBUG] Schema not found for {class_name}, creating...")
                try:
                    self.client.schema.create_class(schema)
                    print(f"[DEBUG] Successfully created schema for {class_name}")
                except Exception as create_e:
                    print(f"[ERROR] Failed to create schema for {class_name}:")
                    print(f"Error type: {type(create_e).__name__}")
                    print(f"Error message: {str(create_e)}")
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

    def add_query(self, query_text: str, sql_id: str, result_count: int, execution_time: float) -> str:
        """Add a query to Weaviate with its embedding"""
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
            return result
        except Exception as e:
            print(f"[ERROR] Failed to add query to Weaviate: {e}")
            return None

    def get_similar_queries(self, query_text: str, limit: int = 5, min_certainty: float = 0.7) -> List[Dict]:
        """Find similar previous queries"""
        try:
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
                .with_limit(limit)
                .do()
            )

            if result and "data" in result and "Get" in result["data"]:
                objects = result["data"]["Get"][self.query_class]
                print(f"\n[DEBUG] Raw objects from Weaviate: {objects}")  # Debug the raw objects
                return [{
                    "query_text": obj["query_text"],
                    "result_count": obj["result_count"],
                    "created_at": obj["created_at"],
                    "sql_id": obj["sql_id"],
                    "execution_time": obj.get("execution_time"),
                    "relevance_score": obj["_additional"]["certainty"]
                } for obj in objects]
            return []
        except Exception as e:
            print(f"Error finding similar queries: {e}")
            return []

    def get_query_suggestions(self, partial_query: str, limit: int = 5) -> List[Dict]:
        """Get query suggestions based on partial input"""
        try:
            # Convert partial query to lowercase for case-insensitive matching
            partial_lower = partial_query.lower()
            
            # First get all queries
            result = (
                self.client.query
                .get(self.query_class, [
                    "query_text",
                    "result_count",
                    "created_at",
                    "sql_id",
                    "execution_time"
                ])
                .do()
            )

            if result and "data" in result and "Get" in result["data"]:
                objects = result["data"]["Get"][self.query_class]
                
                # Filter and sort matches manually
                matches = []
                for obj in objects:
                    query_text = obj["query_text"].lower()
                    if query_text.startswith(partial_lower):
                        matches.append({
                            "query_text": obj["query_text"],  # Keep original case
                            "result_count": obj["result_count"],
                            "created_at": obj["created_at"],
                            "sql_id": obj["sql_id"],
                            "execution_time": obj.get("execution_time")
                        })
                
                # Sort by length (shorter matches first) and limit results
                matches.sort(key=lambda x: len(x["query_text"]))
                return matches[:limit]
            
            return []
        except Exception as e:
            print(f"Error getting query suggestions: {e}")
            return [] 