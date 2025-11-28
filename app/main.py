from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.session import engine
# from app.api.routes import router as api_router  # когда появится роутер


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

# app.include_router(api_router, prefix="/api")