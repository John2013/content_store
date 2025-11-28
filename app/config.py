from functools import lru_cache
from pydantic import AnyUrl, BaseSettings


class Settings(BaseSettings):
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "cursor_test"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "1"

    # Auth / security
    SECRET_KEY: str = "CHANGE_ME_SECRET_KEY"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    @property
    def database_url_async(self) -> AnyUrl:
        # asyncpg + SQLAlchemy URL
        return AnyUrl.build(
            scheme="postgresql+asyncpg",
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            user=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            path=f"/{self.POSTGRES_DB}",
        )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
