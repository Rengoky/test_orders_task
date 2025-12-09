"""Idempotency key repository."""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.idempotency import IdempotencyKey


class IdempotencyRepository:
    """Repository for idempotency key operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, key: str, request_hash: str, order_id: uuid.UUID) -> IdempotencyKey:
        """Create a new idempotency key."""
        idempotency_key = IdempotencyKey(key=key, request_hash=request_hash, order_id=order_id)
        self.session.add(idempotency_key)
        await self.session.flush()
        await self.session.refresh(idempotency_key)
        return idempotency_key

    async def get_by_key(self, key: str) -> IdempotencyKey | None:
        """Get idempotency key by key."""
        result = await self.session.execute(
            select(IdempotencyKey).where(IdempotencyKey.key == key)
        )
        return result.scalar_one_or_none()



