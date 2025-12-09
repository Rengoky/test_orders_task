"""Seed database with sample data for testing."""
import asyncio

from app.db import AsyncSessionLocal
from app.models.product import Product


async def seed_products() -> None:
    """Create sample products."""
    async with AsyncSessionLocal() as session:
        products = [
            Product(name="Laptop", price=1500.00, stock=10, is_active=True),
            Product(name="Mouse", price=25.00, stock=50, is_active=True),
            Product(name="Keyboard", price=75.00, stock=30, is_active=True),
            Product(name="Monitor", price=300.00, stock=15, is_active=True),
            Product(name="Headphones", price=100.00, stock=25, is_active=True),
        ]

        session.add_all(products)
        await session.commit()

        print(f"✅ Created {len(products)} products")
        for p in products:
            print(f"   - {p.name}: ${p.price} (stock: {p.stock})")


if __name__ == "__main__":
    print("🌱 Seeding database...")
    asyncio.run(seed_products())
    print("✅ Done!")



