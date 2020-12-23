"""Collection of loose utility functions."""
import logging
from typing import Callable


def exception_logging_wrapper(method: Callable, **kwargs) -> None:
    """Logs exceptions raised by method_name.

    Increases visibility of multi-threaded exceptions.
    """
    try:
        method(**kwargs)
    except Exception as ex:
        logging.error(ex)
