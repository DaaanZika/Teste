"""Domain exceptions and the FastAPI handlers that turn them into safe JSON.

No unhandled exception should ever reach the client as a stack trace. Every
domain error carries a stable `error` code and a human-readable `message`
in Portuguese, matching the shape mandated for V1:

    {
        "success": false,
        "error": "DOCUMENT_PROCESSING_FAILED",
        "message": "Não foi possível processar o documento.",
        "requires_human_review": true
    }
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("app")


class AppError(Exception):
    """Base class for all domain-level errors.

    Subclasses set a stable machine-readable `error_code`, an HTTP
    `status_code`, a Portuguese `message`, and whether the situation
    requires a human to review the record.
    """

    error_code: str = "APPLICATION_ERROR"
    status_code: int = status.HTTP_400_BAD_REQUEST
    requires_human_review: bool = False

    def __init__(self, message: str, *, error_code: str | None = None, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        if error_code:
            self.error_code = error_code
        if status_code:
            self.status_code = status_code


class NotFoundError(AppError):
    error_code = "NOT_FOUND"
    status_code = status.HTTP_404_NOT_FOUND


class ValidationFailedError(AppError):
    error_code = "VALIDATION_FAILED"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY


class UnsupportedFileTypeError(AppError):
    error_code = "UNSUPPORTED_FILE_TYPE"
    status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE


class FileTooLargeError(AppError):
    error_code = "FILE_TOO_LARGE"
    status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE


class DuplicateDocumentError(AppError):
    error_code = "POSSIBLE_DUPLICATE"
    status_code = status.HTTP_409_CONFLICT
    requires_human_review = True


class DocumentProcessingError(AppError):
    error_code = "DOCUMENT_PROCESSING_FAILED"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    requires_human_review = True


def _error_response(*, error: str, message: str, status_code: int, requires_human_review: bool = False) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": error,
            "message": message,
            "requires_human_review": requires_human_review,
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        logger.warning("AppError %s: %s", exc.error_code, exc.message)
        return _error_response(
            error=exc.error_code,
            message=exc.message,
            status_code=exc.status_code,
            requires_human_review=exc.requires_human_review,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return _error_response(
            error="INVALID_REQUEST",
            message="Os dados enviados são inválidos.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _error_response(
            error="HTTP_ERROR",
            message=str(exc.detail) if isinstance(exc.detail, str) else "Erro ao processar a requisição.",
            status_code=exc.status_code,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error while processing %s %s", request.method, request.url)
        return _error_response(
            error="INTERNAL_ERROR",
            message="Ocorreu um erro inesperado. Nossa equipe foi notificada.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
