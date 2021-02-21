"""Collection of loose utility functions."""
import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Callable

logger = logging.getLogger(__name__)


def exception_logging_wrapper(method: Callable, return_value: object = None, **kwargs) -> None:
    """Log exceptions raised by method_name.

    Increases visibility of multi-threaded exceptions.

    Arguments:
        method (Callable): A method to wrap, for which will we handle and log any exceptions.
        return_value (object): A value to return instead of the method's result.
        **kwargs: Arguments to pass to the method
    """
    try:
        result = method(**kwargs)
    except Exception as ex:
        logger.exception(ex)
        return return_value
    if return_value is None:
        return result
    return return_value


def json_object_hook(dct: dict) -> dict:
    """Clean out empty strings to avoid DynamoDB ValidationExceptions.

    Arguments:
        dct (dict): The dictionary to clean.
    """
    for key, value in dct.items():
        if value == "":
            dct[key] = None
    return dct


def json_default(item: object) -> object:
    """JSON object type converter that handles datetime objects.

    Arguments:
        item: The object JSON is trying to serialise.
    """
    if isinstance(item, datetime):
        return item.isoformat()


def standardise_data_types(resource: dict) -> dict:
    """Return a dictionary normalised to datatypes acceptable for DynamoDB.

    Arguments:
        resource (dict): The dictionary we're normalising to DynamoDB acceptable data types.
    """
    result = json.loads(json.dumps(resource, default=json_default), object_hook=json_object_hook, parse_float=Decimal)
    return result
