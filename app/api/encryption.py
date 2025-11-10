from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
import base64

from ..database import get_db
from app.api.auth import get_current_user
from ..schemas.user import UserResponse
from ..schemas.encrypted_data import (
    HEContextResponse,
    EncryptedMetricBatch,
    EncryptedMetric,
    AggregateRequest,
    AggregateResult,
    EncryptionStatusResponse
)
from ..services.he_service import HEService, create_client_context
from ..models.models import EncryptedMetric as EncryptedMetricModel

router = APIRouter(prefix="/encryption", tags=["encryption"])


@router.get("/context", response_model=HEContextResponse, status_code=status.HTTP_200_OK)
async def get_he_context():
    """
    Get HE context parameters for client-side encryption.

    This endpoint is PUBLIC (no authentication required) and returns the CKKS context
    parameters that clients need to encrypt metrics before uploading.

    Returns:
        HEContextResponse: Context parameters including poly modulus degree, scale, etc.
    """
    try:
        context, serialized_public = create_client_context()

        context_params = {
            "scheme": "CKKS",
            "poly_modulus_degree": HEService.POLY_MODULUS_DEGREE,
            "coeff_mod_bit_sizes": HEService.COEFF_MOD_BIT_SIZES,
            "scale": HEService.SCALE
        }

        return HEContextResponse(
            context_params=context_params,
            serialized_context=serialized_public
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate HE context: {str(e)}"
        )


@router.post("/metrics", response_model=EncryptionStatusResponse, status_code=status.HTTP_201_CREATED)
async def upload_encrypted_metrics(
    batch: EncryptedMetricBatch,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload encrypted metrics for server-side aggregation.

    Validates user's privacy tier and stores HE-encrypted metrics WITHOUT decryption.

    Privacy tier requirements:
    - local_only: REJECTED (403)
    - analytics_sync: ALLOWED
    - full_sync: ALLOWED

    Args:
        batch: Batch of encrypted metrics
        current_user: Authenticated user from JWT
        db: Database session

    Returns:
        EncryptionStatusResponse: Confirmation with count of stored metrics

    Raises:
        403: User's privacy tier does not allow cloud sync
        422: Invalid encrypted data format
    """
    if current_user.privacy_tier == 'local_only':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cloud sync not enabled. Upgrade privacy tier to 'analytics_sync' or 'full_sync' to upload metrics."
        )

    try:
        stored_count = 0

        for metric in batch.metrics:
            encrypted_value_bytes = base64.b64decode(metric.encrypted_value)

            db_metric = EncryptedMetricModel(
                user_id=current_user.id,
                metric_type=metric.metric_type,
                encrypted_value=encrypted_value_bytes,
                timestamp=metric.timestamp,
                created_at=datetime.utcnow()
            )

            db.add(db_metric)
            stored_count += 1

        db.commit()

        return EncryptionStatusResponse(
            message=f"Successfully stored {stored_count} encrypted metrics",
            success=True,
            details={"count": stored_count, "user_id": str(current_user.id)}
        )

    except ValueError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid encrypted data format: {str(e)}"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store encrypted metrics: {str(e)}"
        )


@router.post("/aggregate", response_model=AggregateResult, status_code=status.HTTP_200_OK)
async def aggregate_encrypted_metrics(
    request: AggregateRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Aggregate encrypted metrics without server-side decryption.

    Performs homomorphic addition or averaging on encrypted values and returns
    the encrypted result for client-side decryption.

    Args:
        request: Aggregation parameters (metric_type, operation, time_range)
        current_user: Authenticated user from JWT
        db: Database session

    Returns:
        AggregateResult: Encrypted aggregate result with metadata

    Raises:
        404: No metrics found matching criteria
        500: HE operation failed
    """
    query = db.query(EncryptedMetricModel).filter(
        EncryptedMetricModel.user_id == current_user.id,
        EncryptedMetricModel.metric_type == request.metric_type
    )

    if request.time_range:
        if "start" in request.time_range:
            query = query.filter(EncryptedMetricModel.timestamp >= request.time_range["start"])
        if "end" in request.time_range:
            query = query.filter(EncryptedMetricModel.timestamp <= request.time_range["end"])

    metrics = query.all()

    if not metrics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No encrypted metrics found for type '{request.metric_type}' in specified time range"
        )

    try:
        context = HEService.create_context()
        encrypted_values = [base64.b64encode(m.encrypted_value).decode('utf-8') for m in metrics]

        if request.operation == "sum":
            encrypted_result = HEService.aggregate_sum(encrypted_values, context)
        elif request.operation == "average":
            encrypted_result = HEService.aggregate_average(encrypted_values, context)
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid operation: {request.operation}. Must be 'sum' or 'average'"
            )

        return AggregateResult(
            metric_type=request.metric_type,
            encrypted_result=encrypted_result,
            count=len(metrics),
            operation=request.operation
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to aggregate encrypted metrics: {str(e)}"
        )
