"""Order API routes."""
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging_config import get_logger
from app.core.rate_limiter import check_rate_limit
from app.db import get_db
from app.schemas.order import OrderCreate, OrderResponse
from app.services.order_service import OrderService

logger = get_logger(__name__)

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: OrderCreate,
    request: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """
    Create a new order with idempotency.

    Requires Idempotency-Key header to prevent duplicate orders.
    """
    await check_rate_limit(request, order_data.user_email, limit=5, window=60)

    try:
        service = OrderService(db)
        order, is_duplicate = await service.create_order(order_data, idempotency_key)

        if is_duplicate:
            logger.info(f"Returning existing order for idempotency key: {idempotency_key}")

        return OrderResponse.model_validate(order)

    except ValueError as e:
        error_msg = str(e)
        if "Idempotency key conflict" in error_msg:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error_msg)
        elif "not found" in error_msg or "not active" in error_msg:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)
        elif "Insufficient stock" in error_msg:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error_msg)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Get order by ID."""
    service = OrderService(db)
    order = await service.get_order(order_id)

    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    return OrderResponse.model_validate(order)


@router.post("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """
    Cancel an order.

    Only allowed for orders in created, reserved, or payment_pending status.
    Stock is restored if it was reserved.
    """
    try:
        service = OrderService(db)
        order = await service.cancel_order(order_id)
        return OrderResponse.model_validate(order)
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_msg)
        elif "cannot be canceled" in error_msg:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error_msg)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

