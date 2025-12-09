"""Public product API routes."""
import base64
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging_config import get_logger
from app.db import get_db
from app.schemas.order import ProductFilter
from app.schemas.product import ProductResponse
from app.services.product_service import ProductService

logger = get_logger(__name__)

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[ProductResponse])
async def list_products(
    q: str | None = Query(None, description="Search query for product name"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_desc: bool = Query(True, description="Sort descending"),
    cursor: str | None = Query(None, description="Cursor for pagination"),
    limit: int = Query(20, ge=1, le=100, description="Number of items per page"),
    db: AsyncSession = Depends(get_db),
) -> list[ProductResponse]:
    """
    List products with cursor-based pagination.

    Cursor is base64-encoded value of the sort field from the last item.
    """
    cursor_value = None
    if cursor:
        try:
            cursor_value = base64.b64decode(cursor).decode("utf-8")
        except Exception:
            pass  # Invalid cursor, ignore

    service = ProductService(db)
    products = await service.list_products(
        search_query=q,
        is_active=is_active,
        sort_by=sort_by,
        sort_desc=sort_desc,
        cursor=cursor_value,
        limit=limit,
    )

    return [ProductResponse.model_validate(p) for p in products]

