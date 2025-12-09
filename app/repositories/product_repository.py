"""Product repository."""
import uuid
from typing import Sequence

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product


class ProductRepository:
    """Repository for product operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, product: Product) -> Product:
        """Create a new product."""
        self.session.add(product)
        await self.session.flush()
        await self.session.refresh(product)
        return product

    async def get_by_id(self, product_id: uuid.UUID) -> Product | None:
        """Get product by ID."""
        result = await self.session.execute(select(Product).where(Product.id == product_id))
        return result.scalar_one_or_none()

    async def get_by_id_for_update(self, product_id: uuid.UUID) -> Product | None:
        """Get product by ID with row lock for update."""
        result = await self.session.execute(
            select(Product).where(Product.id == product_id).with_for_update()
        )
        return result.scalar_one_or_none()

    async def get_by_ids_for_update(self, product_ids: list[uuid.UUID]) -> Sequence[Product]:
        """Get multiple products by IDs with row locks for update."""
        result = await self.session.execute(
            select(Product).where(Product.id.in_(product_ids)).with_for_update()
        )
        return result.scalars().all()

    async def get_by_name(self, name: str) -> Product | None:
        """Get product by name."""
        result = await self.session.execute(select(Product).where(Product.name == name))
        return result.scalar_one_or_none()

    async def update(self, product: Product) -> Product:
        """Update product."""
        await self.session.flush()
        await self.session.refresh(product)
        return product

    async def list_products(
        self,
        search_query: str | None = None,
        is_active: bool | None = None,
        sort_by: str = "created_at",
        sort_desc: bool = True,
        cursor_value: str | None = None,
        limit: int = 20,
    ) -> Sequence[Product]:
        """List products with cursor pagination."""
        query = select(Product)

        if search_query:
            query = query.where(Product.name.ilike(f"%{search_query}%"))
        if is_active is not None:
            query = query.where(Product.is_active == is_active)

        if cursor_value:
            if sort_desc:
                query = query.where(getattr(Product, sort_by) < cursor_value)
            else:
                query = query.where(getattr(Product, sort_by) > cursor_value)

        sort_column = getattr(Product, sort_by)
        if sort_desc:
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        query = query.limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

