"""Payment service for handling payment webhooks."""
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging_config import get_logger
from app.models.order import OrderStatus
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.webhook import PaymentStatus

logger = get_logger(__name__)


class PaymentService:
    """Service for payment operations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.order_repo = OrderRepository(session)
        self.product_repo = ProductRepository(session)

    async def process_payment_webhook(
        self, payment_id: str, order_id: uuid.UUID, status: PaymentStatus
    ) -> None:
        """Process payment webhook and update order status."""
        order = await self.order_repo.get_by_id(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")

        logger.info(
            f"Processing payment webhook: payment_id={payment_id}, "
            f"order_id={order_id}, status={status.value}"
        )

        if status == PaymentStatus.SUCCESS:
            order.status = OrderStatus.PAID.value
            await self.order_repo.update(order)
            logger.info(f"Order {order_id} marked as PAID")

        elif status == PaymentStatus.FAILED:
            product_ids = [item.product_id for item in order.items]
            products = await self.product_repo.get_by_ids_for_update(product_ids)
            product_map = {p.id: p for p in products}

            for item in order.items:
                product = product_map.get(item.product_id)
                if product:
                    product.stock += item.quantity
                    logger.info(
                        f"Compensating: restored stock for product {product.id}: "
                        f"+{item.quantity} (new stock: {product.stock})"
                    )

            order.status = OrderStatus.CANCELED.value
            await self.order_repo.update(order)
            logger.info(f"Order {order_id} marked as CANCELED (payment failed)")

        await self.session.commit()

