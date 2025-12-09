"""Security utilities."""
import hmac
import hashlib

from fastapi import Header, HTTPException, status

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def verify_admin_secret(x_admin_secret: str = Header(...)) -> None:
    """Verify admin secret header."""
    if x_admin_secret != settings.admin_secret:
        logger.warning("Invalid admin secret attempt")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin secret",
        )


def compute_hmac_signature(payload: str, secret: str) -> str:
    """Compute HMAC-SHA256 signature for payload."""
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


def verify_webhook_signature(payload: str, signature: str, secret: str) -> bool:
    """Verify HMAC signature for webhook."""
    expected_signature = compute_hmac_signature(payload, secret)
    return hmac.compare_digest(expected_signature, signature)


async def verify_payment_webhook_signature(
    request_body: str, x_signature: str = Header(...)
) -> None:
    """Verify payment webhook signature."""
    if not verify_webhook_signature(
        request_body, x_signature, settings.payment_webhook_secret
    ):
        logger.warning("Invalid webhook signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )



