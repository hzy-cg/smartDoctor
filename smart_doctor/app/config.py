from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/smart_doctor"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 120

    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"

    qwen_api_key: str = ""
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    zhipu_api_key: str = ""
    zhipu_base_url: str = "https://open.bigmodel.cn/api/paas/v4"

    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"

    chroma_persist_dir: str = "./data/chroma"
    chroma_embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"

    asr_provider: str = "aliyun"
    aliyun_asr_app_key: str = ""
    aliyun_asr_access_key: str = ""
    aliyun_asr_secret_key: str = ""

    tts_provider: str = "aliyun"
    aliyun_tts_access_key: str = ""
    aliyun_tts_secret_key: str = ""

    data_retention_days: int = 180

    model_config = {"env_file": str(_PROJECT_ROOT / ".env"), "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
