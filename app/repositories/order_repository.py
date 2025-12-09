"""Order repository."""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.order import Order, OrderItem


class OrderRepository:
    """Repository for order operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, order: Order) -> Order:
        """Create a new order with items."""
        self.session.add(order)
        await self.session.flush()
        await self.session.refresh(order)
        return order

    async def get_by_id(self, order_id: uuid.UUID) -> Order | None:
        """Get order by ID with items."""
        result = await self.session.execute(
            select(Order).where(Order.id == order_id).options(selectinload(Order.items))
        )
        return result.scalar_one_or_none()

    async def update(self, order: Order) -> Order:
        """Update order."""
        await self.session.flush()
        await self.session.refresh(order)
        return order

    async def add_item(self, item: OrderItem) -> OrderItem:
        """Add an item to an order."""
        self.session.add(item)
        await self.session.flush()
        await self.session.refresh(item)
        return item



