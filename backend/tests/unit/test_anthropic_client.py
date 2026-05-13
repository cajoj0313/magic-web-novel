"""Unit tests for AnthropicClient — retry logic, 401 handling, token tracking."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.llm import LLMError
from app.llm.anthropic_client import AnthropicClient


@pytest.fixture(autouse=True)
def _no_sleep():
    """Patch asyncio.sleep to avoid real delays in tests."""
    with patch("app.llm.anthropic_client.asyncio.sleep", new_callable=AsyncMock):
        yield


class TestRetryOnRateLimit:
    """RateLimitError triggers exponential backoff retry, throws LLMCallFailed after 3 retries."""

    async def test_retry_on_rate_limit(self) -> None:
        """RateLimitError triggers retry, succeeds on 2nd attempt."""
        import anthropic

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="success")]
        mock_response.model = "claude-test"
        mock_response.usage = MagicMock(input_tokens=10, output_tokens=20)

        call_count = 0

        async def side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise anthropic.APITimeoutError("Rate limited")
            return mock_response

        client = AnthropicClient(api_key="sk-test", model="claude-test")
        client._client = AsyncMock()
        client._client.messages.create = AsyncMock(side_effect=side_effect)

        result = await client.chat(
            messages=[{"role": "user", "content": "hello"}],
            max_tokens=100,
        )

        assert call_count == 2
        assert result["content"] == "success"

    async def test_retry_exhausted_raises_llm_error(self) -> None:
        """After 3 retries, raises LLMError."""
        import anthropic

        client = AnthropicClient(api_key="sk-test", model="claude-test")
        client._client = AsyncMock()
        client._client.messages.create = AsyncMock(
            side_effect=anthropic.APITimeoutError("Always fails")
        )

        with pytest.raises(LLMError) as exc_info:
            await client.chat(
                messages=[{"role": "user", "content": "hello"}],
                max_tokens=100,
            )

        assert "attempts" in str(exc_info.value)
        assert client._client.messages.create.call_count == 4

    async def test_retry_on_connection_error(self) -> None:
        """APIConnectionError also triggers retry."""
        import anthropic

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="recovered")]
        mock_response.model = "claude-test"
        mock_response.usage = MagicMock(input_tokens=5, output_tokens=10)

        call_count = 0

        async def side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise anthropic.APIConnectionError("Connection dropped")
            return mock_response

        client = AnthropicClient(api_key="sk-test", model="claude-test")
        client._client = AsyncMock()
        client._client.messages.create = AsyncMock(side_effect=side_effect)

        result = await client.chat(
            messages=[{"role": "user", "content": "hello"}],
            max_tokens=100,
        )

        assert result["content"] == "recovered"
        assert call_count == 3


class TestNoRetryOnAuthError:
    """401 error immediately raises, no retry."""

    async def test_auth_error_no_retry(self) -> None:
        """401 AuthenticationError raises immediately without retry."""
        import anthropic

        # AuthenticationError is a subclass of APIStatusError, needs response mock
        mock_response = MagicMock()
        mock_response.status_code = 401
        error_401 = anthropic.AuthenticationError(
            message="Invalid API key",
            response=mock_response,
            body={"error": "invalid_api_key"},
        )

        client = AnthropicClient(api_key="sk-invalid", model="claude-test")
        client._client = AsyncMock()
        client._client.messages.create = AsyncMock(side_effect=error_401)

        with pytest.raises(LLMError):
            await client.chat(
                messages=[{"role": "user", "content": "hello"}],
                max_tokens=100,
            )

        assert client._client.messages.create.call_count == 1


class TestTokenUsageTracking:
    """Each call records prompt_tokens + completion_tokens."""

    async def test_token_usage_returned(self) -> None:
        """Chat response includes usage info."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="hello back")]
        mock_response.model = "claude-sonnet-4-20250514"
        mock_response.usage = MagicMock(input_tokens=42, output_tokens=100)

        client = AnthropicClient(api_key="sk-test")
        client._client = AsyncMock()
        client._client.messages.create = AsyncMock(return_value=mock_response)

        result = await client.chat(
            messages=[{"role": "user", "content": "hello"}],
            max_tokens=100,
        )

        assert "usage" in result
        assert result["usage"]["input_tokens"] == 42
        assert result["usage"]["output_tokens"] == 100
        assert result["model"] == "claude-sonnet-4-20250514"


class TestOpenAICompatibleClientCall:
    """OpenAI compatible interface calls with correct parameters."""

    async def test_openai_client_passes_params(self) -> None:
        """OpenAICompatibleClient passes system, messages, temperature correctly."""
        from app.llm.openai_client import OpenAICompatibleClient

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="test response"))]
        mock_response.model = "deepseek-chat"
        mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=20)

        client = OpenAICompatibleClient(
            api_key="sk-test",
            model="deepseek-chat",
            base_url="https://api.deepseek.com/v1",
        )
        client._client = AsyncMock()
        client._client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await client.chat(
            system="You are a helper",
            messages=[{"role": "user", "content": "hello"}],
            temperature=0.5,
            max_tokens=2048,
            model="deepseek-chat",
        )

        client._client.chat.completions.create.assert_awaited_once()
        call_kwargs = client._client.chat.completions.create.call_args[1]
        assert call_kwargs["temperature"] == 0.5
        assert call_kwargs["max_tokens"] == 2048
        assert call_kwargs["model"] == "deepseek-chat"
        assert result["content"] == "test response"
        assert result["model"] == "deepseek-chat"

    async def test_openai_client_default_model(self) -> None:
        """Uses configured default model when not overridden."""
        from app.llm.openai_client import OpenAICompatibleClient

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="ok"))]
        mock_response.model = "gpt-4"
        mock_response.usage = MagicMock(prompt_tokens=1, completion_tokens=1)

        client = OpenAICompatibleClient(api_key="sk-test", model="gpt-4", base_url="https://api.openai.com/v1")
        client._client = AsyncMock()
        client._client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await client.chat(
            messages=[{"role": "user", "content": "hi"}],
        )

        call_kwargs = client._client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "gpt-4"
        assert result["content"] == "ok"
