"""Global error codes and unified error response model."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel


class ErrorCode(str, Enum):
    """All error codes used across the API."""

    # Project errors
    PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"
    PROJECT_ROOT_INVALID = "PROJECT_ROOT_INVALID"
    CONTRACT_MISSING = "CONTRACT_MISSING"

    # Task errors
    TASK_NOT_FOUND = "TASK_NOT_FOUND"
    TASK_ALREADY_EXISTS = "TASK_ALREADY_EXISTS"
    TASK_CANCEL_FAILED = "TASK_CANCEL_FAILED"
    TASK_CONFLICT = "TASK_CONFLICT"

    # LLM errors
    LLM_CONFIG_NOT_FOUND = "LLM_CONFIG_NOT_FOUND"
    LLM_CONNECTION_FAILED = "LLM_CONNECTION_FAILED"
    LLM_CALL_FAILED = "LLM_CALL_FAILED"
    LLM_RESPONSE_INVALID = "LLM_RESPONSE_INVALID"

    # Chapter errors
    CHAPTER_NOT_FOUND = "CHAPTER_NOT_FOUND"
    CHAPTER_SAVE_FAILED = "CHAPTER_SAVE_FAILED"

    # File / data errors
    FILE_READ_ERROR = "FILE_READ_ERROR"
    FILE_WRITE_ERROR = "FILE_WRITE_ERROR"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    FILE_CORRUPTED = "FILE_CORRUPTED"
    SQLITE_ERROR = "SQLITE_ERROR"

    # Validation
    INVALID_REQUEST = "INVALID_REQUEST"
    VALIDATION_ERROR = "VALIDATION_ERROR"

    # Internal
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ErrorDetail(BaseModel):
    """Structured error detail inside an ErrorResponse."""

    code: ErrorCode
    message: str
    details: dict[str, Any] = {}


class ErrorResponse(BaseModel):
    """Standard error envelope returned on every API failure.

    Matches the spec format:
      { "success": false, "error_code": "...", "message": "...", "detail": {...} }
    """

    success: bool = False
    error_code: str
    message: str
    detail: dict[str, Any] | None = None

    @property
    def ok(self) -> bool:
        """Alias for success (for test compatibility)."""
        return self.success

    @property
    def error(self) -> ErrorDetail:
        """Return an ErrorDetail view of this response."""
        return ErrorDetail(
            code=ErrorCode(self.error_code) if self.error_code in ErrorCode.__members__ else ErrorCode.INTERNAL_ERROR,
            message=self.message,
            details=self.detail or {},
        )


def error_response(
    code: ErrorCode,
    message: str,
    detail: dict[str, Any] | None = None,
    details: dict[str, Any] | None = None,
) -> ErrorResponse:
    """Helper to construct an ErrorResponse."""
    return ErrorResponse(
        success=False,
        error_code=code.value if isinstance(code, ErrorCode) else code,
        message=message,
        detail=detail or details,
    )
