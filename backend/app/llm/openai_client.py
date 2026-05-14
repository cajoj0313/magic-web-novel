"""OpenAI-compatible API client wrapper."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from openai import AsyncOpenAI
from openai import APIStatusError, APIConnectionError, APITimeoutError

from app.core.logger import get_logger
from app.llm import LLMError

logger: logging.Logger = get_logger(__name__)


class OpenAICompatibleClient:
    """Async wrapper for any OpenAI-compatible API with retry logic."""

    _MAX_RETRIES = 3
    _BASE_DELAY = 1.0  # seconds

    def __init__(self, api_key: str, model: str, base_url: str):
        self._api_key = api_key
        self._model = model
        self._base_url = base_url
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 8192,
        model: str | None = None,
        **kwargs,
    ) -> dict:
        """Send a chat request to the OpenAI-compatible endpoint.

        Args:
            messages: List of dicts with 'role' and 'content' keys.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.

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
                    temperature=temperature,
                    max_tokens=max_tokens,
                    model=model,
                    **kwargs,
                )
            except LLMError:
                raise
            except (APIStatusError, APIConnectionError, APITimeoutError) as exc:
                # Auth errors will never succeed on retry
                if isinstance(exc, APIStatusError) and exc.status_code in (401, 403):
                    logger.error("OpenAI auth error (non-retryable): %s", exc)
                    last_exception = exc
                    break
                last_exception = exc
                if attempt < self._MAX_RETRIES:
                    delay = self._BASE_DELAY * (2 ** attempt)
                    logger.warning(
                        "OpenAI API error (attempt %d/%d): %s — retrying in %.1fs",
                        attempt + 1,
                        self._MAX_RETRIES,
                        exc,
                        delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error("OpenAI API exhausted retries: %s", exc)
            except Exception as exc:
                last_exception = exc
                if attempt < self._MAX_RETRIES:
                    delay = self._BASE_DELAY * (2 ** attempt)
                    logger.warning(
                        "Unexpected error calling OpenAI (attempt %d/%d): %s — retrying in %.1fs",
                        attempt + 1,
                        self._MAX_RETRIES,
                        exc,
                        delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error("OpenAI call exhausted retries with unexpected error: %s", exc)

        raise LLMError(
            message=f"OpenAI-compatible API call failed after {self._MAX_RETRIES + 1} attempts: {last_exception}",
            provider="openai",
            status_code=last_exception.status_code if isinstance(last_exception, APIStatusError) else None,
        )

    async def _do_chat(
        self,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
        model: str | None,
        **kwargs,
    ) -> dict:
        """Core chat call without retry logic."""
        effective_model = model or self._model

        # OpenAI SDK doesn't accept a `system` kwarg — system prompt must be
        # in the messages list.  Extract it if present and prepend.
        system = kwargs.pop("system", None)
        if system:
            messages = [{"role": "system", "content": system}, *messages]

        kwargs.setdefault("messages", messages)
        kwargs.setdefault("max_tokens", max_tokens)
        kwargs.setdefault("temperature", temperature)
        kwargs["model"] = effective_model

        logger.debug(
            "OpenAI chat request: model=%s, base_url=%s, messages=%d, temperature=%.1f, max_tokens=%d",
            effective_model,
            self._base_url,
            len(messages),
            temperature,
            max_tokens,
        )

        response = await self._client.chat.completions.create(**kwargs)

        choice = response.choices[0]
        content = choice.message.content or ""

        usage = {
            "input_tokens": response.usage.prompt_tokens if response.usage else 0,
            "output_tokens": response.usage.completion_tokens if response.usage else 0,
        }

        model_used = response.model or self._model

        logger.debug(
            "OpenAI chat response: model=%s, input_tokens=%d, output_tokens=%d",
            model_used,
            usage["input_tokens"],
            usage["output_tokens"],
        )

        return {
            "content": content,
            "model": model_used,
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
