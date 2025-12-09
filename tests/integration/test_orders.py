"""Integration tests for order creation and idempotency."""
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product


@pytest.mark.asyncio
async def test_create_order_with_idempotency(client: AsyncClient, db_session: AsyncSession):
    """Test order creation with idempotency key."""
    # Create a product first
    product = Product(name="Test Product", price=100.00, stock=10, is_active=True)
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    # Create order
    order_data = {
        "user_email": "test@example.com",
        "items": [{"product_id": str(product.id), "quantity": 2}],
    }

    idempotency_key = str(uuid.uuid4())
    headers = {"Idempotency-Key": idempotency_key, "X-Admin-Secret": "test-secret"}

    # First request - should create order
    response1 = await client.post("/orders", json=order_data, headers=headers)
    assert response1.status_code == 201
    order1 = response1.json()
    assert order1["user_email"] == "test@example.com"
    assert order1["status"] == "reserved"
    assert float(order1["items_total"]) == 200.00

    # Second request with same key and payload - should return same order
    response2 = await client.post("/orders", json=order_data, headers=headers)
    assert response2.status_code == 201
    order2 = response2.json()
    assert order1["id"] == order2["id"]

    # Verify stock was reserved only once
    await db_session.refresh(product)
    assert product.stock == 8  # 10 - 2 = 8


@pytest.mark.asyncio
async def test_idempotency_key_conflict(client: AsyncClient, db_session: AsyncSession):
    """Test idempotency key conflict with different payload."""
    # Create products
    product1 = Product(name="Product 1", price=100.00, stock=10, is_active=True)
    product2 = Product(name="Product 2", price=200.00, stock=10, is_active=True)
    db_session.add_all([product1, product2])
    await db_session.commit()
    await db_session.refresh(product1)
    await db_session.refresh(product2)

    idempotency_key = str(uuid.uuid4())
    headers = {"Idempotency-Key": idempotency_key, "X-Admin-Secret": "test-secret"}

    # First request
    order_data1 = {
        "user_email": "test@example.com",
        "items": [{"product_id": str(product1.id), "quantity": 1}],
    }
    response1 = await client.post("/orders", json=order_data1, headers=headers)
    assert response1.status_code == 201

    # Second request with same key but different payload - should fail
    order_data2 = {
        "user_email": "test@example.com",
        "items": [{"product_id": str(product2.id), "quantity": 1}],
    }
    response2 = await client.post("/orders", json=order_data2, headers=headers)
    assert response2.status_code == 409
    assert "Idempotency key conflict" in response2.json()["detail"]


@pytest.mark.asyncio
async def test_insufficient_stock(client: AsyncClient, db_session: AsyncSession):
    """Test order creation with insufficient stock."""
    # Create product with limited stock
    product = Product(name="Limited Product", price=100.00, stock=5, is_active=True)
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    # Try to order more than available
    order_data = {
        "user_email": "test@example.com",
        "items": [{"product_id": str(product.id), "quantity": 10}],
    }

    headers = {"Idempotency-Key": str(uuid.uuid4()), "X-Admin-Secret": "test-secret"}
    response = await client.post("/orders", json=order_data, headers=headers)

    assert response.status_code == 409
    assert "Insufficient stock" in response.json()["detail"]

    # Verify stock unchanged
    await db_session.refresh(product)
    assert product.stock == 5


@pytest.mark.asyncio
async def test_cancel_order_restores_stock(client: AsyncClient, db_session: AsyncSession):
    """Test that canceling an order restores stock."""
    # Create product
    product = Product(name="Test Product", price=100.00, stock=10, is_active=True)
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    # Create order
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
    assert product.stock == 7  # 10 - 3 = 7

    # Cancel order
    response = await client.post(f"/orders/{order_id}/cancel")
    assert response.status_code == 200
    canceled_order = response.json()
    assert canceled_order["status"] == "canceled"

    # Verify stock was restored
    await db_session.refresh(product)
    assert product.stock == 10  # 7 + 3 = 10



