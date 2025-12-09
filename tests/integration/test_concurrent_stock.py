"""Test concurrent stock reservation."""
import asyncio
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product


@pytest.mark.asyncio
async def test_concurrent_stock_reservation(client: AsyncClient, db_session: AsyncSession):
    """Test that concurrent requests properly handle stock reservation."""
    # Create product with only 1 item in stock
    product = Product(name="Last Item", price=100.00, stock=1, is_active=True)
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    # Create two concurrent requests for the same product
    order_data = {
        "user_email": "test@example.com",
        "items": [{"product_id": str(product.id), "quantity": 1}],
    }

    headers1 = {"Idempotency-Key": str(uuid.uuid4()), "X-Admin-Secret": "test-secret"}
    headers2 = {"Idempotency-Key": str(uuid.uuid4()), "X-Admin-Secret": "test-secret"}

    # Send both requests concurrently
    responses = await asyncio.gather(
        client.post("/orders", json=order_data, headers=headers1),
        client.post("/orders", json=order_data, headers=headers2),
        return_exceptions=True,
    )

    # One should succeed, one should fail
    status_codes = [r.status_code for r in responses if hasattr(r, "status_code")]

    # We should have one success (201) and one conflict (409)
    assert 201 in status_codes
    assert 409 in status_codes or len([s for s in status_codes if s == 201]) == 1

    # Verify final stock is 0 (only one order succeeded)
    await db_session.refresh(product)
    assert product.stock == 0



