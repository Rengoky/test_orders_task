# Примеры API - Сервис заказов

Подробные примеры для всех API эндпоинтов.

## Требования

Установите переменные окружения:
```bash
export API_URL="http://localhost:8000"
export ADMIN_SECRET="dev-admin-secret"
```

## Admin эндпоинты

### Создать продукт

```bash
curl -X POST "$API_URL/admin/products" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Secret: $ADMIN_SECRET" \
  -d '{
    "name": "MacBook Pro",
    "price": 2499.99,
    "stock": 5,
    "is_active": true
  }'
```

**Ответ (201 Created)**:
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "name": "MacBook Pro",
  "price": "2499.99",
  "stock": 5,
  "is_active": true,
  "created_at": "2024-12-08T22:00:00Z",
  "updated_at": "2024-12-08T22:00:00Z"
}
```

### Обновить продукт

```bash
# Обновить цену и количество
curl -X PATCH "$API_URL/admin/products/3fa85f64-5717-4562-b3fc-2c963f66afa6" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Secret: $ADMIN_SECRET" \
  -d '{
    "price": 2299.99,
    "stock": 10
  }'
```

```bash
# Деактивировать продукт
curl -X PATCH "$API_URL/admin/products/3fa85f64-5717-4562-b3fc-2c963f66afa6" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Secret: $ADMIN_SECRET" \
  -d '{
    "is_active": false
  }'
```

## Публичные эндпоинты

### Список продуктов

**Базовый запрос**:
```bash
curl "$API_URL/products"
```

**С фильтрами**:
```bash
# Только активные продукты
curl "$API_URL/products?is_active=true"

# Поиск по названию
curl "$API_URL/products?q=macbook"

# С пагинацией
curl "$API_URL/products?limit=10"

# Следующая страница (используйте cursor из предыдущего ответа)
curl "$API_URL/products?cursor=MjAyNC0xMi0wOFQyMjowMDowMFo=&limit=10"

# Сортировка по цене по возрастанию
curl "$API_URL/products?sort_by=price&sort_desc=false"
```

**Ответ**:
```json
[
  {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "name": "MacBook Pro",
    "price": "2499.99",
    "stock": 5,
    "is_active": true,
    "created_at": "2024-12-08T22:00:00Z",
    "updated_at": "2024-12-08T22:00:00Z"
  }
]
```

### Создать заказ (идемпотентно)

```bash
curl -X POST "$API_URL/orders" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: order-$(date +%s)" \
  -d '{
    "user_email": "customer@example.com",
    "items": [
      {
        "product_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "quantity": 2
      }
    ]
  }'
```

**Ответ (201 Created)**:
```json
{
  "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "user_email": "customer@example.com",
  "status": "reserved",
  "items_total": "4999.98",
  "items": [
    {
      "id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
      "product_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "quantity": 2,
      "price_snapshot": "2499.99"
    }
  ],
  "created_at": "2024-12-08T22:05:00Z",
  "updated_at": "2024-12-08T22:05:00Z"
}
```

**Случаи ошибок**:

```bash
# Недостаточно товара (409 Conflict)
curl -X POST "$API_URL/orders" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: unique-key" \
  -d '{
    "user_email": "customer@example.com",
    "items": [
      {"product_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6", "quantity": 100}
    ]
  }'

# Ответ: {"detail": "Insufficient stock for MacBook Pro: requested 100, available 5"}
```

```bash
# Продукт не найден (400 Bad Request)
curl -X POST "$API_URL/orders" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: unique-key-2" \
  -d '{
    "user_email": "customer@example.com",
    "items": [
      {"product_id": "00000000-0000-0000-0000-000000000000", "quantity": 1}
    ]
  }'

# Ответ: {"detail": "Products not found: {...}"}
```

```bash
# Конфликт ключа идемпотентности (409 Conflict)
# Сначала создайте заказ
curl -X POST "$API_URL/orders" \
  -H "Idempotency-Key: test-key-123" \
  -H "Content-Type: application/json" \
  -d '{"user_email": "test@example.com", "items": [...]}'

# Затем попробуйте тот же ключ с другими данными
curl -X POST "$API_URL/orders" \
  -H "Idempotency-Key: test-key-123" \
  -H "Content-Type: application/json" \
  -d '{"user_email": "different@example.com", "items": [...]}'

# Ответ: {"detail": "Idempotency key conflict: different payload for same key"}
```

### Получить заказ

```bash
curl "$API_URL/orders/7c9e6679-7425-40de-944b-e07fc1f90ae7"
```

**Ответ (200 OK)**:
```json
{
  "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "user_email": "customer@example.com",
  "status": "paid",
  "items_total": "4999.98",
  "items": [...],
  "created_at": "2024-12-08T22:05:00Z",
  "updated_at": "2024-12-08T22:06:00Z"
}
```

### Отменить заказ

```bash
curl -X POST "$API_URL/orders/7c9e6679-7425-40de-944b-e07fc1f90ae7/cancel"
```

**Ответ (200 OK)**:
```json
{
  "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "user_email": "customer@example.com",
  "status": "canceled",
  "items_total": "4999.98",
  "items": [...],
  "created_at": "2024-12-08T22:05:00Z",
  "updated_at": "2024-12-08T22:07:00Z"
}
```

**Случаи ошибок**:

```bash
# Нельзя отменить оплаченный заказ (409 Conflict)
curl -X POST "$API_URL/orders/{paid_order_id}/cancel"
# Ответ: {"detail": "Order {id} cannot be canceled (status: paid)"}

# Заказ не найден (404 Not Found)
curl -X POST "$API_URL/orders/00000000-0000-0000-0000-000000000000/cancel"
# Ответ: {"detail": "Order 00000000-0000-0000-0000-000000000000 not found"}
```

## Webhook платежей

### Fake Payment сервис

```bash
curl -X POST "$API_URL/_fake_payments" \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "amount": 4999.98
  }'
```

**Ответ**:
```json
{
  "payment_id": "pay_1a2b3c4d5e6f",
  "status": "pending"
}
```

### Payment Callback (Webhook)

**Успех**:
```bash
curl -X POST "$API_URL/payments/callback" \
  -H "Content-Type: application/json" \
  -d '{
    "payment_id": "pay_1a2b3c4d5e6f",
    "order_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "status": "success"
  }'
```

**Неудача**:
```bash
curl -X POST "$API_URL/payments/callback" \
  -H "Content-Type: application/json" \
  -d '{
    "payment_id": "pay_1a2b3c4d5e6f",
    "order_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "status": "failed"
  }'
```

**Ответ**:
```json
{
  "status": "ok",
  "message": "Webhook processed successfully"
}
```

## Наблюдаемость

### Health Check

```bash
curl "$API_URL/healthz"
```

**Ответ**:
```json
{
  "status": "healthy",
  "database": "connected"
}
```

### Метрики Prometheus

```bash
curl "$API_URL/metrics"
```

**Ответ**:
```
# HELP orders_total Total number of orders created
# TYPE orders_total counter
orders_total 42.0

# HELP orders_canceled_total Total number of orders canceled
# TYPE orders_canceled_total counter
orders_canceled_total 5.0

# HELP orders_paid_total Total number of orders paid
# TYPE orders_paid_total counter
orders_paid_total 37.0

# HELP outbox_pending Number of pending outbox events
# TYPE outbox_pending gauge
outbox_pending 0.0

# HELP worker_errors_total Total number of worker errors
# TYPE worker_errors_total counter
worker_errors_total 0.0
```

## Полный пример потока

```bash
#!/bin/bash

API_URL="http://localhost:8000"
ADMIN_SECRET="dev-admin-secret"

# 1. Создать продукт
echo "Создание продукта..."
PRODUCT=$(curl -s -X POST "$API_URL/admin/products" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Secret: $ADMIN_SECRET" \
  -d '{"name": "Тестовый продукт", "price": 100.00, "stock": 10, "is_active": true}')

PRODUCT_ID=$(echo "$PRODUCT" | jq -r '.id')
echo "ID продукта: $PRODUCT_ID"

# 2. Создать заказ
echo "Создание заказа..."
ORDER=$(curl -s -X POST "$API_URL/orders" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: test-$(date +%s)" \
  -d "{\"user_email\": \"test@example.com\", \"items\": [{\"product_id\": \"$PRODUCT_ID\", \"quantity\": 2}]}")

ORDER_ID=$(echo "$ORDER" | jq -r '.id')
echo "ID заказа: $ORDER_ID"
echo "Статус: $(echo "$ORDER" | jq -r '.status')"

# 3. Ждать обработки платежа (Outbox воркер)
sleep 10

# 4. Проверить финальный статус заказа
echo "Проверка статуса заказа..."
curl -s "$API_URL/orders/$ORDER_ID" | jq '{id, status, items_total}'
```

## Rate Limiting

API применяет ограничение частоты запросов при создании заказов:
- **Лимит**: 5 заказов в минуту на email пользователя
- **Ответ**: 429 Too Many Requests

```bash
# Тест rate limiting
for i in {1..6}; do
  curl -X POST "$API_URL/orders" \
    -H "Content-Type: application/json" \
    -H "Idempotency-Key: rate-test-$i" \
    -d '{"user_email": "test@example.com", "items": [...]}'
  echo ""
done

# 6-й запрос вернет:
# {"detail": "Rate limit exceeded: 5 requests per 60 seconds"}
```

## Аутентификация

### Admin эндпоинты
Требуют заголовок `X-Admin-Secret`:
```bash
curl -H "X-Admin-Secret: your-secret" "$API_URL/admin/products"
```

### Webhook подпись (Production)
Webhook платежей должны включать HMAC подпись:
```bash
PAYLOAD='{"payment_id": "...", "order_id": "...", "status": "success"}'
SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "webhook-secret" | cut -d' ' -f2)

curl -X POST "$API_URL/payments/callback" \
  -H "Content-Type: application/json" \
  -H "X-Signature: $SIGNATURE" \
  -d "$PAYLOAD"
```
