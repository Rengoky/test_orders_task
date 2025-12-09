# Orders v2 — Reservation + Payments (Saga)

Система управления заказами с резервированием товаров и обработкой платежей по паттерну Saga.

## Основные возможности

- ✅ **Управление продуктами**: Admin API для создания и обновления товаров
- ✅ **Создание заказов**: Атомарное резервирование товара со склада
- ✅ **Интеграция платежей**: Fake payment service с webhook колбэками
- ✅ **Saga паттерн**: Компенсирующие транзакции при неудачной оплате
- ✅ **Идемпотентность**: Защита от дублирующих запросов
- ✅ **Конкурентность**: Row-level блокировки для управления товарами
- ✅ **Outbox паттерн**: Надежная обработка событий с повторными попытками
- ✅ **Rate Limiting**: Redis sliding window для ограничения запросов
- ✅ **Безопасность**: Admin secret, HMAC webhook подписи
- ✅ **Наблюдаемость**: JSON логи, Prometheus метрики, health checks

## Технологии

- **Python 3.11+**, **FastAPI** (async), **PostgreSQL**, **SQLAlchemy 2.0**, **Redis**, **Alembic**

## Быстрый старт

### 1. Запуск через Docker

```bash
# Запустить все сервисы
docker-compose up -d

# Проверить здоровье
curl http://localhost:8000/healthz

# Просмотр логов
docker-compose logs -f app
```

### 2. API документация

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 3. Примеры использования

#### Создать продукт (Admin)
```bash
curl -X POST http://localhost:8000/admin/products \
  -H "Content-Type: application/json" \
  -H "X-Admin-Secret: dev-admin-secret" \
  -d '{
    "name": "Laptop",
    "price": 1500.00,
    "stock": 10
  }'
```

#### Получить список продуктов
```bash
curl "http://localhost:8000/products?is_active=true&limit=20"
```

#### Создать заказ (с идемпотентностью)
```bash
curl -X POST http://localhost:8000/orders \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: unique-key-123" \
  -d '{
    "user_email": "customer@example.com",
    "items": [
      {"product_id": "product-uuid", "quantity": 2}
    ]
  }'
```

#### Получить заказ
```bash
curl http://localhost:8000/orders/{order_id}
```

#### Отменить заказ
```bash
curl -X POST http://localhost:8000/orders/{order_id}/cancel
```

## Архитектура

### Структура проекта
```
app/
├── core/          # Конфигурация, логирование, безопасность
├── models/        # SQLAlchemy модели
├── repositories/  # Слой доступа к данным
├── services/      # Бизнес-логика
├── routers/       # API эндпоинты
├── workers/       # Фоновые воркеры (Outbox)
└── schemas/       # Pydantic схемы
```

### Жизненный цикл заказа

1. **created** → Начальное состояние
2. **reserved** → Товар зарезервирован
3. **payment_pending** → Платеж инициирован через Outbox
4. **paid** → Успешная оплата
5. **canceled** → Неудачная оплата (товар возвращен на склад)

## Ключевые особенности

### Идемпотентность
Повторный запрос с тем же ключом и данными возвращает существующий заказ. Тот же ключ с другими данными → **409 Conflict**.

### Конкурентное резервирование
Два параллельных запроса на последний товар → один успешен, второй получает **409 Insufficient Stock**. Защита через `SELECT ... FOR UPDATE`.

### Rate Limiting
Более 5 заказов в минуту на один email → **429 Too Many Requests**.

### Saga для платежей

**Успешный сценарий**:
1. Заказ создан → `reserved` (товар уменьшен)
2. Outbox воркер инициирует платеж
3. Webhook: `success` → Заказ становится `paid`

**Сценарий с ошибкой** (компенсация):
1. Заказ создан → `reserved` (товар уменьшен)
2. Outbox воркер инициирует платеж
3. Webhook: `failed`
4. **Компенсация**: Товар восстановлен на складе
5. Заказ становится `canceled`

### Outbox паттерн
- События сохраняются в таблице `outbox`
- Фоновый воркер обрабатывает с экспоненциальной задержкой
- Повторные попытки: 1с, 2с, 4с, 8с, 16с
- Dead letter queue после 5 неудач

## Тестирование

### Интеграционные тесты
```bash
# Создать тестовую БД
createdb orders_test_db

# Запустить тесты
pytest tests/ -v

# С покрытием
pytest tests/ --cov=app --cov-report=html
```

### Покрытые сценарии
- ✅ Создание заказа с идемпотентностью
- ✅ Конфликт идемпотентных ключей
- ✅ Недостаточно товара
- ✅ Конкурентное резервирование (race condition)
- ✅ Отмена с восстановлением товара
- ✅ Webhook: success → paid
- ✅ Webhook: failed → компенсация

## Наблюдаемость

### Health Check
```bash
curl http://localhost:8000/healthz
```

### Метрики (Prometheus)
```bash
curl http://localhost:8000/metrics
```

Доступные метрики:
- `orders_total` - Всего заказов создано
- `orders_paid_total` - Оплаченных заказов
- `orders_canceled_total` - Отмененных заказов
- `outbox_pending` - События в очереди
- `worker_errors_total` - Ошибки воркера

## Безопасность

1. **Admin аутентификация**: `X-Admin-Secret` header для admin эндпоинтов
2. **Webhook подписи**: HMAC-SHA256 верификация
3. **SQL Injection**: Защита через SQLAlchemy ORM
4. **Rate Limiting**: Предотвращение злоупотреблений
5. **Идемпотентность**: Защита от дублей
6. **Конкурентность**: Row-level locks
7. **Валидация**: Pydantic схемы для всех входных данных

## Локальная разработка

### Переменные окружения (.env)
```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/orders_db
REDIS_URL=redis://localhost:6379/0
ADMIN_SECRET=dev-admin-secret
PAYMENT_WEBHOOK_SECRET=dev-webhook-secret
LOG_LEVEL=INFO
FAKE_PAYMENT_ENABLED=true
FAKE_PAYMENT_SUCCESS_RATE=0.8
RATE_LIMIT_ORDERS_PER_MINUTE=5
```

### Установка
```bash
# Создать venv
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Установить зависимости
pip install -r requirements.txt

# Запустить миграции
alembic upgrade head

# Запустить сервер
uvicorn app.main:app --reload
```

## Качество кода

```bash
# Форматирование
black app/ tests/

# Линтинг
ruff check app/ tests/

# Проверка типов
mypy app/
```

## Production Checklist

- [ ] Изменить все секреты
- [ ] Настроить `DATABASE_URL` и `REDIS_URL`
- [ ] Настроить бэкапы БД
- [ ] Настроить логирование и мониторинг
- [ ] Масштабировать Outbox воркеры при необходимости
- [ ] Включить HTTPS/TLS
- [ ] Настроить reverse proxy

## Документация

- **FOR_REVIEWER.md** - Руководство для ревьюера
- **PROJECT_SUMMARY.md** - Полная сводка проекта
- **API_EXAMPLES.md** - Детальные примеры API
- **ACCEPTANCE_TESTS.md** - Тестовые сценарии
- **QUICKSTART.md** - 5-минутный старт

---

Реализовано все требования + дополнительные функции (rate limiting, metrics, observability).
