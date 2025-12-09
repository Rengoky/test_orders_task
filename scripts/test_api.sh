#!/bin/bash

# API Testing Script
# Demonstrates complete order flow

set -e

BASE_URL="${BASE_URL:-http://localhost:8000}"
ADMIN_SECRET="${ADMIN_SECRET:-dev-admin-secret}"

echo "🧪 Testing Orders API"
echo "====================="
echo ""

# 1. Create a product
echo "1️⃣  Creating product..."
PRODUCT_RESPONSE=$(curl -s -X POST "$BASE_URL/admin/products" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Secret: $ADMIN_SECRET" \
  -d '{
    "name": "Test Product '"$(date +%s)"'",
    "price": 100.00,
    "stock": 10,
    "is_active": true
  }')

PRODUCT_ID=$(echo "$PRODUCT_RESPONSE" | jq -r '.id')
echo "   ✅ Product created: $PRODUCT_ID"
echo ""

# 2. List products
echo "2️⃣  Listing products..."
curl -s "$BASE_URL/products?limit=5" | jq '.[] | {id, name, price, stock}'
echo ""

# 3. Create an order
echo "3️⃣  Creating order..."
IDEMPOTENCY_KEY="test-$(date +%s)"
ORDER_RESPONSE=$(curl -s -X POST "$BASE_URL/orders" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $IDEMPOTENCY_KEY" \
  -d '{
    "user_email": "test@example.com",
    "items": [
      {
        "product_id": "'"$PRODUCT_ID"'",
        "quantity": 2
      }
    ]
  }')

ORDER_ID=$(echo "$ORDER_RESPONSE" | jq -r '.id')
ORDER_STATUS=$(echo "$ORDER_RESPONSE" | jq -r '.status')
echo "   ✅ Order created: $ORDER_ID (status: $ORDER_STATUS)"
echo ""

# 4. Test idempotency - same request should return same order
echo "4️⃣  Testing idempotency (duplicate request)..."
DUPLICATE_RESPONSE=$(curl -s -X POST "$BASE_URL/orders" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $IDEMPOTENCY_KEY" \
  -d '{
    "user_email": "test@example.com",
    "items": [
      {
        "product_id": "'"$PRODUCT_ID"'",
        "quantity": 2
      }
    ]
  }')

DUPLICATE_ORDER_ID=$(echo "$DUPLICATE_RESPONSE" | jq -r '.id')

if [ "$ORDER_ID" == "$DUPLICATE_ORDER_ID" ]; then
  echo "   ✅ Idempotency works! Same order returned: $ORDER_ID"
else
  echo "   ❌ Idempotency failed! Different order: $DUPLICATE_ORDER_ID"
fi
echo ""

# 5. Get order details
echo "5️⃣  Getting order details..."
curl -s "$BASE_URL/orders/$ORDER_ID" | jq '{id, status, items_total, user_email, items: .items | length}'
echo ""

# 6. Check health
echo "6️⃣  Checking health..."
curl -s "$BASE_URL/healthz" | jq '.'
echo ""

# 7. View metrics
echo "7️⃣  Viewing metrics..."
curl -s "$BASE_URL/metrics" | grep -E "^(orders_|outbox_|worker_)" | head -10
echo ""

echo "✅ All tests completed!"
echo ""
echo "📊 Summary:"
echo "   - Product ID: $PRODUCT_ID"
echo "   - Order ID: $ORDER_ID"
echo "   - Status: Check 'docker-compose logs -f app' for Outbox worker processing"



