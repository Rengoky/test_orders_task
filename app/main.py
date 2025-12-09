"""Main FastAPI application."""
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.core.rate_limiter import close_redis, init_redis
from app.middleware import RequestIdMiddleware
from app.routers import admin, observability, orders, payments, products
from app.workers import outbox_worker


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    setup_logging()
    init_redis()

    worker_task = asyncio.create_task(outbox_worker.start())

    yield

    await outbox_worker.stop()
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass

    await close_redis()


app = FastAPI(
    title=settings.app_name,
    description="Orders service with reservation, payments, and saga pattern",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(RequestIdMiddleware)

app.include_router(observability.router)
app.include_router(admin.router)
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(payments.router)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "service": settings.app_name,
        "version": "2.0.0",
        "status": "running",
    }

