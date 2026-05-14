"""Unit tests for model router — LLMConfigRegistry and ModelRouter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.llm import LLMError
from app.llm.model_router import LLMConfig, LLMConfigRegistry, ModelRouter


class TestLLMConfigRegistry:
    def test_register_and_get(self) -> None:
        """Register a config and retrieve it by ID."""
        registry = LLMConfigRegistry()
        config = LLMConfig(
            id="cfg-1",
            name="Claude Test",
            provider="anthropic",
            model="claude-sonnet-4-6",
            api_key="sk-test",
        )
        registry.register(config)
        assert registry.get("cfg-1") is config

    def test_list_all(self) -> None:
        """list_all returns all registered configs."""
        registry = LLMConfigRegistry()
        registry.register(LLMConfig(id="a", name="A", provider="anthropic", model="m", api_key="k"))
        registry.register(LLMConfig(id="b", name="B", provider="openai", model="m2", api_key="k2"))
        assert len(registry.list_all()) == 2

    def test_get_default_none(self) -> None:
        """get_default returns None when no default is set."""
        registry = LLMConfigRegistry()
        assert registry.get_default() is None

    def test_get_default(self) -> None:
        """get_default returns the config marked as default."""
        registry = LLMConfigRegistry()
        c1 = LLMConfig(id="a", name="A", provider="anthropic", model="m", api_key="k")
        c2 = LLMConfig(id="b", name="B", provider="anthropic", model="m2", api_key="k2", is_default=True)
        registry.register(c1)
        registry.register(c2)
        default = registry.get_default()
        assert default is not None
        assert default.id == "b"

    def test_registering_default_unsets_previous(self) -> None:
        """Registering a new default unsets the old one."""
        registry = LLMConfigRegistry()
        registry.register(LLMConfig(id="a", name="A", provider="anthropic", model="m", api_key="k", is_default=True))
        registry.register(LLMConfig(id="b", name="B", provider="openai", model="m2", api_key="k2", is_default=True))
        defaults = [c for c in registry.list_all() if c.is_default]
        assert len(defaults) == 1
        assert defaults[0].id == "b"

    def test_remove(self) -> None:
        """remove deletes a config and returns True."""
        registry = LLMConfigRegistry()
        registry.register(LLMConfig(id="a", name="A", provider="anthropic", model="m", api_key="k"))
        assert registry.remove("a") is True
        assert registry.get("a") is None
        assert registry.remove("nonexistent") is False

    def test_register_replaces_existing(self) -> None:
        """Registering with the same ID replaces the previous config."""
        registry = LLMConfigRegistry()
        registry.register(LLMConfig(id="a", name="Old", provider="anthropic", model="m1", api_key="k"))
        registry.register(LLMConfig(id="a", name="New", provider="openai", model="m2", api_key="k2"))
        config = registry.get("a")
        assert config is not None
        assert config.name == "New"
        assert config.provider == "openai"


class TestModelRouter:
    def test_get_client_anthropic(self) -> None:
        """get_client returns AnthropicClient for 'anthropic' provider."""
        from app.llm.anthropic_client import AnthropicClient
        router = ModelRouter()
        client = router.get_client("anthropic")
        assert isinstance(client, AnthropicClient)

    def test_get_client_openai(self) -> None:
        """get_client returns OpenAICompatibleClient for 'openai' provider."""
        from app.llm.openai_client import OpenAICompatibleClient
        with patch("app.llm.openai_client.AsyncOpenAI"):
            router = ModelRouter()
            client = router.get_client("openai")
            assert isinstance(client, OpenAICompatibleClient)

    def test_get_client_unknown_raises(self) -> None:
        """get_client raises LLMError for unknown provider."""
        router = ModelRouter()
        with pytest.raises(LLMError) as exc_info:
            router.get_client("gemini")
        assert "Unknown LLM provider" in str(exc_info.value)

    def test_get_client_caches_per_provider(self) -> None:
        """Same provider returns the same client instance."""
        router = ModelRouter()
        c1 = router.get_client("anthropic")
        c2 = router.get_client("anthropic")
        assert c1 is c2

    def test_get_client_with_registry_config(self) -> None:
        """get_client uses registry config to construct clients with proper params."""
        from app.llm.anthropic_client import AnthropicClient
        from app.llm.openai_client import OpenAICompatibleClient
        with patch("app.llm.openai_client.AsyncOpenAI"):
            registry = LLMConfigRegistry()
            registry.register(LLMConfig(
                id="cfg1", name="My Claude", provider="anthropic",
                model="claude-sonnet-4-6", api_key="sk-registry-key",
                base_url="https://proxy.example.com",
            ))
            registry.register(LLMConfig(
                id="cfg2", name="My OpenAI", provider="openai",
                model="gpt-4", api_key="sk-openai-key",
                base_url="https://openai.example.com",
            ))
            service = MagicMock()
            service.registry = registry
            router = ModelRouter(llm_config_service=service)
            assert isinstance(router.get_client("anthropic"), AnthropicClient)
            assert isinstance(router.get_client("openai"), OpenAICompatibleClient)

    async def test_chat_anthropic_routes_correctly(self) -> None:
        """chat routes to AnthropicClient.chat for anthropic provider."""
        from app.llm.anthropic_client import AnthropicClient

        # Create a real client but override its chat method
        real_client = AnthropicClient(api_key="sk-fake")
        real_client.chat = AsyncMock(return_value={"content": "hello", "model": "claude", "usage": {}})
        router = ModelRouter()
        router._clients["anthropic"] = real_client

        result = await router.chat("anthropic", "claude-sonnet", [{"role": "user", "content": "hi"}])
        assert result["content"] == "hello"
        call_kwargs = real_client.chat.call_args[1]
        assert call_kwargs["model"] == "claude-sonnet"

    async def test_chat_openai_routes_correctly(self) -> None:
        """chat routes to OpenAICompatibleClient.chat for openai provider."""
        from app.llm.openai_client import OpenAICompatibleClient

        with patch("app.llm.openai_client.AsyncOpenAI"):
            real_client = OpenAICompatibleClient(api_key="sk-fake", model="gpt-4", base_url="")
        real_client.chat = AsyncMock(return_value={"content": "hi", "model": "gpt", "usage": {}})
        router = ModelRouter()
        router._clients["openai"] = real_client

        result = await router.chat("openai", "gpt-4o", [{"role": "user", "content": "hi"}])
        assert result["content"] == "hi"
        real_client.chat.assert_called_once()

    async def test_chat_passes_kwargs(self) -> None:
        """chat passes extra kwargs to the client."""
        from app.llm.anthropic_client import AnthropicClient

        real_client = AnthropicClient(api_key="sk-fake")
        real_client.chat = AsyncMock(return_value={"content": "ok", "model": "m", "usage": {}})
        router = ModelRouter()
        router._clients["anthropic"] = real_client

        await router.chat(
            "anthropic",
            "claude",
            [{"role": "user", "content": "hi"}],
            system="You are helpful",
            temperature=0.5,
        )
        call_kwargs = real_client.chat.call_args[1]
        assert call_kwargs["temperature"] == 0.5

    async def test_chat_unknown_provider_raises(self) -> None:
        """chat raises LLMError when get_client returns unknown type."""
        router = ModelRouter()
        # Inject a fake client that is neither Anthropic nor OpenAI
        router._clients["unknown"] = object()  # type: ignore[arg-type]

        with pytest.raises(LLMError) as exc_info:
            await router.chat("unknown", "model", [])
        assert "No handler" in str(exc_info.value)
