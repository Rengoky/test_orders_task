"""Product schemas."""
import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    """Schema for creating a product."""

    name: str = Field(..., min_length=1, max_length=255, description="Product name")
    price: Decimal = Field(..., ge=0, decimal_places=2, description="Product price")
    stock: int = Field(default=0, ge=0, description="Stock quantity")
    is_active: bool = Field(default=True, description="Whether product is active")


class ProductUpdate(BaseModel):
    """Schema for updating a product."""

    price: Decimal | None = Field(None, ge=0, decimal_places=2, description="Product price")
    stock: int | None = Field(None, ge=0, description="Stock quantity")
    is_active: bool | None = Field(None, description="Whether product is active")


class ProductResponse(BaseModel):
    """Schema for product response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    price: Decimal
    stock: int
    is_active: bool
    created_at: datetime
    updated_at: datetime



