"""Product service."""
import uuid
from decimal import Decimal
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging_config import get_logger
from app.models.product import Product
from app.repositories.product_repository import ProductRepository

logger = get_logger(__name__)


class ProductService:
    """Service for product operations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.product_repo = ProductRepository(session)

    async def create_product(
        self, name: str, price: Decimal, stock: int = 0, is_active: bool = True
    ) -> Product:
        """Create a new product."""
        existing = await self.product_repo.get_by_name(name)
        if existing:
            raise ValueError(f"Product with name '{name}' already exists")

        product = Product(name=name, price=price, stock=stock, is_active=is_active)
        product = await self.product_repo.create(product)
        await self.session.commit()

        logger.info(f"Created product: {product.id} ({product.name})")
        return product

    async def update_product(
        self,
        product_id: uuid.UUID,
        price: Decimal | None = None,
        stock: int | None = None,
        is_active: bool | None = None,
    ) -> Product:
        """Update product."""
        product = await self.product_repo.get_by_id(product_id)
        if not product:
            raise ValueError(f"Product {product_id} not found")

        if price is not None:
            product.price = price
        if stock is not None:
            product.stock = stock
        if is_active is not None:
            product.is_active = is_active

        product = await self.product_repo.update(product)
        await self.session.commit()

        logger.info(f"Updated product: {product.id}")
        return product

    async def get_product(self, product_id: uuid.UUID) -> Product | None:
        """Get product by ID."""
        return await self.product_repo.get_by_id(product_id)

    async def list_products(
        self,
        search_query: str | None = None,
        is_active: bool | None = None,
        sort_by: str = "created_at",
        sort_desc: bool = True,
        cursor: str | None = None,
        limit: int = 20,
    ) -> Sequence[Product]:
        """List products with cursor pagination."""
        return await self.product_repo.list_products(
            search_query=search_query,
            is_active=is_active,
            sort_by=sort_by,
            sort_desc=sort_desc,
            cursor_value=cursor,
            limit=limit,
        )

