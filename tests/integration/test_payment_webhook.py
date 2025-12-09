"""Test payment webhook handling."""
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import OrderStatus
from app.models.product import Product


@pytest.mark.asyncio
async def test_payment_webhook_success(client: AsyncClient, db_session: AsyncSession):
    """Test successful payment webhook updates order to paid."""
    # Create product and order
    product = Product(name="Test Product", price=100.00, stock=10, is_active=True)
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    order_data = {
        "user_email": "test@example.com",
        "items": [{"product_id": str(product.id), "quantity": 2}],
    }

    headers = {"Idempotency-Key": str(uuid.uuid4()), "X-Admin-Secret": "test-secret"}
    response = await client.post("/orders", json=order_data, headers=headers)
    assert response.status_code == 201
    order = response.json()
    order_id = order["id"]

    # Send successful payment webhook
    webhook_data = {"payment_id": str(uuid.uuid4()), "order_id": order_id, "status": "success"}

    response = await client.post("/payments/callback", json=webhook_data)
    assert response.status_code == 200

    # Verify order is marked as paid
    response = await client.get(f"/orders/{order_id}")
    assert response.status_code == 200
    updated_order = response.json()
    assert updated_order["status"] == "paid"

    # Verify stock remains reserved (not restored)
    await db_session.refresh(product)
    assert product.stock == 8


@pytest.mark.asyncio
async def test_payment_webhook_failed(client: AsyncClient, db_session: AsyncSession):
    """Test failed payment webhook cancels order and restores stock."""
    # Create product and order
    product = Product(name="Test Product", price=100.00, stock=10, is_active=True)
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    order_data = {
        "user_email": "test@example.com",
        "items": [{"product_id": str(product.id), "quantity": 3}],
    }

    headers = {"Idempotency-Key": str(uuid.uuid4()), "X-Admin-Secret": "test-secret"}
    response = await client.post("/orders", json=order_data, headers=headers)
    assert response.status_code == 201
    order = response.json()
    order_id = order["id"]

    # Verify stock was reserved
    await db_session.refresh(product)
    assert product.stock == 7

    # Send failed payment webhook
    webhook_data = {"payment_id": str(uuid.uuid4()), "order_id": order_id, "status": "failed"}

    response = await client.post("/payments/callback", json=webhook_data)
    assert response.status_code == 200

    # Verify order is canceled
    response = await client.get(f"/orders/{order_id}")
    assert response.status_code == 200
    updated_order = response.json()
    assert updated_order["status"] == "canceled"

    # Verify stock was restored
    await db_session.refresh(product)
    assert product.stock == 10



