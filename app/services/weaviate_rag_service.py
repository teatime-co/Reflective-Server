import weaviate
from weaviate.embedded import EmbeddedOptions
import numpy as np
from typing import List, Dict, Optional
import os
from datetime import datetime
import requests

class WeaviateRAGService:
    def __init__(self, persistence_dir: str = "./weaviate-data", use_embedded: bool = True):
        """Initialize Weaviate RAG service
        
        Args:
            persistence_dir: Directory for storing Weaviate data in embedded mode
            use_embedded: Whether to use embedded mode (True) or connect to external Weaviate (False)
        """
        if use_embedded:
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
        else:
            # Default to localhost if not using embedded
            weaviate_url = os.getenv("WEAVIATE_URL", "http://localhost:8080")
            self.client = weaviate.Client(url=weaviate_url)
            
        self.class_name = "Log"
        self._ensure_schema()

    def _get_embeddings(self, text: str) -> List[float]:
        """Get embeddings from Ollama API"""
        response = requests.post(
            "http://localhost:11434/api/embeddings",
            json={
                "model": "snowflake-arctic-embed2",
                "prompt": text
            }
        )
        if response.status_code == 200:
            return response.json()["embedding"]
        else:
            raise Exception(f"Failed to get embeddings: {response.text}")

    def _ensure_schema(self):
        """Ensure the required schema exists in Weaviate"""
        schema = {
            "class": self.class_name,
            "vectorizer": "none",  # We'll handle vectorization ourselves
            "properties": [
                {
                    "name": "content",
                    "dataType": ["text"],
                },
                {
                    "name": "tags",
                    "dataType": ["string[]"],  # Explicitly using string[] for array of strings
                }
            ]
        }

        # Check if schema exists
        try:
            self.client.schema.get(self.class_name)
        except weaviate.exceptions.UnexpectedStatusCodeException:
            # Create schema if it doesn't exist
            self.client.schema.create_class(schema)

    def add_log(self, content: str, tags: List[str] = None) -> str:
        """Add a log entry to Weaviate"""
        # Get embeddings from Ollama
        vector = self._get_embeddings(content)
        
        # Prepare data object with only essential fields
        data_object = {
            "content": content,
            "tags": tags or []
        }

        # Add to Weaviate with vector
        try:
            result = self.client.data_object.create(
                data_object=data_object,
                class_name=self.class_name,
                vector=vector  # Pass the vector explicitly
            )
            return result
        except Exception as e:
            print(f"Error adding log to Weaviate: {e}")
            return None

    def semantic_search(self, query: str, limit: int = 5) -> List[Dict]:
        """Perform semantic search on logs"""
        try:
            # Get query vector from Ollama
            query_vector = self._get_embeddings(query)
            
            result = (
                self.client.query
                .get(self.class_name, ["content", "tags"])
                .with_additional(["id", "certainty"])
                .with_near_vector({
                    "vector": query_vector,
                    "certainty": 0.7  # Minimum similarity threshold
                })
                .with_limit(limit)
                .do()
            )

            # Extract and format results
            if result and "data" in result and "Get" in result["data"]:
                objects = result["data"]["Get"][self.class_name]
                
                # Deduplicate results by ID
                seen_ids = set()
                unique_objects = []
                for obj in objects:
                    obj_id = obj["_additional"]["id"]
                    if obj_id not in seen_ids:
                        seen_ids.add(obj_id)
                        unique_objects.append(obj)
                
                return [{
                    "content": obj["content"],
                    "tags": obj.get("tags", []),
                    "id": obj["_additional"]["id"],
                    "relevance_score": obj["_additional"]["certainty"]
                } for obj in unique_objects]
            return []
        except Exception as e:
            print(f"Error in semantic search: {e}")
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
                class_name=self.class_name,
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
                class_name=self.class_name
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
                .get(self.class_name, ["content", "tags"])
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
                self.class_name in result["data"]["Get"] and
                result["data"]["Get"][self.class_name] is not None):
                
                objects = result["data"]["Get"][self.class_name]
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