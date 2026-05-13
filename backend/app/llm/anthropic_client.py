"""Anthropic Claude API client wrapper."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import anthropic

from app.core.logger import get_logger
from app.llm import LLMError

logger: logging.Logger = get_logger(__name__)


class AnthropicClient:
    """Async wrapper around the Anthropic SDK with retry logic."""

    _MAX_RETRIES = 3
    _BASE_DELAY = 1.0  # seconds

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
        base_url: str | None = None,
    ):
        self._api_key = api_key
        self._model = model
        client_kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        self._client = anthropic.AsyncAnthropic(**client_kwargs)

    async def chat(
        self,
        messages: list[dict],
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 8192,
        model: str | None = None,
        thinking_budget: int | None = None,
    ) -> dict:
        """Send a chat request to the Anthropic API.

        Args:
            messages: List of dicts with 'role' and 'content' keys.
            system: Optional system prompt.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.
            thinking_budget: Budget for extended thinking (optional).

        Returns:
            Dict with 'content', 'model', and 'usage' keys.

        Raises:
            LLMError: On API errors after retries are exhausted.
        """
        last_exception: Exception | None = None

        for attempt in range(self._MAX_RETRIES + 1):
            try:
                return await self._do_chat(
                    messages=messages,
                    system=system,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    model=model,
                    thinking_budget=thinking_budget,
                )
            except LLMError:
                raise
            except (anthropic.APIStatusError, anthropic.APIConnectionError, anthropic.APITimeoutError) as exc:
                # Auth errors (401/403) should not be retried
                status = getattr(exc, "status_code", None)
                if status in (401, 403):
                    raise LLMError(
                        message=f"Anthropic API auth error: {exc}",
                        provider="anthropic",
                        status_code=status,
                    )
                last_exception = exc
                if attempt < self._MAX_RETRIES:
                    delay = self._BASE_DELAY * (2 ** attempt)
                    logger.warning(
                        "Anthropic API error (attempt %d/%d): %s — retrying in %.1fs",
                        attempt + 1,
                        self._MAX_RETRIES,
                        exc,
                        delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error("Anthropic API exhausted retries: %s", exc)
            except Exception as exc:
                last_exception = exc
                if attempt < self._MAX_RETRIES:
                    delay = self._BASE_DELAY * (2 ** attempt)
                    logger.warning(
                        "Unexpected error calling Anthropic (attempt %d/%d): %s — retrying in %.1fs",
                        attempt + 1,
                        self._MAX_RETRIES,
                        exc,
                        delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error("Anthropic call exhausted retries with unexpected error: %s", exc)

        raise LLMError(
            message=f"Anthropic API call failed after {self._MAX_RETRIES + 1} attempts: {last_exception}",
            provider="anthropic",
            status_code=last_exception.status_code if isinstance(last_exception, anthropic.APIStatusError) else None,
        )

    async def _do_chat(
        self,
        messages: list[dict],
        system: str | None,
        temperature: float,
        max_tokens: int,
        model: str | None,
        thinking_budget: int | None,
    ) -> dict:
        """Core chat call without retry logic."""
        effective_model = model or self._model
        kwargs: dict[str, Any] = {
            "model": effective_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system is not None:
            kwargs["system"] = system
        if thinking_budget is not None:
            kwargs["thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}

        logger.debug(
            "Anthropic chat request: model=%s, messages=%d, temperature=%.1f, max_tokens=%d",
            self._model,
            len(messages),
            temperature,
            max_tokens,
        )

        response = await self._client.messages.create(**kwargs)

        # Extract text content from response blocks
        text_parts: list[str] = []
        for block in response.content:
            if hasattr(block, "text"):
                text_parts.append(block.text)
            elif hasattr(block, "thinking"):
                # Skip thinking blocks in the returned content
                pass

        content = "".join(text_parts)

        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }

        logger.debug(
            "Anthropic chat response: model=%s, input_tokens=%d, output_tokens=%d",
            response.model,
            usage["input_tokens"],
            usage["output_tokens"],
        )

        return {
            "content": content,
            "model": response.model,
            "usage": usage,
        }

    async def test_connection(self) -> dict:
        """Test connectivity with a minimal request."""
        result = await self.chat(
            messages=[{"role": "user", "content": "Reply with 'OK' only."}],
            max_tokens=10,
            temperature=0,
        )
        return {"model": result["model"]}
