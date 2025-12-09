"""Outbox repository."""
import uuid
from datetime import datetime
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outbox import Outbox, OutboxStatus


class OutboxRepository:
    """Repository for outbox operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, outbox: Outbox) -> Outbox:
        """Create a new outbox event."""
        self.session.add(outbox)
        await self.session.flush()
        await self.session.refresh(outbox)
        return outbox

    async def get_pending_events(self, limit: int = 10) -> Sequence[Outbox]:
        """Get pending events that are ready to be processed."""
        now = datetime.utcnow()
        result = await self.session.execute(
            select(Outbox)
            .where(Outbox.status == OutboxStatus.PENDING.value)
            .where(Outbox.next_attempt_at <= now)
            .order_by(Outbox.next_attempt_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return result.scalars().all()

    async def update(self, outbox: Outbox) -> Outbox:
        """Update outbox event."""
        await self.session.flush()
        await self.session.refresh(outbox)
        return outbox

    async def get_dead_events(self, limit: int = 100) -> Sequence[Outbox]:
        """Get dead letter events."""
        result = await self.session.execute(
            select(Outbox)
            .where(Outbox.status == OutboxStatus.DEAD.value)
            .order_by(Outbox.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()



