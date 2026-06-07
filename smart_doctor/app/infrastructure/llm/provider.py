from typing import Protocol, AsyncIterator

from app.config import get_settings
from app.infrastructure.llm.openai_provider import OpenAIProvider


class LLMProvider(Protocol):
    async def chat(self, messages: list[dict], **kwargs) -> str: ...
    async def chat_stream(self, messages: list[dict], **kwargs) -> AsyncIterator[str]: ...


def create_llm() -> LLMProvider:
    settings = get_settings()
    provider = settings.llm_provider
    model = settings.llm_model

    if provider == "openai":
        return OpenAIProvider(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=model,
        )
    if provider == "qwen":
        return OpenAIProvider(
            api_key=settings.qwen_api_key,
            base_url=settings.qwen_base_url,
            model=model,
        )
    if provider == "zhipu":
        return OpenAIProvider(
            api_key=settings.zhipu_api_key,
            base_url=settings.zhipu_base_url,
            model=model,
        )
    raise ValueError(f"Unknown LLM provider: {provider}")
