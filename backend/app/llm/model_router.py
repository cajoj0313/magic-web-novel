"""Model selection, configuration, and routing for LLM providers."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.logger import get_logger
from app.llm import LLMError
from app.llm.anthropic_client import AnthropicClient
from app.llm.openai_client import OpenAICompatibleClient

logger = get_logger(__name__)


@dataclass(frozen=True)
class LLMConfig:
    """Immutable LLM model configuration."""

    id: str
    name: str
    provider: str  # "anthropic" or "openai"
    model: str
    api_key: str
    base_url: str = ""
    temperature: float = 0.7
    max_tokens: int = 8192
    is_default: bool = False


class LLMConfigRegistry:
    """Registry for LLM configurations with default tracking."""

    def __init__(self):
        self._configs: dict[str, LLMConfig] = {}

    def register(self, config: LLMConfig) -> None:
        """Register an LLM configuration, replacing any existing entry with the same ID."""
        if config.is_default:
            # Unset previous default
            for existing in self._configs.values():
                if existing.is_default and existing.id != config.id:
                    self._configs[existing.id] = existing.__class__(
                        id=existing.id,
                        name=existing.name,
                        provider=existing.provider,
                        model=existing.model,
                        api_key=existing.api_key,
                        base_url=existing.base_url,
                        temperature=existing.temperature,
                        max_tokens=existing.max_tokens,
                        is_default=False,
                    )
        self._configs[config.id] = config
        logger.debug("Registered LLM config: id=%s, provider=%s, model=%s", config.id, config.provider, config.model)

    def get(self, config_id: str) -> LLMConfig | None:
        """Get a configuration by ID."""
        return self._configs.get(config_id)

    def list_all(self) -> list[LLMConfig]:
        """Return all registered configurations."""
        return list(self._configs.values())

    def get_default(self) -> LLMConfig | None:
        """Return the default configuration, or None if no default is set."""
        for config in self._configs.values():
            if config.is_default:
                return config
        return None

    def remove(self, config_id: str) -> bool:
        """Remove a configuration by ID. Returns True if found and removed."""
        if config_id in self._configs:
            del self._configs[config_id]
            logger.debug("Removed LLM config: id=%s", config_id)
            return True
        return False


class ModelRouter:
    """Route chat requests to the correct LLM client based on provider."""

    def __init__(self, llm_config_service: object | None = None):
        self._llm_config_service = llm_config_service
        self._clients: dict[str, AnthropicClient | OpenAICompatibleClient] = {}

    def get_client(self, provider: str) -> AnthropicClient | OpenAICompatibleClient:
        """Get or create a client for the given provider.

        Args:
            provider: Provider name ("anthropic" or "openai").

        Raises:
            LLMError: If the provider is not recognized.
        """
        if provider in self._clients:
            return self._clients[provider]

        # Try to get config from registry first
        registry: LLMConfigRegistry | None = None
        if hasattr(self._llm_config_service, "registry"):
            registry = self._llm_config_service.registry
        config: LLMConfig | None = None
        if registry:
            config = registry.get(provider)

        if provider == "anthropic":
            if config:
                client: AnthropicClient | OpenAICompatibleClient = AnthropicClient(
                    api_key=config.api_key,
                    model=config.model,
                    base_url=config.base_url if config.base_url else None,
                )
            else:
                client = AnthropicClient(api_key="")
        elif provider == "openai":
            if config:
                client = OpenAICompatibleClient(
                    api_key=config.api_key,
                    model=config.model,
                    base_url=config.base_url or "",
                )
            else:
                client = OpenAICompatibleClient(api_key="", model="", base_url="")
        else:
            raise LLMError(
                message=f"Unknown LLM provider: {provider!r}. Supported: 'anthropic', 'openai'.",
                provider=provider,
            )

        self._clients[provider] = client
        logger.info("Created LLM client for provider: %s", provider)
        return client

    async def chat(
        self,
        provider: str,
        model: str,
        messages: list[dict],
        system: str | None = None,
        **kwargs,
    ) -> dict:
        """Route a chat request to the correct provider client.

        Args:
            provider: Provider name ("anthropic" or "openai").
            model: Model identifier to use.
            messages: List of message dicts with 'role' and 'content'.
            system: Optional system prompt.
            **kwargs: Additional provider-specific arguments (e.g., temperature, max_tokens, thinking_budget).

        Returns:
            Normalized response dict with 'content', 'model', and 'usage' keys.
        """
        client = self.get_client(provider)

        if isinstance(client, AnthropicClient):
            return await client.chat(
                messages=messages,
                system=system,
                model=model,
                **kwargs,
            )
        elif isinstance(client, OpenAICompatibleClient):
            return await client.chat(
                messages=messages,
                **kwargs,
            )
        else:
            raise LLMError(
                message=f"No handler for provider: {provider!r}",
                provider=provider,
            )
