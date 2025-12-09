# Быстрый старт ⚡

Запустите сервис Orders v2 за 5 минут.

## Требования

- Docker & Docker Compose установлены
- `curl` и `jq` для тестирования

## 1. Запуск сервиса (30 секунд)

```bash
# Перейдите в проект
cd self_test_task

# Запустите все сервисы
docker-compose up -d

# Подождите запуска сервисов
sleep 10

# Проверьте здоровье
curl http://localhost:8000/healthz
```

**Ожидаемый результат**:
```json
{"status": "healthy", "database": "connected"}
```

## 2. Создайте первый продукт (30 секунд)

```bash
# Установите переменные
export API_URL="http://localhost:8000"
export ADMIN_SECRET="dev-admin-secret"

# Создайте продукт
curl -X POST "$API_URL/admin/products" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Secret: $ADMIN_SECRET" \
  -d '{
    "name": "Laptop",
    "price": 1500.00,
    "stock": 10,
    "is_active": true
  }' | jq '.'
```

**Сохраните ID продукта** из ответа!

## 3. Создайте первый заказ (1 минута)

```bash
# Замените на ваш ID продукта
PRODUCT_ID="вставьте-id-продукта-сюда"

# Создайте заказ
curl -X POST "$API_URL/orders" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: my-first-order" \
  -d "{
    \"user_email\": \"customer@example.com\",
    \"items\": [
      {
        \"product_id\": \"$PRODUCT_ID\",
        \"quantity\": 2
      }
    ]
  }" | jq '.'
```

**Ожидаемый ответ**:
```json
{
  "id": "...",
  "user_email": "customer@example.com",
  "status": "reserved",
  "items_total": "3000.00",
  "items": [...],
  "created_at": "...",
  "updated_at": "..."
}
```

## 4. Наблюдайте за магией ✨ (30 секунд)

```bash
# Сохраните ID заказа
ORDER_ID="вставьте-id-заказа-сюда"

# Смотрите логи обработки Outbox воркером
docker-compose logs -f app | grep -E "order.created|payment|webhook"

# В другом терминале проверьте статус заказа через 10 секунд
sleep 10
curl "$API_URL/orders/$ORDER_ID" | jq '.status'
```

**Вы увидите**:
1. Outbox воркер подхватывает событие
2. Вызывает fake payment сервис
3. Симулирует обработку платежа
4. Webhook обратный вызов обновляет заказ
5. Заказ становится **"paid"** (80% шанс) или **"canceled"** (20% шанс)

## 5. Попробуйте ключевые функции (2 минуты)

### Тест идемпотентности
```bash
# Отправьте тот же запрос дважды
curl -X POST "$API_URL/orders" \
  -H "Idempotency-Key: my-first-order" \
  -H "Content-Type: application/json" \
  -d "{...те же данные...}" | jq '.id'

# Должен вернуть ТОТ ЖЕ ID заказа!
```

### Тест нехватки товара
```bash
curl -X POST "$API_URL/orders" \
  -H "Idempotency-Key: test-stock" \
  -H "Content-Type: application/json" \
  -d "{
    \"user_email\": \"test@example.com\",
    \"items\": [{\"product_id\": \"$PRODUCT_ID\", \"quantity\": 999}]
  }" | jq '.'

# Ожидается: 409 Conflict - "Insufficient stock"
```

### Тест отмены заказа
```bash
# Отмените заказ
curl -X POST "$API_URL/orders/$ORDER_ID/cancel" | jq '.status'

# Проверьте, что товар восстановлен
curl "$API_URL/products" | jq '.[] | select(.id == "'$PRODUCT_ID'") | .stock'
```

### Просмотр метрик
```bash
curl "$API_URL/metrics" | grep -E "^orders_|^outbox_"
```

## 6. Запустите автоматические тесты (1 минута)

```bash
# Быстрый тест API
bash scripts/test_api.sh

# Полные интеграционные тесты (требуется настройка тестовой БД)
pytest tests/ -v
```

## Полный демо-скрипт

Сохраните как `demo.sh` и запустите:

```bash
#!/bin/bash
set -e

API_URL="http://localhost:8000"
ADMIN_SECRET="dev-admin-secret"

echo "🚀 Orders v2 Демо"
echo "================"

# Health check
echo "1. Проверка здоровья..."
curl -s "$API_URL/healthz" | jq '.status'

# Создание продукта
echo "2. Создание продукта..."
PRODUCT=$(curl -s -X POST "$API_URL/admin/products" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Secret: $ADMIN_SECRET" \
  -d '{"name": "Демо Продукт", "price": 100.00, "stock": 10, "is_active": true}')
PRODUCT_ID=$(echo "$PRODUCT" | jq -r '.id')
echo "   ID продукта: $PRODUCT_ID"

# Создание заказа
echo "3. Создание заказа..."
ORDER=$(curl -s -X POST "$API_URL/orders" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: demo-$(date +%s)" \
  -d "{\"user_email\": \"demo@example.com\", \"items\": [{\"product_id\": \"$PRODUCT_ID\", \"quantity\": 2}]}")
ORDER_ID=$(echo "$ORDER" | jq -r '.id')
echo "   ID заказа: $ORDER_ID"
echo "   Статус: $(echo "$ORDER" | jq -r '.status')"

# Тест идемпотентности
echo "4. Тест идемпотентности..."
ORDER2=$(curl -s -X POST "$API_URL/orders" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: demo-$(date +%s)" \
  -d "{\"user_email\": \"demo@example.com\", \"items\": [{\"product_id\": \"$PRODUCT_ID\", \"quantity\": 2}]}")
ORDER_ID2=$(echo "$ORDER2" | jq -r '.id')
echo "   Тот же заказ? $([ "$ORDER_ID" == "$ORDER_ID2" ] && echo "Да ✓" || echo "Нет ✗")"

# Ожидание платежа
echo "5. Ожидание обработки платежа..."
sleep 10

# Проверка финального статуса
FINAL_STATUS=$(curl -s "$API_URL/orders/$ORDER_ID" | jq -r '.status')
echo "   Финальный статус: $FINAL_STATUS"

# Просмотр метрик
echo "6. Метрики:"
curl -s "$API_URL/metrics" | grep -E "^orders_total|^outbox_pending" | head -2

echo ""
echo "✅ Демо завершено!"
echo "   Просмотр логов: docker-compose logs -f app"
echo "   API документация: http://localhost:8000/docs"
```

## Что дальше?

### Исследуйте API
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Прочитайте документацию
- `README.md` - Полное руководство
- `API_EXAMPLES.md` - Все API эндпоинты
- `ACCEPTANCE_TESTS.md` - Тестовые сценарии

### Погрузитесь в код
- `app/services/order_service.py` - Логика создания заказов
- `app/workers/outbox_worker.py` - Фоновый воркер
- `app/repositories/` - Паттерны доступа к данным

### Запустите полный набор тестов
```bash
# Интеграционные тесты
pytest tests/integration/ -v

# С покрытием
pytest tests/ --cov=app --cov-report=html

# Просмотр отчета покрытия
open htmlcov/index.html  # или start htmlcov/index.html на Windows
```

## Устранение неполадок

### Сервисы не запускаются
```bash
# Проверьте Docker
docker-compose ps

# Просмотр логов
docker-compose logs

# Перезапуск
docker-compose down -v
docker-compose up -d
```

### Не удается подключиться к БД
```bash
# Проверьте PostgreSQL
docker-compose logs postgres

# Подключитесь вручную
docker-compose exec postgres psql -U user orders_db
```

### Redis не работает
```bash
# Проверьте Redis
docker-compose exec redis redis-cli ping

# Должно вернуть: PONG
```

### Outbox воркер не обрабатывает
```bash
# Проверьте логи воркера
docker-compose logs app | grep -i outbox

# Проверьте таблицу outbox
docker-compose exec postgres psql -U user orders_db -c \
  "SELECT id, event_type, status, attempts FROM outbox;"
```

## Остановка сервиса

```bash
# Остановить сервисы (сохранить данные)
docker-compose down

# Остановить и удалить данные
docker-compose down -v
```

## Краткая справка

### Переменные окружения
```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/orders_db
REDIS_URL=redis://localhost:6379/0
ADMIN_SECRET=dev-admin-secret
PAYMENT_WEBHOOK_SECRET=dev-webhook-secret
RATE_LIMIT_ORDERS_PER_MINUTE=5
```

### Ключевые эндпоинты
- **Здоровье**: GET /healthz
- **Метрики**: GET /metrics
- **Продукты**: GET /products
- **Создать заказ**: POST /orders (требуется Idempotency-Key)
- **Получить заказ**: GET /orders/{id}
- **Отменить заказ**: POST /orders/{id}/cancel

### Полезные команды
```bash
# Просмотр логов
docker-compose logs -f app

# Запуск тестов
make test

# Форматирование кода
make format

# Проверка типов
make typecheck

# Загрузка тестовых данных
make seed
```

---

**Нужна помощь?** Смотрите `README.md` для подробной документации.

**Готовы к развертыванию?** Смотрите production checklist в `README.md`.
