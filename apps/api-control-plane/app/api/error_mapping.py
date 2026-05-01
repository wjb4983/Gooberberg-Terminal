from collections.abc import Callable
from typing import TypeVar

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

T = TypeVar("T")


def map_model_config_domain_error(*, route_context: str, model_family: str, error: Exception) -> HTTPException:
    if isinstance(error, KeyError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{route_context}: unknown model_family='{model_family}'",
        )
    if isinstance(error, (ValidationError, ValueError, TypeError)):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{route_context}: invalid config payload for model_family='{model_family}'",
        )
    if isinstance(error, SQLAlchemyError):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{route_context}: model config could not be persisted for model_family='{model_family}'",
        )
    raise error


def execute_model_config_service_call(*, route_context: str, model_family: str, operation: Callable[[], T]) -> T:
    try:
        return operation()
    except Exception as error:  # noqa: BLE001 - intentionally translate domain failures to HTTP errors
        raise map_model_config_domain_error(route_context=route_context, model_family=model_family, error=error) from error
