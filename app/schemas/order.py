"""Order schemas."""
import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class OrderItemCreate(BaseModel):
    """Schema for creating an order item."""

    product_id: uuid.UUID = Field(..., description="Product ID")
    quantity: int = Field(..., gt=0, description="Quantity to order")


class OrderItemResponse(BaseModel):
    """Schema for order item response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    quantity: int
    price_snapshot: Decimal


class OrderCreate(BaseModel):
    """Schema for creating an order."""

    user_email: EmailStr = Field(..., description="User email address")
    items: list[OrderItemCreate] = Field(..., min_length=1, description="Order items")


class OrderResponse(BaseModel):
    """Schema for order response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_email: str
    status: str
    items_total: Decimal
    items: list[OrderItemResponse]
    created_at: datetime
    updated_at: datetime


class CursorPaginationParams(BaseModel):
    """Cursor-based pagination parameters."""

    cursor: str | None = Field(None, description="Base64 encoded cursor for pagination")
    limit: int = Field(default=20, ge=1, le=100, description="Number of items per page")


class ProductFilter(BaseModel):
    """Product filtering parameters."""

    q: str | None = Field(None, description="Search query for product name")
    is_active: bool | None = Field(None, description="Filter by active status")
    sort_by: str = Field(default="created_at", description="Sort field")
    sort_desc: bool = Field(default=True, description="Sort descending")



