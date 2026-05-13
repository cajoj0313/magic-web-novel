"""Integration tests for LLM config API."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


class TestLLMConfigsAPI:
    async def test_llm_configs_crud(self, fastapi_client, tmp_path) -> None:
        """Full add → list → update → delete cycle."""
        with patch("app.services.llm_service.settings") as mock_settings:
            mock_settings.app_secret_key = ""
            mock_settings.app_data_dir = str(tmp_path)
            with patch("app.core.config.ensure_app_data_dir") as mock_ensure:
                mock_ensure.return_value = tmp_path
                # Add
                resp = await fastapi_client.post("/api/llm-configs/add", json={
                    "name": "Test Model",
                    "provider": "anthropic",
                    "model": "claude-test",
                    "url": "https://api.anthropic.com",
                    "api_key": "sk-test-key",
                })
                data = resp.json()
                config_id = data["id"]

                # List
                resp = await fastapi_client.post("/api/llm-configs/list", json={})
                data = resp.json()
                assert len(data["configs"]) == 1
                assert data["configs"][0]["name"] == "Test Model"

                # Delete
                resp = await fastapi_client.post("/api/llm-configs/delete", json={"id": config_id})
                assert resp.json()["ok"] is True

                # List again — should be empty
                resp = await fastapi_client.post("/api/llm-configs/list", json={})
                assert len(resp.json()["configs"]) == 0

    async def test_llm_configs_set_default(self, fastapi_client, tmp_path) -> None:
        """Add two configs, set second as default, verify only one default."""
        with patch("app.services.llm_service.settings") as mock_settings:
            mock_settings.app_secret_key = ""
            mock_settings.app_data_dir = str(tmp_path)
            with patch("app.core.config.ensure_app_data_dir") as mock_ensure:
                mock_ensure.return_value = tmp_path
                # Add two
                await fastapi_client.post("/api/llm-configs/add", json={
                    "name": "Model A", "provider": "anthropic", "model": "a",
                    "url": "http://a", "api_key": "k",
                })
                await fastapi_client.post("/api/llm-configs/add", json={
                    "name": "Model B", "provider": "anthropic", "model": "b",
                    "url": "http://b", "api_key": "k",
                })

                # Get list to find IDs
                resp = await fastapi_client.post("/api/llm-configs/list", json={})
                configs = resp.json()["configs"]
                model_b_id = [c for c in configs if c["name"] == "Model B"][0]["id"]

                # Set Model B as default
                resp = await fastapi_client.post("/api/llm-configs/set-default", json={"id": model_b_id})
                assert resp.json()["ok"] is True

                # Verify only one default
                resp = await fastapi_client.post("/api/llm-configs/list", json={})
                defaults = [c for c in resp.json()["configs"] if c.get("is_default")]
                assert len(defaults) == 1
                assert defaults[0]["name"] == "Model B"

    async def test_llm_configs_test_connection(self, fastapi_client, tmp_path) -> None:
        """Test connection returns ok with latency."""
        with patch("app.services.llm_service.settings") as mock_settings:
            mock_settings.app_secret_key = ""
            mock_settings.app_data_dir = str(tmp_path)
            with patch("app.core.config.ensure_app_data_dir") as mock_ensure:
                mock_ensure.return_value = tmp_path
                resp_add = await fastapi_client.post("/api/llm-configs/add", json={
                    "name": "TestConn", "provider": "anthropic", "model": "t",
                    "url": "http://t", "api_key": "k",
                })
                config_id = resp_add.json()["id"]

                mock_client = AsyncMock()
                mock_client.test_connection = AsyncMock(return_value={"ok": True, "latency_ms": 100})
                with patch("app.services.llm_service.model_router") as mock_router:
                    mock_router.get_client.return_value = mock_client
                    resp = await fastapi_client.post("/api/llm-configs/test", json={"id": config_id})
                    data = resp.json()
                    assert data["ok"] is True
                    assert data["latency_ms"] == 100
