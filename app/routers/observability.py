"""Observability endpoints (health, metrics)."""
from fastapi import APIRouter, Depends
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, generate_latest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.core.logging_config import get_logger
from app.db import get_db

logger = get_logger(__name__)

router = APIRouter(tags=["observability"])

orders_total = Counter("orders_total", "Total number of orders created")
orders_canceled = Counter("orders_canceled_total", "Total number of orders canceled")
orders_paid = Counter("orders_paid_total", "Total number of orders paid")
outbox_pending = Gauge("outbox_pending", "Number of pending outbox events")
worker_errors = Counter("worker_errors_total", "Total number of worker errors")


@router.get("/healthz")
async def health_check(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """Health check endpoint."""
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}


@router.get("/metrics")
async def metrics() -> Response:
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

