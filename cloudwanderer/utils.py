"""Collection of loose utility functions."""
import json
import logging
import os
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


def exception_logging_wrapper(method: Callable, return_value: object = None, **kwargs) -> Optional[Any]:
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


def json_default(item: object) -> Optional[object]:
    """JSON object type converter that handles datetime objects.

    Arguments:
        item: The object JSON is trying to serialise.
    """
    if isinstance(item, datetime):
        return item.isoformat()
    return None


def standardise_data_types(resource: dict) -> Dict[str, Any]:
    """Return a dictionary normalised to datatypes acceptable for DynamoDB.

    Arguments:
        resource (dict): The dictionary we're normalising to DynamoDB acceptable data types.
    """
    result = json.loads(json.dumps(resource, default=json_default), object_hook=json_object_hook, parse_float=Decimal)
    return result


def load_json_definitions(path: str) -> Dict[str, Any]:
    """Return the parsed contents of all JSON files in a given path.

    Arguments:
        path: The path to load JSON files from.
    """
    definition_files = [
        (os.path.abspath(os.path.join(path, file_name)), Path(file_name).stem)
        for file_name in os.listdir(path)
        if os.path.isfile(os.path.join(path, file_name))
    ]
    definitions = {}
    for file_path, service_name in definition_files:
        with open(file_path) as definition_path:
            definitions[service_name] = json.load(definition_path)
    return definitions


def snake_to_pascal(snake_case: str) -> str:
    """Return a PascalCase version of a snake_case name.

    Arguments:
        snake_case: the string to turn into PascalCase.
    """
    snake_case = snake_case.lower()
    return snake_case.replace("_", " ").title().replace(" ", "")
