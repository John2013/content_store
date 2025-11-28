## cursor-test FastAPI app

Простой пример FastAPI-приложения с:
- **async PostgreSQL** (SQLAlchemy + asyncpg)
- **Alembic** миграциями
- **JWT-аутентификацией** и моделью пользователя.

### 1. Установка и инициализация

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows PowerShell

pip install -e .
```

Или, если используешь `uv`:

```bash
uv sync
```

### 2. Настройка переменных окружения

Создай файл `.env` в корне проекта:

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=cursor_test
POSTGRES_USER=postgres
POSTGRES_PASSWORD=1

SECRET_KEY=замени_на_свой_секрет
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### 3. Миграции Alembic

Прогони миграции (из корня проекта, при активном виртуальном окружении):

```bash
alembic upgrade head
```

### 4. Запуск приложения

Запусти FastAPI с Uvicorn:

```bash
uvicorn app.main:app --reload
```

После запуска:
- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

### 5. API Endpoints

#### Пользователи

**Публичные (без авторизации):**
- `POST /api/users/register` — регистрация пользователя (email + password).
- `POST /api/users/login` — логин, выдаёт JWT (`access_token`).

**Защищённые (требуют `Authorization: Bearer <token>`):**
- `GET /api/users/me` — получить данные текущего пользователя.
- `GET /api/users/` — получить список всех пользователей.
- `GET /api/users/{user_id}` — получить пользователя по ID.
- `PUT /api/users/{user_id}` — обновить пользователя (email, is_active).
- `DELETE /api/users/{user_id}` — удалить пользователя.

#### Магазин цифрового контента

**Публичные (без авторизации):**
- `GET /api/store/categories` — список категорий товаров.
- `GET /api/store/products` — список товаров (опционально: `?category_id=1`).
- `GET /api/store/products/{id}` — детали товара (без текста контента).
- `GET /api/store/products/{id}/reviews` — отзывы на товар.

**Корзина (без авторизации, но нужен `session_id`):**
- `GET /api/store/cart?session_id={id}` — получить корзину.
- `POST /api/store/cart` — добавить товар в корзину (автоматически создаёт `session_id` если не указан).
- `DELETE /api/store/cart/{item_id}` — удалить элемент из корзины.
- `DELETE /api/store/cart?session_id={id}` — очистить корзину.

**Заказы (требуют авторизации):**
- `POST /api/store/orders` — создать заказ из корзины (можно указать `session_id` для анонимной корзины).
- `GET /api/store/orders` — список заказов пользователя.
- `GET /api/store/orders/{id}` — детали заказа.
- `POST /api/store/orders/{id}/pay` — фиктивная оплата заказа (генерирует `payment_id`).

**Покупки (требуют авторизации):**
- `GET /api/store/purchases` — история покупок пользователя.
- `GET /api/store/purchases/{order_id}/content` — получить текст контента для оплаченного заказа.

**Отзывы (требуют авторизации и покупки товара):**
- `POST /api/store/products/{id}/reviews` — оставить отзыв (rating 1-5, comment).
- `PUT /api/store/reviews/{id}` — обновить свой отзыв.
- `DELETE /api/store/reviews/{id}` — удалить свой отзыв.

### 6. Пример использования API магазина

```bash
# 1. Регистрация и авторизация
curl -X POST "http://localhost:8000/api/users/register" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}'

curl -X POST "http://localhost:8000/api/users/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=password123"
# Получаем access_token

# 2. Просмотр товаров
curl "http://localhost:8000/api/store/products"

# 3. Добавление в корзину (без авторизации)
curl -X POST "http://localhost:8000/api/store/cart" \
  -H "Content-Type: application/json" \
  -d '{"product_id": 1, "quantity": 1}'
# Получаем session_id в ответе или генерируем сами

# 4. Создание заказа (с авторизацией)
curl -X POST "http://localhost:8000/api/store/orders" \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "your-session-id"}'

# 5. Оплата заказа
curl -X POST "http://localhost:8000/api/store/orders/{order_id}/pay" \
  -H "Authorization: Bearer {access_token}"

# 6. Получение контента
curl "http://localhost:8000/api/store/purchases/{order_id}/content" \
  -H "Authorization: Bearer {access_token}"

# 7. Оставить отзыв
curl -X POST "http://localhost:8000/api/store/products/{product_id}/reviews" \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{"rating": 5, "comment": "Отличный контент!"}'
```

### 7. Тестирование

Запуск тестов:

```bash
pytest -q
```

Тесты покрывают:
- Регистрацию и авторизацию
- Защищённые эндпоинты (требующие JWT токен)
- CRUD операции с пользователями
- Публичные endpoints магазина
- Работу с корзиной (с session_id)
- Создание заказов и оплату
- Доступ к купленному контенту
- Отзывы на товары
- Обработку ошибок (404, 401, 403)


