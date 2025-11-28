from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.session import engine
from app.user.routes import router as user_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    async with engine.begin() as conn:
        # опционально: проверка, что БД доступна
        await conn.run_sync(lambda _: None)
    yield
    # shutdown
    await engine.dispose()


app = FastAPI(lifespan=lifespan)

app.include_router(user_router, prefix="/api")
