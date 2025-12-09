"""Webhook schemas."""
from enum import Enum

from pydantic import BaseModel, Field


class PaymentStatus(str, Enum):
    """Payment status enum."""

    SUCCESS = "success"
    FAILED = "failed"


class PaymentWebhook(BaseModel):
    """Payment webhook payload."""

    payment_id: str = Field(..., description="Payment ID")
    status: PaymentStatus = Field(..., description="Payment status")
    order_id: str = Field(..., description="Order ID")


class FakePaymentRequest(BaseModel):
    """Fake payment service request."""

    order_id: str = Field(..., description="Order ID")
    amount: float = Field(..., gt=0, description="Payment amount")


class FakePaymentResponse(BaseModel):
    """Fake payment service response."""

    payment_id: str = Field(..., description="Payment ID")
    status: str = Field(default="pending", description="Initial payment status")



