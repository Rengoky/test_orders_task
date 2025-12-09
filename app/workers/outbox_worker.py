"""Outbox worker for processing events with retry logic."""
import asyncio
import json
import random
import uuid
from datetime import datetime, timedelta

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging_config import get_logger, request_id_ctx_var
from app.db import AsyncSessionLocal
from app.models.order import OrderStatus
from app.models.outbox import OutboxStatus
from app.repositories.order_repository import OrderRepository
from app.repositories.outbox_repository import OutboxRepository

logger = get_logger(__name__)


class OutboxWorker:
    """Worker for processing outbox events."""

    def __init__(self) -> None:
        self.running = False
        self.http_client: httpx.AsyncClient | None = None

    async def start(self) -> None:
        """Start the outbox worker."""
        self.running = True
        self.http_client = httpx.AsyncClient(timeout=30.0)
        logger.info("Outbox worker started")

        try:
            while self.running:
                await self._process_events()
                await asyncio.sleep(settings.outbox_worker_interval_seconds)
        except Exception as e:
            logger.error(f"Outbox worker crashed: {e}")
        finally:
            if self.http_client:
                await self.http_client.aclose()

    async def stop(self) -> None:
        """Stop the outbox worker."""
        self.running = False
        logger.info("Outbox worker stopped")

    async def _process_events(self) -> None:
        """Process pending outbox events."""
        async with AsyncSessionLocal() as session:
            try:
                repo = OutboxRepository(session)
                events = await repo.get_pending_events(limit=10)

                if not events:
                    return

                logger.info(f"Processing {len(events)} outbox events")

                for event in events:
                    request_id_ctx_var.set(str(event.id))

                    try:
                        await self._process_event(event, session)
                        await session.commit()
                    except Exception as e:
                        logger.error(f"Failed to process event {event.id}: {e}")
                        await session.rollback()

            except Exception as e:
                logger.error(f"Error fetching outbox events: {e}")
                await session.rollback()

    async def _process_event(self, event: any, session: AsyncSession) -> None:  # type: ignore[valid-type]
        """Process a single outbox event."""
        logger.info(f"Processing event: {event.id} ({event.event_type})")

        try:
            if event.event_type == "order.created":
                await self._handle_order_created(event, session)

            event.status = OutboxStatus.SENT.value
            await session.flush()

            logger.info(f"Event {event.id} processed successfully")

        except Exception as e:
            event.attempts += 1

            if event.attempts >= settings.outbox_max_attempts:
                event.status = OutboxStatus.DEAD.value
                logger.error(
                    f"Event {event.id} moved to dead letter queue after "
                    f"{event.attempts} attempts: {e}"
                )
            else:
                delay = settings.outbox_retry_base_delay_seconds * (2 ** (event.attempts - 1))
                delay += random.uniform(0, 1)
                event.next_attempt_at = datetime.utcnow() + timedelta(seconds=delay)

                logger.warning(
                    f"Event {event.id} retry scheduled in {delay}s "
                    f"(attempt {event.attempts}/{settings.outbox_max_attempts}): {e}"
                )

            await session.flush()
            raise

    async def _handle_order_created(self, event: any, session: AsyncSession) -> None:  # type: ignore[valid-type]
        """Handle order.created event by calling fake payment service."""
        payload = json.loads(event.payload_json)
        order_id = payload["order_id"]
        total = float(payload["total"])

        logger.info(f"Initiating payment for order {order_id}, amount: {total}")

        order_repo = OrderRepository(session)
        order = await order_repo.get_by_id(uuid.UUID(order_id))
        if order:
            order.status = OrderStatus.PAYMENT_PENDING.value
            await order_repo.update(order)

        if settings.fake_payment_enabled and self.http_client:
            payment_response = await self.http_client.post(
                "http://localhost:8000/_fake_payments",
                json={"order_id": order_id, "amount": total},
            )
            payment_response.raise_for_status()
            payment_data = payment_response.json()
            payment_id = payment_data["payment_id"]

            logger.info(f"Payment initiated: {payment_id} for order {order_id}")

            await asyncio.sleep(1)

            success = random.random() < settings.fake_payment_success_rate
            payment_status = "success" if success else "failed"

            logger.info(
                f"Simulating payment webhook: payment_id={payment_id}, "
                f"order_id={order_id}, status={payment_status}"
            )

            webhook_response = await self.http_client.post(
                "http://localhost:8000/payments/callback",
                json={
                    "payment_id": payment_id,
                    "order_id": order_id,
                    "status": payment_status,
                },
            )
            webhook_response.raise_for_status()

        else:
            logger.warning("Fake payment service is disabled, skipping payment call")


outbox_worker = OutboxWorker()

