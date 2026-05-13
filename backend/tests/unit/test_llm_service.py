"""Unit tests for LLMService — retry, multi-model, encryption."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.services.llm_service import LLMService, _encrypt_api_key, _decrypt_api_key


class TestEncryptDecrypt:
    def test_encrypt_decrypt_with_secret_key(self) -> None:
        """XOR encryption/decryption round-trip with secret key."""
        with patch("app.services.llm_service.settings") as mock_settings:
            mock_settings.app_secret_key = "test-secret-key-32-bytes-long!!"
            plaintext = "sk-test-api-key-12345"
            encrypted = _encrypt_api_key(plaintext)
            assert encrypted != plaintext
            assert encrypted.startswith("enc:")
            decrypted = _decrypt_api_key(encrypted)
            assert decrypted == plaintext

    def test_decrypt_without_secret_key(self) -> None:
        """Falls back to plaintext when no secret key is set."""
        with patch("app.services.llm_service.settings") as mock_settings:
            mock_settings.app_secret_key = ""
            plaintext = "my-api-key"
            encrypted = _encrypt_api_key(plaintext)
            assert encrypted == plaintext
            decrypted = _decrypt_api_key(encrypted)
            assert decrypted == plaintext


class TestLLMServiceCrud:
    @pytest.fixture(autouse=True)
    def _patch_app_data(self, tmp_path):
        """Redirect LLM config storage to temp directory."""
        with patch("app.services.llm_service.settings") as mock_settings:
            mock_settings.app_secret_key = ""
            mock_settings.app_data_dir = str(tmp_path)
            with patch("app.core.config.ensure_app_data_dir") as mock_ensure:
                mock_ensure.return_value = tmp_path
                yield

    def test_add_and_list_configs(self) -> None:
        """Config can be added and listed."""
        result = LLMService.add_config(
            name="Test Model",
            provider="anthropic",
            model="claude-test",
            url="https://api.test.com",
            api_key="sk-test",
        )
        configs = LLMService.list_configs()
        assert len(configs) == 1
        assert configs[0]["name"] == "Test Model"

    def test_set_default_is_unique(self) -> None:
        """Setting a new default unsets the previous one."""
        LLMService.add_config(name="Model A", provider="anthropic", model="a", url="http://a", api_key="k")
        LLMService.add_config(name="Model B", provider="openai_compatible", model="b", url="http://b", api_key="k")
        configs = LLMService.list_configs()
        LLMService.set_default(configs[1]["id"])
        updated = LLMService.list_configs()
        defaults = [c for c in updated if c.get("is_default")]
        assert len(defaults) == 1
        assert defaults[0]["name"] == "Model B"

    def test_get_default_returns_first_if_no_default(self) -> None:
        """If no config is marked default, returns the first one."""
        LLMService.add_config(name="First", provider="anthropic", model="f", url="http://f", api_key="k")
        default = LLMService.get_default_config()
        assert default is not None
        assert default["name"] == "First"

    def test_delete_config(self) -> None:
        """Config is removed from list."""
        config_id = LLMService.add_config(name="ToDelete", provider="anthropic", model="x", url="http://x", api_key="k")
        LLMService.delete_config(config_id)
        assert len(LLMService.list_configs()) == 0


class TestLLMClient:
    async def test_connection_success(self, tmp_path) -> None:
        """Test connection returns ok with latency."""
        with patch("app.services.llm_service.settings") as mock_settings:
            mock_settings.app_secret_key = ""
            mock_settings.app_data_dir = str(tmp_path)
            with patch("app.core.config.ensure_app_data_dir") as mock_ensure:
                mock_ensure.return_value = tmp_path
                LLMService.add_config(name="Test", provider="anthropic", model="t", url="http://t", api_key="k")
                configs = LLMService.list_configs()

                mock_client = AsyncMock()
                mock_client.test_connection = AsyncMock(return_value={"ok": True, "latency_ms": 150})
                with patch("app.services.llm_service.model_router") as mock_router:
                    mock_router.get_client.return_value = mock_client
                    result = await LLMService.test_connection(configs[0]["id"])
                    assert result["ok"] is True

    async def test_connection_failure(self, tmp_path) -> None:
        """Test connection returns error on failure."""
        with patch("app.services.llm_service.settings") as mock_settings:
            mock_settings.app_secret_key = ""
            mock_settings.app_data_dir = str(tmp_path)
            with patch("app.core.config.ensure_app_data_dir") as mock_ensure:
                mock_ensure.return_value = tmp_path
                LLMService.add_config(name="Test", provider="anthropic", model="t", url="http://t", api_key="k")
                configs = LLMService.list_configs()

                mock_client = AsyncMock()
                mock_client.test_connection = AsyncMock(side_effect=RuntimeError("API error"))
                with patch("app.services.llm_service.model_router") as mock_router:
                    mock_router.get_client.return_value = mock_client
                    result = await LLMService.test_connection(configs[0]["id"])
                    assert result["ok"] is False
                    assert "error" in result
