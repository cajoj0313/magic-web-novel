"""Unit tests for error codes and error response helper."""

from __future__ import annotations

import pytest

from app.core.error_codes import ErrorCode, ErrorResponse, error_response


class TestErrorResponseFormat:
    def test_error_response_format(self) -> None:
        """error_response returns the correct ErrorResponse structure."""
        resp = error_response(ErrorCode.PROJECT_NOT_FOUND, "项目不存在")
        assert isinstance(resp, ErrorResponse)
        assert resp.ok is False
        assert resp.error.code == ErrorCode.PROJECT_NOT_FOUND
        assert resp.error.message == "项目不存在"
        assert resp.error.details == {}

    def test_error_response_with_details(self) -> None:
        """error_response supports optional details dict."""
        resp = error_response(
            ErrorCode.VALIDATION_ERROR,
            "字段验证失败",
            details={"field": "title", "reason": "too short"},
        )
        assert resp.error.details["field"] == "title"


class TestAllErrorCodesExist:
    def test_all_error_codes_exist(self) -> None:
        """Enum contains all spec-defined error codes."""
        expected_codes = {
            "PROJECT_NOT_FOUND",
            "PROJECT_ROOT_INVALID",
            "CONTRACT_MISSING",
            "TASK_NOT_FOUND",
            "TASK_CONFLICT",
            "CHAPTER_NOT_FOUND",
            "CHAPTER_SAVE_FAILED",
            "LLM_CALL_FAILED",
            "LLM_RESPONSE_INVALID",
            "LLM_CONFIG_NOT_FOUND",
            "FILE_NOT_FOUND",
            "FILE_CORRUPTED",
            "VALIDATION_ERROR",
            "INTERNAL_ERROR",
        }
        actual_codes = {e.name for e in ErrorCode}
        for code in expected_codes:
            assert code in actual_codes, f"Missing error code: {code}"
