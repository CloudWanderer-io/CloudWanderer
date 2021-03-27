"""Helpers that facilitate type hints and mypy validation."""
import functools
from typing import Callable, TypeVar

T = TypeVar("T")


def lru_cache_property(func: Callable[..., T]) -> T:
    """Wrap lru_cache to facilitate type hinting.

    Arguments:
        func: The function to be wrapped.
    """
    return functools.lru_cache()(func)  # type: ignore
