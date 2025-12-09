"""Order service with idempotency and stock reservation."""
import hashlib
import json
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging_config import get_logger
from app.models.order import Order, OrderItem, OrderStatus
from app.models.outbox import Outbox, OutboxStatus
from app.repositories.idempotency_repository import IdempotencyRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.outbox_repository import OutboxRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.order import OrderCreate

logger = get_logger(__name__)


class OrderService:
    """Service for order operations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.order_repo = OrderRepository(session)
        self.product_repo = ProductRepository(session)
        self.outbox_repo = OutboxRepository(session)
        self.idempotency_repo = IdempotencyRepository(session)

    def _compute_request_hash(self, order_data: OrderCreate) -> str:
        """Compute hash of request payload for idempotency check."""
        payload = {
            "user_email": order_data.user_email,
            "items": [
                {"product_id": str(item.product_id), "quantity": item.quantity}
                for item in order_data.items
            ],
        }
        json_str = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()

    async def create_order(
        self, order_data: OrderCreate, idempotency_key: str
    ) -> tuple[Order, bool]:
        """
        Create order with idempotency, stock reservation, and outbox event.

        Returns:
            tuple: (Order, is_duplicate) - Order object and whether it's a duplicate request
        """
        request_hash = self._compute_request_hash(order_data)

        existing_key = await self.idempotency_repo.get_by_key(idempotency_key)
        if existing_key:
            if existing_key.request_hash != request_hash:
                raise ValueError("Idempotency key conflict: different payload for same key")

            order = await self.order_repo.get_by_id(existing_key.order_id)
            if not order:
                raise ValueError("Referenced order not found")
            logger.info(f"Duplicate request detected for order: {order.id}")
            return order, True

        product_ids = [item.product_id for item in order_data.items]
        products = await self.product_repo.get_by_ids_for_update(product_ids)

        if len(products) != len(product_ids):
            found_ids = {p.id for p in products}
            missing = set(product_ids) - found_ids
            raise ValueError(f"Products not found: {missing}")

        product_map = {p.id: p for p in products}

        items_total = Decimal("0")
        order_items = []

        for item_data in order_data.items:
            product = product_map[item_data.product_id]

            if not product.is_active:
                raise ValueError(f"Product {product.name} is not active")

            if product.stock < item_data.quantity:
                raise ValueError(
                    f"Insufficient stock for {product.name}: "
                    f"requested {item_data.quantity}, available {product.stock}"
                )

            product.stock -= item_data.quantity

            item_total = product.price * item_data.quantity
            items_total += item_total

            order_item = OrderItem(
                product_id=product.id,
                quantity=item_data.quantity,
                price_snapshot=product.price,
            )
            order_items.append(order_item)

        order = Order(
            user_email=order_data.user_email,
            status=OrderStatus.RESERVED.value,
            items_total=items_total,
            items=order_items,
        )
        order = await self.order_repo.create(order)

        try:
            await self.idempotency_repo.create(idempotency_key, request_hash, order.id)
        except IntegrityError:
            await self.session.rollback()
            existing_key = await self.idempotency_repo.get_by_key(idempotency_key)
            if existing_key and existing_key.request_hash == request_hash:
                order = await self.order_repo.get_by_id(existing_key.order_id)
                if order:
                    logger.info(f"Race condition: returning existing order {order.id}")
                    return order, True
            raise

        outbox_payload = {
            "order_id": str(order.id),
            "total": str(order.items_total),
            "items": [
                {
                    "product_id": str(item.product_id),
                    "quantity": item.quantity,
                    "price": str(item.price_snapshot),
                }
                for item in order.items
            ],
        }

        outbox = Outbox(
            event_type="order.created",
            payload_json=json.dumps(outbox_payload),
            status=OutboxStatus.PENDING.value,
            attempts=0,
            next_attempt_at=datetime.utcnow(),
        )
        await self.outbox_repo.create(outbox)

        await self.session.commit()

        logger.info(
            f"Created order: {order.id}, total: {order.items_total}, "
            f"items: {len(order.items)}, user: {order.user_email}"
        )

        return order, False

    async def get_order(self, order_id: uuid.UUID) -> Order | None:
        """Get order by ID."""
        return await self.order_repo.get_by_id(order_id)

    async def cancel_order(self, order_id: uuid.UUID) -> Order:
        """Cancel order and restore stock if not paid."""
        order = await self.order_repo.get_by_id(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")

        cancellable_statuses = [
            OrderStatus.CREATED.value,
            OrderStatus.RESERVED.value,
            OrderStatus.PAYMENT_PENDING.value,
        ]

        if order.status not in cancellable_statuses:
            raise ValueError(f"Order {order_id} cannot be canceled (status: {order.status})")

        if order.status in [OrderStatus.RESERVED.value, OrderStatus.PAYMENT_PENDING.value]:
            product_ids = [item.product_id for item in order.items]
            products = await self.product_repo.get_by_ids_for_update(product_ids)
            product_map = {p.id: p for p in products}

            for item in order.items:
                product = product_map.get(item.product_id)
                if product:
                    product.stock += item.quantity
                    logger.info(
                        f"Restored stock for product {product.id}: +{item.quantity} "
                        f"(new stock: {product.stock})"
                    )

        order.status = OrderStatus.CANCELED.value
        order = await self.order_repo.update(order)
        await self.session.commit()

        logger.info(f"Canceled order: {order.id}")
        return order

