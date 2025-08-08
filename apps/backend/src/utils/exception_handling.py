"""
Reusable exception handling utilities: decorator for consistent logging and HTTPException generation.
"""
from __future__ import annotations

import functools
import logging
from typing import Any, Awaitable, Callable, ParamSpec, TypeVar

from fastapi import HTTPException
from apps.backend.src.core.logging import get_request_id

P = ParamSpec("P")
R = TypeVar("R")

logger = logging.getLogger(__name__)


def handle_exceptions(
    *,
    message: str = "Operation failed",
    status_code: int = 500,
    error_code: str | None = None,
    rethrow: tuple[type[BaseException], ...] | None = None,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """
    Decorator to standardize exception logging and HTTP responses for ASYNC callables.

    - Logs the original exception with context
    - Converts unknown exceptions to HTTPException(status_code)
    - Allows specifying exceptions to rethrow untouched via `rethrow`
    - Optional `error_code` is added to the HTTPException detail payload
    """

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            try:
                return await func(*args, **kwargs)
            except Exception as e:  # noqa: BLE001 - centralizing logging
                if rethrow and isinstance(e, rethrow):
                    raise
                request_id = get_request_id()
                logger.error(
                    f"{message}: {e}",
                    exc_info=True,
                    extra={"request_id": request_id} if request_id else None,
                )
                detail: dict[str, Any] = {"detail": f"{message}: {str(e)}"}
                if request_id:
                    detail["request_id"] = request_id
                if error_code:
                    detail["code"] = error_code
                raise HTTPException(status_code=status_code, detail=detail) from e

        return wrapper

    return decorator
