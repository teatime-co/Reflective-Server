from fastapi import APIRouter, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST, CollectorRegistry
from prometheus_client.multiprocess import MultiProcessCollector
import os

router = APIRouter()

registry = CollectorRegistry()

try:
    if 'PROMETHEUS_MULTIPROC_DIR' in os.environ:
        MultiProcessCollector(registry)
except Exception:
    pass

auth_failed_logins = Counter(
    'reflective_auth_failed_logins_total',
    'Total number of failed login attempts',
    registry=registry
)

auth_jwt_errors = Counter(
    'reflective_auth_jwt_errors_total',
    'Total number of JWT decode/validation errors',
    registry=registry
)

auth_active_sessions = Gauge(
    'reflective_auth_active_sessions',
    'Number of currently active authenticated sessions',
    registry=registry
)

db_pool_size = Gauge(
    'reflective_db_pool_size',
    'Current database connection pool size',
    registry=registry
)

db_pool_checked_out = Gauge(
    'reflective_db_pool_checked_out',
    'Number of database connections currently checked out',
    registry=registry
)

db_query_duration = Histogram(
    'reflective_db_query_duration_seconds',
    'Database query duration in seconds',
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
    registry=registry
)

he_operation_duration = Histogram(
    'reflective_he_operation_duration_seconds',
    'Homomorphic encryption operation duration in seconds',
    labelnames=['operation'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
    registry=registry
)

he_context_creation_duration = Histogram(
    'reflective_he_context_creation_duration_seconds',
    'TenSEAL context creation duration in seconds',
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=registry
)

http_requests_total = Counter(
    'reflective_http_requests_total',
    'Total number of HTTP requests',
    labelnames=['method', 'endpoint', 'status'],
    registry=registry
)

http_request_duration = Histogram(
    'reflective_http_request_duration_seconds',
    'HTTP request duration in seconds',
    labelnames=['method', 'endpoint'],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
    registry=registry
)

@router.get("/metrics")
async def get_metrics():
    """
    Prometheus metrics endpoint.
    Exposes application metrics in Prometheus text format.
    """
    return Response(content=generate_latest(registry), media_type=CONTENT_TYPE_LATEST)
