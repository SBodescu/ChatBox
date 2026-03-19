from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    UPLOAD_DIR : str = "files"

    sqlite_database_url: str = "chatbox.db"

    pg_database_url: str | None = None

    voyage_api_key: str

    groq_api_key: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

settings = get_settings()