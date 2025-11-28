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

#### Публичные (без авторизации):
- `POST /api/users/register` — регистрация пользователя (email + password).
- `POST /api/users/login` — логин, выдаёт JWT (`access_token`).

#### Защищённые (требуют `Authorization: Bearer <token>`):
- `GET /api/users/me` — получить данные текущего пользователя.
- `GET /api/users/` — получить список всех пользователей.
- `GET /api/users/{user_id}` — получить пользователя по ID.
- `PUT /api/users/{user_id}` — обновить пользователя (email, is_active).
- `DELETE /api/users/{user_id}` — удалить пользователя.

### 6. Тестирование

Запуск тестов:

```bash
pytest -q
```

Тесты покрывают:
- Регистрацию и авторизацию
- Защищённые эндпоинты (требующие JWT токен)
- CRUD операции с пользователями
- Обработку ошибок (404, 401)


