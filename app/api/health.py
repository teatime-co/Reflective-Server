from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
import tenseal as ts

router = APIRouter()

@router.get("/health")
async def health_check():
    """
    Basic liveness check - verifies the application is running.
    """
    return {
        "status": "healthy",
        "service": "reflective-api"
    }

@router.get("/health/ready")
async def readiness_check(db: Session = Depends(get_db)):
    """
    Readiness check - verifies critical dependencies are available.
    Checks: database connectivity, TenSEAL library initialization.
    """
    checks = {
        "database": "unknown",
        "tenseal": "unknown"
    }

    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = "unhealthy"
        raise HTTPException(
            status_code=503,
            detail={"status": "not_ready", "checks": checks, "error": str(e)}
        )

    try:
        context = ts.context(ts.SCHEME_TYPE.CKKS, poly_modulus_degree=8192, coeff_mod_bit_sizes=[60, 40, 40, 60])
        context.global_scale = 2**40
        checks["tenseal"] = "healthy"
    except Exception as e:
        checks["tenseal"] = "unhealthy"
        raise HTTPException(
            status_code=503,
            detail={"status": "not_ready", "checks": checks, "error": str(e)}
        )

    return {
        "status": "ready",
        "checks": checks
    }
