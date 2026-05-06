"""HTTP error primitives for the TES API service."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


class ApiError(Exception):
    """Base exception for clean API error responses."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


class InvalidRequestError(ApiError):
    """Raised when an API request is semantically invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(400, "invalid_request", message)


class RunNotFoundError(ApiError):
    """Raised when a run identifier is not present in storage."""

    def __init__(self, run_id: str) -> None:
        super().__init__(404, "run_not_found", f"run not found: {run_id}")


class RunExecutionError(ApiError):
    """Raised when a simulation run fails during execution."""

    def __init__(self, message: str) -> None:
        super().__init__(500, "run_failed", message)


def register_error_handlers(app: FastAPI) -> None:
    """Register stable JSON error responses for API exceptions."""

    @app.exception_handler(ApiError)
    async def _handle_api_error(_request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "request validation failed",
                    "details": jsonable_encoder(exc.errors()),
                }
            },
        )
