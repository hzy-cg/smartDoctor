import pytest
import os
from unittest.mock import patch, MagicMock
from uuid import uuid4

from app.config import Settings, get_settings


class TestConfig:

    def test_default_settings(self):
        settings = Settings()
        assert settings.database_url
        assert settings.jwt_algorithm == "HS256"
        assert settings.jwt_expire_minutes == 1440
        assert settings.llm_provider in ("openai", "deepseek")
        assert settings.llm_model in ("gpt-4o-mini", "deepseek-chat")

    def test_custom_settings(self):
        settings = Settings(
            database_url="postgresql://test:test@localhost:5432/test_db",
            secret_key="my-secret-key",
            jwt_expire_minutes=60
        )
        assert settings.database_url == "postgresql://test:test@localhost:5432/test_db"
        assert settings.secret_key == "my-secret-key"
        assert settings.jwt_expire_minutes == 60

    @patch('app.config.Settings')
    def test_get_settings_cached(self, MockSettings):
        mock_instance = MagicMock()
        MockSettings.return_value = mock_instance
        
        s1 = get_settings()
        s2 = get_settings()
        
        assert s1 is s2

    def test_model_config(self):
        settings = Settings()
        assert settings.model_config["env_file"] == ".env"