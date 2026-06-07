import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.infrastructure.llm.openai_provider import OpenAIProvider
from app.infrastructure.llm.provider import create_llm, LLMProvider


class TestOpenAIProvider:
    def test_init(self):
        provider = OpenAIProvider(api_key="test-key", base_url="http://test", model="gpt-4o-mini")
        assert provider._model == "gpt-4o-mini"
        assert provider._max_retries == 3

    @pytest.mark.asyncio
    async def test_chat_success(self):
        provider = OpenAIProvider(api_key="test-key", base_url="http://test", model="gpt-4o-mini")
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "你好"
        provider._client = AsyncMock()
        provider._client.chat.completions.create.return_value = mock_response
        result = await provider.chat([{"role": "user", "content": "你好"}])
        assert result == "你好"

    @pytest.mark.asyncio
    async def test_chat_empty_response(self):
        provider = OpenAIProvider(api_key="test-key", base_url="http://test", model="gpt-4o-mini")
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None
        provider._client = AsyncMock()
        provider._client.chat.completions.create.return_value = mock_response
        result = await provider.chat([{"role": "user", "content": "你好"}])
        assert result == ""

    @pytest.mark.asyncio
    async def test_chat_retry_on_failure(self):
        provider = OpenAIProvider(api_key="test-key", base_url="http://test", model="gpt-4o-mini", max_retries=2)
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "重试成功"
        provider._client = AsyncMock()
        provider._client.chat.completions.create.side_effect = [
            Exception("timeout"),
            mock_response,
        ]
        result = await provider.chat([{"role": "user", "content": "你好"}])
        assert result == "重试成功"

    @pytest.mark.asyncio
    async def test_chat_all_retries_fail(self):
        provider = OpenAIProvider(api_key="test-key", base_url="http://test", model="gpt-4o-mini", max_retries=2)
        provider._client = AsyncMock()
        provider._client.chat.completions.create.side_effect = Exception("fail")
        with pytest.raises(Exception, match="fail"):
            await provider.chat([{"role": "user", "content": "你好"}])


class TestCreateLLM:
    def test_create_openai(self):
        from unittest.mock import patch
        with patch("app.infrastructure.llm.provider.get_settings") as mock_settings:
            s = MagicMock()
            s.llm_provider = "openai"
            s.llm_model = "gpt-4o-mini"
            s.openai_api_key = "test-key"
            s.openai_base_url = "https://api.openai.com/v1"
            mock_settings.return_value = s
            provider = create_llm()
            assert isinstance(provider, OpenAIProvider)

    def test_create_qwen(self):
        from unittest.mock import patch
        with patch("app.infrastructure.llm.provider.get_settings") as mock_settings:
            s = MagicMock()
            s.llm_provider = "qwen"
            s.llm_model = "qwen-plus"
            s.qwen_api_key = "test-key"
            s.qwen_base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
            mock_settings.return_value = s
            provider = create_llm()
            assert isinstance(provider, OpenAIProvider)

    def test_create_zhipu(self):
        from unittest.mock import patch
        with patch("app.infrastructure.llm.provider.get_settings") as mock_settings:
            s = MagicMock()
            s.llm_provider = "zhipu"
            s.llm_model = "glm-4"
            s.zhipu_api_key = "test-key"
            s.zhipu_base_url = "https://open.bigmodel.cn/api/paas/v4"
            mock_settings.return_value = s
            provider = create_llm()
            assert isinstance(provider, OpenAIProvider)

    def test_create_unknown_provider(self):
        from unittest.mock import patch
        with patch("app.infrastructure.llm.provider.get_settings") as mock_settings:
            s = MagicMock()
            s.llm_provider = "unknown"
            s.llm_model = "test"
            mock_settings.return_value = s
            with pytest.raises(ValueError, match="Unknown LLM provider"):
                create_llm()