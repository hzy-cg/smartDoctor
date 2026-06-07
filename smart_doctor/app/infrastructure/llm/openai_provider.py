from typing import AsyncIterator
import asyncio
import logging
from openai import AsyncOpenAI
from openai import RateLimitError, APIConnectionError, APITimeoutError

logger = logging.getLogger(__name__)


class OpenAIProvider:
    def __init__(self, api_key: str, base_url: str, model: str,
                 max_retries: int = 3, timeout: float = 30.0):
        self._model = model
        self._client = AsyncOpenAI(
            api_key=api_key, base_url=base_url, timeout=timeout,
        )
        self._max_retries = max_retries

    _RETRYABLE_ERRORS = (RateLimitError, APIConnectionError, APITimeoutError)

    async def chat(self, messages: list[dict], **kwargs) -> str:
        for attempt in range(self._max_retries):
            try:
                response = await self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    **kwargs,
                )
                return response.choices[0].message.content or ""
            except self._RETRYABLE_ERRORS:
                if attempt == self._max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
            except Exception:
                raise

    async def chat_stream(self, messages: list[dict], **kwargs) -> AsyncIterator[str]:
        for attempt in range(self._max_retries):
            try:
                stream = await self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    stream=True,
                    **kwargs,
                )
                async for chunk in stream:
                    content = chunk.choices[0].delta.content
                    if content:
                        yield content
                return
            except self._RETRYABLE_ERRORS:
                if attempt == self._max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
            except Exception:
                raise
