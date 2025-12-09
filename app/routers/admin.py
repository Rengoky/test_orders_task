"""Admin API routes."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging_config import get_logger
from app.core.security import verify_admin_secret
from app.db import get_db
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate
from app.services.product_service import ProductService

logger = get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(verify_admin_secret)])


@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreate,
    db: AsyncSession = Depends(get_db),
) -> ProductResponse:
    """Create a new product (admin only)."""
    try:
        service = ProductService(db)
        product = await service.create_product(
            name=product_data.name,
            price=product_data.price,
            stock=product_data.stock,
            is_active=product_data.is_active,
        )
        return ProductResponse.model_validate(product)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch("/products/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: uuid.UUID,
    product_data: ProductUpdate,
    db: AsyncSession = Depends(get_db),
) -> ProductResponse:
    """Update a product (admin only)."""
    try:
        service = ProductService(db)
        product = await service.update_product(
            product_id=product_id,
            price=product_data.price,
            stock=product_data.stock,
            is_active=product_data.is_active,
        )
        return ProductResponse.model_validate(product)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))



