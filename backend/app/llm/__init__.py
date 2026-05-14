"""LLM client package."""

from __future__ import annotations


class LLMError(Exception):
    """Custom exception for LLM provider errors."""

    def __init__(
        self,
        message: str,
        provider: str = "unknown",
        status_code: int | None = None,
    ):
        self.provider = provider
        self.status_code = status_code
        super().__init__(message)
