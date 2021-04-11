"""Helpers that facilitate type hints and mypy validation."""
import functools
import weakref
from threading import RLock
from typing import Any, Callable, Optional


def memoized_method(*lru_args, **lru_kwargs) -> Callable:
    """Instance oriented wrapper of lru_cache.

    from https://stackoverflow.com/questions/33672412/python-functools-lru-cache-with-class-methods-release-object

    Arguments:
        *lru_args:
            The args that will be passed on to lru_cache
        **lru_kwargs:
            The kwargs that will be passed on to lru_cache
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapped_func(self: Any, *args, **kwargs) -> Callable:
            # We're storing the wrapped method inside the instance. If we had
            # a strong reference to self the instance would never die.
            self_weak = weakref.ref(self)

            @functools.wraps(func)
            @functools.lru_cache(*lru_args, **lru_kwargs)
            def cached_method(*args, **kwargs) -> Any:
                return func(self_weak(), *args, **kwargs)

            setattr(self, func.__name__, cached_method)
            return cached_method(*args, **kwargs)

        return wrapped_func

    return decorator


_NOT_FOUND = object()


class cached_property:
    """Instance oriented caching of a property method."""

    def __init__(self, func: Callable) -> None:
        self.func = func
        self.attrname: Optional[str] = None
        self.__doc__ = func.__doc__
        self.lock = RLock()

    def __set_name__(self, owner: Any, name: str) -> None:
        """Determine the name of the attribute we're decorating.

        Arguments:
            owner: The class the method we're decorating is a member of
            name: The name of the attribute we're decorating

        Raises:
            TypeError: When the same cached_property is being applied to two different names.
        """
        if self.attrname is None:
            self.attrname = name
        elif name != self.attrname:
            raise TypeError(
                "Cannot assign the same cached_property to two different names " f"({self.attrname!r} and {name!r})."
            )

    def __get__(self, instance: Any, owner: Any = None) -> Any:
        """Return the cached value if one exists.

        Arguments:
            instance: The object our decorated method is a member of
            owner: The class our decorated method is a member of

        Raises:
            TypeError: When cached_property is being used without calling __set_name__ first.
        """
        if instance is None:
            return self
        if self.attrname is None:
            raise TypeError("Cannot use cached_property instance without calling __set_name__ on it.")
        try:
            cache = instance.__dict__
        except AttributeError:  # not all objects have __dict__ (e.g. class defines slots)
            msg = (
                f"No '__dict__' attribute on {type(instance).__name__!r} "
                f"instance to cache {self.attrname!r} property."
            )
            raise TypeError(msg) from None
        val = cache.get(self.attrname, _NOT_FOUND)
        if val is _NOT_FOUND:
            with self.lock:
                # check if another thread filled cache while we awaited lock
                val = cache.get(self.attrname, _NOT_FOUND)
                if val is _NOT_FOUND:
                    val = self.func(instance)
                    try:
                        cache[self.attrname] = val
                    except TypeError:
                        msg = (
                            f"The '__dict__' attribute on {type(instance).__name__!r} instance "
                            f"does not support item assignment for caching {self.attrname!r} property."
                        )
                        raise TypeError(msg) from None
        return val
