"""Domain exceptions mapped to clean HTTP responses (no stack traces leak)."""
from __future__ import annotations


class SanthraError(Exception):
    status_code = 400
    error_code = "bad_request"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvalidImageError(SanthraError):
    status_code = 422
    error_code = "invalid_image"


class UnsupportedFormatError(SanthraError):
    status_code = 415
    error_code = "unsupported_format"


class FileTooLargeError(SanthraError):
    status_code = 413
    error_code = "file_too_large"


class NotFoundError(SanthraError):
    status_code = 404
    error_code = "not_found"


class AnalysisError(SanthraError):
    status_code = 500
    error_code = "analysis_failed"
