from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.session import engine
from app.user.routes import router as user_router
from app.store.routes import router as store_router


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
app.include_router(store_router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "Hello World"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
