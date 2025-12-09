# Приемочные тестовые сценарии

Подробные сценарии приемочного тестирования сервиса Orders v2.

## Требования

```bash
# Запустить сервисы
docker-compose up -d

# Дождаться готовности сервисов
sleep 10

# Проверить здоровье
curl http://localhost:8000/healthz
```

## Сценарий 1: Успешный путь - Успешный заказ

**Цель**: Создать продукт, разместить заказ, проверить успешную оплату

```bash
#!/bin/bash
set -e

API_URL="http://localhost:8000"
ADMIN_SECRET="dev-admin-secret"

echo "=== Сценарий 1: Успешный путь ==="

# Шаг 1: Создать продукт
echo "1. Создание продукта..."
PRODUCT=$(curl -s -X POST "$API_URL/admin/products" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Secret: $ADMIN_SECRET" \
  -d '{
    "name": "Тестовый ноутбук",
    "price": 1000.00,
    "stock": 10,
    "is_active": true
  }')

PRODUCT_ID=$(echo "$PRODUCT" | jq -r '.id')
echo "✓ Продукт создан: $PRODUCT_ID"

# Шаг 2: Проверить список продуктов
echo "2. Проверка списка продуктов..."
PRODUCTS=$(curl -s "$API_URL/products?is_active=true")
COUNT=$(echo "$PRODUCTS" | jq 'length')
echo "✓ Найдено $COUNT активных продуктов"

# Шаг 3: Создать заказ
echo "3. Создание заказа..."
ORDER=$(curl -s -X POST "$API_URL/orders" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: acceptance-test-1" \
  -d "{
    \"user_email\": \"customer@example.com\",
    \"items\": [
      {
        \"product_id\": \"$PRODUCT_ID\",
        \"quantity\": 2
      }
    ]
  }")

ORDER_ID=$(echo "$ORDER" | jq -r '.id')
ORDER_STATUS=$(echo "$ORDER" | jq -r '.status')
ORDER_TOTAL=$(echo "$ORDER" | jq -r '.items_total')

echo "✓ Заказ создан: $ORDER_ID"
echo "  Статус: $ORDER_STATUS"
echo "  Сумма: \$$ORDER_TOTAL"

# Шаг 4: Проверить резервирование товара
echo "4. Проверка резервирования товара..."
PRODUCT_UPDATED=$(curl -s "$API_URL/products" | jq ".[] | select(.id == \"$PRODUCT_ID\")")
NEW_STOCK=$(echo "$PRODUCT_UPDATED" | jq -r '.stock')
echo "✓ Товар обновлен: 10 → $NEW_STOCK (ожидается: 8)"

if [ "$NEW_STOCK" -ne 8 ]; then
  echo "✗ Несоответствие товара!"
  exit 1
fi

# Шаг 5: Дождаться обработки платежа
echo "5. Ожидание обработки платежа (10с)..."
sleep 10

# Шаг 6: Проверить оплату заказа
echo "6. Проверка финального статуса заказа..."
FINAL_ORDER=$(curl -s "$API_URL/orders/$ORDER_ID")
FINAL_STATUS=$(echo "$FINAL_ORDER" | jq -r '.status')

echo "✓ Финальный статус: $FINAL_STATUS"

if [ "$FINAL_STATUS" == "paid" ]; then
  echo "✓✓✓ УСПЕХ: Заказ успешно завершен!"
elif [ "$FINAL_STATUS" == "canceled" ]; then
  echo "⚠ Заказ был отменен (платеж не прошел - это нормально для теста)"
else
  echo "⚠ Неожиданный статус: $FINAL_STATUS"
fi

echo ""
```

**Ожидаемые результаты**:
- ✅ Продукт создан с stock=10
- ✅ Заказ создан со статусом=reserved
- ✅ Товар уменьшился до 8
- ✅ Заказ переходит в paid (80% вероятность) или canceled (20% вероятность)

## Сценарий 2: Идемпотентность

**Цель**: Проверить, что дублирующие запросы возвращают тот же заказ

```bash
echo "=== Сценарий 2: Идемпотентность ==="

IDEMPOTENCY_KEY="test-idempotency-$(date +%s)"

# Первый запрос
echo "1. Первый запрос..."
ORDER1=$(curl -s -X POST "$API_URL/orders" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $IDEMPOTENCY_KEY" \
  -d "{
    \"user_email\": \"test@example.com\",
    \"items\": [{\"product_id\": \"$PRODUCT_ID\", \"quantity\": 1}]
  }")

ORDER_ID1=$(echo "$ORDER1" | jq -r '.id')
echo "✓ Заказ 1: $ORDER_ID1"

# Второй запрос (дубликат)
echo "2. Дублирующий запрос (те же данные)..."
ORDER2=$(curl -s -X POST "$API_URL/orders" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $IDEMPOTENCY_KEY" \
  -d "{
    \"user_email\": \"test@example.com\",
    \"items\": [{\"product_id\": \"$PRODUCT_ID\", \"quantity\": 1}]
  }")

ORDER_ID2=$(echo "$ORDER2" | jq -r '.id')
echo "✓ Заказ 2: $ORDER_ID2"

# Проверить, что вернулся тот же заказ
if [ "$ORDER_ID1" == "$ORDER_ID2" ]; then
  echo "✓✓✓ УСПЕХ: Вернулся тот же заказ для дублирующего запроса"
else
  echo "✗✗✗ ОШИБКА: Вернулись разные заказы!"
  exit 1
fi

# Третий запрос (другие данные, тот же ключ)
echo "3. Запрос с тем же ключом но другими данными..."
ORDER3=$(curl -s -X POST "$API_URL/orders" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $IDEMPOTENCY_KEY" \
  -d "{
    \"user_email\": \"different@example.com\",
    \"items\": [{\"product_id\": \"$PRODUCT_ID\", \"quantity\": 2}]
  }")

ERROR=$(echo "$ORDER3" | jq -r '.detail // empty')

if [[ "$ERROR" == *"conflict"* ]]; then
  echo "✓✓✓ УСПЕХ: Обнаружен конфликт ключа идемпотентности"
else
  echo "✗✗✗ ОШИБКА: Должен вернуть 409 conflict"
  exit 1
fi

echo ""
```

**Ожидаемые результаты**:
- ✅ Дублирующий запрос возвращает тот же ID заказа
- ✅ Другие данные с тем же ключом возвращают 409 Conflict

## Сценарий 3: Недостаточно товара

**Цель**: Проверить работу валидации товара

```bash
echo "=== Сценарий 3: Недостаточно товара ==="

# Получить текущий товар
CURRENT_STOCK=$(curl -s "$API_URL/products" | jq -r ".[] | select(.id == \"$PRODUCT_ID\") | .stock")
echo "Текущий товар: $CURRENT_STOCK"

# Попытаться заказать больше, чем доступно
echo "Попытка заказать $(($CURRENT_STOCK + 1)) единиц..."
RESULT=$(curl -s -X POST "$API_URL/orders" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: insufficient-stock-test" \
  -d "{
    \"user_email\": \"test@example.com\",
    \"items\": [{\"product_id\": \"$PRODUCT_ID\", \"quantity\": $(($CURRENT_STOCK + 1))}]
  }")

ERROR=$(echo "$RESULT" | jq -r '.detail // empty')

if [[ "$ERROR" == *"Insufficient stock"* ]]; then
  echo "✓✓✓ УСПЕХ: Возвращена ошибка недостаточного товара"
else
  echo "✗✗✗ ОШИБКА: Должна вернуться ошибка недостаточного товара"
  echo "Ответ: $RESULT"
  exit 1
fi

echo ""
```

**Ожидаемые результаты**:
- ✅ Возвращает 409 Conflict с сообщением "Insufficient stock"
- ✅ Товар остается без изменений

## Сценарий 4: Конкурентное резервирование товара

**Цель**: Проверить отсутствие race conditions в управлении товаром

```bash
echo "=== Сценарий 4: Конкурентное резервирование товара ==="

# Создать продукт с только 1 единицей
echo "Создание продукта с stock=1..."
LIMITED_PRODUCT=$(curl -s -X POST "$API_URL/admin/products" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Secret: $ADMIN_SECRET" \
  -d '{
    "name": "Ограниченный товар '"$(date +%s)"'",
    "price": 50.00,
    "stock": 1,
    "is_active": true
  }')

LIMITED_ID=$(echo "$LIMITED_PRODUCT" | jq -r '.id')
echo "✓ Ограниченный продукт: $LIMITED_ID (stock=1)"

# Отправить 5 конкурентных запросов
echo "Отправка 5 конкурентных запросов на тот же товар..."

for i in {1..5}; do
  curl -s -X POST "$API_URL/orders" \
    -H "Content-Type: application/json" \
    -H "Idempotency-Key: concurrent-$i" \
    -d "{
      \"user_email\": \"test$i@example.com\",
      \"items\": [{\"product_id\": \"$LIMITED_ID\", \"quantity\": 1}]
    }" > /tmp/order_$i.json &
done

wait

# Подсчитать успешные заказы
SUCCESS_COUNT=0
for i in {1..5}; do
  STATUS=$(cat /tmp/order_$i.json | jq -r '.status // "error"')
  if [ "$STATUS" == "reserved" ]; then
    SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
  fi
done

echo "Успешных заказов: $SUCCESS_COUNT (ожидается: 1)"

if [ "$SUCCESS_COUNT" -eq 1 ]; then
  echo "✓✓✓ УСПЕХ: Только один заказ успешен (нет race condition)"
else
  echo "✗✗✗ ОШИБКА: Несколько заказов успешны (обнаружена race condition!)"
  exit 1
fi

# Проверить, что финальный товар = 0
FINAL_STOCK=$(curl -s "$API_URL/products" | jq -r ".[] | select(.id == \"$LIMITED_ID\") | .stock")
echo "Финальный товар: $FINAL_STOCK (ожидается: 0)"

if [ "$FINAL_STOCK" -eq 0 ]; then
  echo "✓✓✓ УСПЕХ: Товар управляется правильно"
else
  echo "✗✗✗ ОШИБКА: Несоответствие товара!"
  exit 1
fi

echo ""
```

**Ожидаемые результаты**:
- ✅ Только 1 из 5 конкурентных запросов успешен
- ✅ Финальный товар = 0
- ✅ Остальные 4 запроса получают 409 Conflict

## Сценарий 5: Отмена заказа

**Цель**: Проверить восстановление товара при отмене

```bash
echo "=== Сценарий 5: Отмена заказа ==="

# Создать заказ
echo "1. Создание заказа..."
CANCEL_ORDER=$(curl -s -X POST "$API_URL/orders" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: cancel-test-$(date +%s)" \
  -d "{
    \"user_email\": \"cancel@example.com\",
    \"items\": [{\"product_id\": \"$PRODUCT_ID\", \"quantity\": 3}]
  }")

CANCEL_ORDER_ID=$(echo "$CANCEL_ORDER" | jq -r '.id')
echo "✓ Заказ создан: $CANCEL_ORDER_ID"

# Проверить товар до отмены
STOCK_BEFORE=$(curl -s "$API_URL/products" | jq -r ".[] | select(.id == \"$PRODUCT_ID\") | .stock")
echo "Товар до отмены: $STOCK_BEFORE"

# Отменить заказ
echo "2. Отмена заказа..."
CANCELED=$(curl -s -X POST "$API_URL/orders/$CANCEL_ORDER_ID/cancel")
CANCEL_STATUS=$(echo "$CANCELED" | jq -r '.status')

if [ "$CANCEL_STATUS" != "canceled" ]; then
  echo "✗ Не удалось отменить заказ"
  exit 1
fi

echo "✓ Заказ отменен"

# Проверить товар после отмены
STOCK_AFTER=$(curl -s "$API_URL/products" | jq -r ".[] | select(.id == \"$PRODUCT_ID\") | .stock")
echo "Товар после отмены: $STOCK_AFTER"

# Проверить восстановление товара
EXPECTED_STOCK=$((STOCK_BEFORE + 3))
if [ "$STOCK_AFTER" -eq "$EXPECTED_STOCK" ]; then
  echo "✓✓✓ УСПЕХ: Товар восстановлен ($STOCK_BEFORE + 3 = $STOCK_AFTER)"
else
  echo "✗✗✗ ОШИБКА: Товар не восстановлен правильно"
  exit 1
fi

echo ""
```

**Ожидаемые результаты**:
- ✅ Статус заказа меняется на canceled
- ✅ Товар восстановлен на +3

## Сценарий 6: Webhook платежей - Успех

**Цель**: Проверить обновление заказа при успешном webhook платежа

```bash
echo "=== Сценарий 6: Webhook платежей - Успех ==="

# Создать заказ
WEBHOOK_ORDER=$(curl -s -X POST "$API_URL/orders" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: webhook-success-$(date +%s)" \
  -d "{
    \"user_email\": \"webhook@example.com\",
    \"items\": [{\"product_id\": \"$PRODUCT_ID\", \"quantity\": 1}]
  }")

WEBHOOK_ORDER_ID=$(echo "$WEBHOOK_ORDER" | jq -r '.id')
echo "Заказ создан: $WEBHOOK_ORDER_ID"

# Вручную отправить успешный webhook
echo "Отправка успешного webhook..."
curl -s -X POST "$API_URL/payments/callback" \
  -H "Content-Type: application/json" \
  -d "{
    \"payment_id\": \"manual-pay-$(date +%s)\",
    \"order_id\": \"$WEBHOOK_ORDER_ID\",
    \"status\": \"success\"
  }" > /dev/null

sleep 1

# Проверить статус заказа
FINAL_STATUS=$(curl -s "$API_URL/orders/$WEBHOOK_ORDER_ID" | jq -r '.status')

if [ "$FINAL_STATUS" == "paid" ]; then
  echo "✓✓✓ УСПЕХ: Заказ отмечен как оплаченный"
else
  echo "✗✗✗ ОШИБКА: Статус заказа $FINAL_STATUS (ожидается: paid)"
  exit 1
fi

echo ""
```

**Ожидаемые результаты**:
- ✅ Статус заказа меняется на "paid"
- ✅ Товар остается зарезервированным

## Сценарий 7: Webhook платежей - Неудача

**Цель**: Проверить восстановление товара при неудачном платеже

```bash
echo "=== Сценарий 7: Webhook платежей - Неудача ==="

# Получить товар до
STOCK_BEFORE=$(curl -s "$API_URL/products" | jq -r ".[] | select(.id == \"$PRODUCT_ID\") | .stock")

# Создать заказ
FAIL_ORDER=$(curl -s -X POST "$API_URL/orders" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: webhook-fail-$(date +%s)" \
  -d "{
    \"user_email\": \"fail@example.com\",
    \"items\": [{\"product_id\": \"$PRODUCT_ID\", \"quantity\": 2}]
  }")

FAIL_ORDER_ID=$(echo "$FAIL_ORDER" | jq -r '.id')
echo "Заказ создан: $FAIL_ORDER_ID"

STOCK_AFTER_ORDER=$(curl -s "$API_URL/products" | jq -r ".[] | select(.id == \"$PRODUCT_ID\") | .stock")
echo "Товар после заказа: $STOCK_BEFORE → $STOCK_AFTER_ORDER"

# Отправить неудачный webhook
echo "Отправка неудачного webhook..."
curl -s -X POST "$API_URL/payments/callback" \
  -H "Content-Type: application/json" \
  -d "{
    \"payment_id\": \"manual-fail-$(date +%s)\",
    \"order_id\": \"$FAIL_ORDER_ID\",
    \"status\": \"failed\"
  }" > /dev/null

sleep 1

# Проверить статус заказа
FINAL_STATUS=$(curl -s "$API_URL/orders/$FAIL_ORDER_ID" | jq -r '.status')
STOCK_AFTER_FAIL=$(curl -s "$API_URL/products" | jq -r ".[] | select(.id == \"$PRODUCT_ID\") | .stock")

echo "Статус заказа: $FINAL_STATUS"
echo "Товар восстановлен: $STOCK_AFTER_ORDER → $STOCK_AFTER_FAIL"

if [ "$FINAL_STATUS" == "canceled" ] && [ "$STOCK_AFTER_FAIL" -eq "$STOCK_BEFORE" ]; then
  echo "✓✓✓ УСПЕХ: Заказ отменен и товар восстановлен"
else
  echo "✗✗✗ ОШИБКА: Компенсация не сработала правильно"
  exit 1
fi

echo ""
```

**Ожидаемые результаты**:
- ✅ Статус заказа меняется на "canceled"
- ✅ Товар восстанавливается до исходного значения

## Мониторинг во время тестов

**Просмотр логов**:
```bash
docker-compose logs -f app
```

**Проверка метрик**:
```bash
watch -n 2 "curl -s http://localhost:8000/metrics | grep -E '^orders_|^outbox_|^worker_'"
```

**Проверка базы данных**:
```bash
docker-compose exec postgres psql -U user orders_db -c "
  SELECT status, COUNT(*) FROM orders GROUP BY status;
"
```

## Очистка

```bash
docker-compose down -v
```
