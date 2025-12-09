"""Payment webhook and fake payment service routes."""
import random
import uuid

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging_config import get_logger
from app.core.security import compute_hmac_signature
from app.db import get_db
from app.schemas.webhook import FakePaymentRequest, FakePaymentResponse, PaymentWebhook
from app.services.payment_service import PaymentService

logger = get_logger(__name__)

router = APIRouter(tags=["payments"])


@router.post("/_fake_payments", response_model=FakePaymentResponse)
async def create_fake_payment(payment_data: FakePaymentRequest) -> FakePaymentResponse:
    """
    Fake payment service endpoint (for testing).

    Simulates creating a payment that will be processed asynchronously.
    """
    if not settings.fake_payment_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Fake payment service is disabled",
        )

    payment_id = str(uuid.uuid4())

    logger.info(
        f"Fake payment created: payment_id={payment_id}, "
        f"order_id={payment_data.order_id}, amount={payment_data.amount}"
    )

    return FakePaymentResponse(payment_id=payment_id, status="pending")


@router.post("/payments/callback", status_code=status.HTTP_200_OK)
async def payment_webhook(
    webhook_data: PaymentWebhook,
    request_body: str = Body(..., media_type="application/json"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """
    Payment webhook endpoint.

    Receives payment status updates from the payment provider.
    Signature verification is performed via dependency injection in production.
    """
    logger.info(
        f"Payment webhook received: payment_id={webhook_data.payment_id}, "
        f"order_id={webhook_data.order_id}, status={webhook_data.status.value}"
    )

    try:
        order_id = uuid.UUID(webhook_data.order_id)
        service = PaymentService(db)
        await service.process_payment_webhook(
            payment_id=webhook_data.payment_id,
            order_id=order_id,
            status=webhook_data.status,
        )

        return {"status": "ok", "message": "Webhook processed successfully"}

    except ValueError as e:
        logger.error(f"Payment webhook processing failed: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

