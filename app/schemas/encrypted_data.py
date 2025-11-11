"""
Encrypted Data Schemas

Pydantic models for encrypted data transmission between client and server.
Supports homomorphic encryption (HE) and AES-256 encryption.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Optional, Literal, Any
from datetime import datetime


class EncryptedMetric(BaseModel):
    """Single encrypted metric (HE-encrypted)"""
    metric_type: str = Field(..., description="Type of metric (word_count, sentiment, duration, etc.)")
    encrypted_value: str = Field(..., description="Base64-encoded CKKS encrypted value")
    timestamp: datetime = Field(..., description="When the metric was recorded")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "metric_type": "word_count",
            "encrypted_value": "AQAAAAAA...base64...",
            "timestamp": "2025-11-09T10:30:00Z"
        }
    })


class EncryptedMetricBatch(BaseModel):
    """Batch of encrypted metrics from client"""
    user_id: Optional[str] = Field(None, description="User ID (auto-populated from JWT)")
    metrics: list[EncryptedMetric] = Field(..., description="List of encrypted metrics")
    context_params: Optional[Dict[str, Any]] = Field(None, description="HE context parameters (optional)")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "metrics": [
                {
                    "metric_type": "word_count",
                    "encrypted_value": "AQAAAAAA...",
                    "timestamp": "2025-11-09T10:30:00Z"
                }
            ]
        }
    })


class AggregateRequest(BaseModel):
    """Request to aggregate encrypted metrics"""
    metric_type: str = Field(..., description="Type of metric to aggregate")
    operation: Literal["sum", "average"] = Field(..., description="Aggregation operation")
    time_range: Optional[Dict[str, datetime]] = Field(None, description="Optional time range filter")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "metric_type": "word_count",
            "operation": "sum",
            "time_range": {
                "start": "2025-11-01T00:00:00Z",
                "end": "2025-11-09T23:59:59Z"
            }
        }
    })


class AggregateResult(BaseModel):
    """Result of aggregation on encrypted metrics"""
    metric_type: str = Field(..., description="Type of metric aggregated")
    encrypted_result: str = Field(..., description="Base64-encoded encrypted aggregate")
    count: int = Field(..., description="Number of values aggregated")
    operation: Literal["sum", "average"] = Field(..., description="Operation performed")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "metric_type": "word_count",
            "encrypted_result": "AQAAAAAA...base64...",
            "count": 42,
            "operation": "sum"
        }
    })


class HEContextResponse(BaseModel):
    """HE context parameters for client"""
    context_params: Dict[str, Any] = Field(..., description="CKKS context parameters")
    serialized_context: Optional[str] = Field(None, description="Base64-encoded public context (optional)")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "context_params": {
                "scheme": "CKKS",
                "poly_modulus_degree": 8192,
                "coeff_mod_bit_sizes": [60, 40, 40, 60],
                "scale": 1099511627776
            }
        }
    })


class EncryptedContent(BaseModel):
    """AES-256 encrypted content (journal entry)"""
    content_id: str = Field(..., description="Log ID")
    encrypted_blob: str = Field(..., description="Base64-encoded AES-256 encrypted content")
    iv: str = Field(..., description="Initialization vector (base64)")
    tag: Optional[str] = Field(None, description="Authentication tag for GCM mode (base64)")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "content_id": "550e8400-e29b-41d4-a716-446655440000",
            "encrypted_blob": "YWJjZGVm...base64...",
            "iv": "MTIzNDU2Nzg5MDEyMzQ1Ng==",
            "tag": "dGFnMTIzNDU2Nzg5MDEyMzQ1Ng=="
        }
    })


class EncryptedEmbedding(BaseModel):
    """AES-256 encrypted embedding vector"""
    embedding_id: str = Field(..., description="Log ID")
    encrypted_vector: str = Field(..., description="Base64-encoded encrypted embedding")
    iv: str = Field(..., description="Initialization vector (base64)")
    vector_dimension: Optional[int] = Field(None, description="Embedding dimension (for validation)")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "embedding_id": "550e8400-e29b-41d4-a716-446655440000",
            "encrypted_vector": "YWJjZGVm...base64...",
            "iv": "MTIzNDU2Nzg5MDEyMzQ1Ng==",
            "vector_dimension": 1024
        }
    })


class EncryptedBackupData(BaseModel):
    """Complete encrypted backup (content + embedding)"""
    id: str = Field(..., description="Log ID")
    encrypted_content: str = Field(..., description="Base64-encoded AES-256 encrypted content")
    content_iv: str = Field(..., description="Content IV (base64)")
    content_tag: Optional[str] = Field(None, description="Content auth tag (base64)")

    encrypted_embedding: Optional[str] = Field(None, description="Base64-encoded encrypted embedding")
    embedding_iv: Optional[str] = Field(None, description="Embedding IV (base64)")

    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    device_id: str = Field(..., description="Device that created/updated this entry")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "encrypted_content": "YWJjZGVm...",
            "content_iv": "MTIzNDU2Nzg5MDEyMzQ1Ng==",
            "encrypted_embedding": "ZW1iZWRkaW5n...",
            "embedding_iv": "ZW1iZWRkaW5nSVY=",
            "created_at": "2025-11-09T10:30:00Z",
            "updated_at": "2025-11-09T10:30:00Z",
            "device_id": "device-uuid-12345"
        }
    })


class EncryptedBackupResponse(BaseModel):
    """Response from backup upload"""
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    device_id: str
    message: str = "Backup stored successfully"


class EncryptedBackupList(BaseModel):
    """List of encrypted backups for sync"""
    backups: list[EncryptedBackupData]
    has_more: bool = Field(False, description="Whether there are more backups to fetch")
    total_count: Optional[int] = Field(None, description="Total number of backups (optional)")


class ConflictVersion(BaseModel):
    """One version of a conflicting entry"""
    encrypted_content: str
    iv: str
    tag: Optional[str] = Field(None, description="Authentication tag for AES-GCM (base64)")
    updated_at: datetime
    device_id: str


class SyncConflict(BaseModel):
    """Conflict between local and remote versions"""
    id: str = Field(..., description="Conflict ID")
    log_id: str = Field(..., description="ID of the conflicting log entry")
    local_version: ConflictVersion
    remote_version: ConflictVersion
    detected_at: datetime

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": "conflict-uuid",
            "log_id": "log-uuid",
            "local_version": {
                "encrypted_content": "bG9jYWw=",
                "iv": "bG9jYWxJVg==",
                "tag": "bG9jYWxUYWc=",
                "updated_at": "2025-11-09T10:30:00Z",
                "device_id": "device-1"
            },
            "remote_version": {
                "encrypted_content": "cmVtb3Rl",
                "iv": "cmVtb3RlSVY=",
                "tag": "cmVtb3RlVGFn",
                "updated_at": "2025-11-09T10:31:00Z",
                "device_id": "device-2"
            },
            "detected_at": "2025-11-09T10:32:00Z"
        }
    })


class ConflictResolution(BaseModel):
    """Client's resolution of a conflict"""
    chosen_version: Literal["local", "remote", "merged"] = Field(..., description="Which version to keep")
    final_encrypted_content: Optional[str] = Field(None, description="If 'merged', the merged content")
    final_iv: Optional[str] = Field(None, description="If 'merged', the IV for merged content")
    final_encrypted_embedding: Optional[str] = Field(None, description="If 'merged', the merged embedding")
    final_embedding_iv: Optional[str] = Field(None, description="If 'merged', the embedding IV")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "chosen_version": "local"
        }
    })


class ConflictList(BaseModel):
    """List of unresolved conflicts"""
    conflicts: list[SyncConflict]
    total_count: int


class EncryptionStatusResponse(BaseModel):
    """Generic status response for encryption operations"""
    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None
