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
                    "name": "created_at",
                    "dataType": ["date"],
                },
                {
                    "name": "updated_at",
                    "dataType": ["date"],
                },
                {
                    "name": "word_count",
                    "dataType": ["int"],
                },
                {
                    "name": "processing_status",
                    "dataType": ["string"],
                },
                {
                    "name": "tags",
                    "dataType": ["string[]"],
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
        
        # Use datetime's built-in ISO format (RFC3339 compatible)
        now = datetime.utcnow().isoformat() + "Z"
        
        # Prepare data object
        data_object = {
            "content": content,
            "created_at": now,
            "updated_at": now,
            "word_count": len(content.split()),
            "processing_status": "processed",
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
                .get(self.class_name, ["content", "tags", "created_at", "_additional {certainty}"])
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
                return [{
                    "content": obj["content"],
                    "tags": obj.get("tags", []),
                    "created_at": obj["created_at"],
                    "relevance_score": obj["_additional"]["certainty"]
                } for obj in objects]
            return []
        except Exception as e:
            print(f"Error in semantic search: {e}")
            return []

    def update_log(self, log_id: str, content: str, tags: List[str] = None) -> bool:
        """Update a log entry in Weaviate"""
        # Get new embeddings from Ollama
        vector = self._get_embeddings(content)
        
        # Use datetime's built-in ISO format (RFC3339 compatible)
        now = datetime.utcnow().isoformat() + "Z"
        
        # Prepare update object
        data_object = {
            "content": content,
            "updated_at": now,
            "word_count": len(content.split()),
            "processing_status": "processed"
        }
        if tags is not None:
            data_object["tags"] = tags

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
        result = (
            self.client.query
            .get(self.class_name, ["content", "tags", "created_at"])
            .with_where({
                "path": ["tags"],
                "operator": "ContainsAny",
                "valueString": tag
            })
            .with_limit(limit)
            .do()
        )

        if result and "data" in result and "Get" in result["data"]:
            return result["data"]["Get"][self.class_name]
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