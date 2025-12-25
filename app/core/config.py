from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "SmartDoc Assistant"

    DASHSCOPE_API_KEY: str
    OPENAI_MODEL: str = "qwen-max"
    OPENAI_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    # 并发控制
    MAX_CONCURRENT_CRAWLS: int = 2

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()