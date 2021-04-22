from typing import Any, Dict
from unittest.mock import MagicMock


def named_mock(name: str, **kwargs: Dict[str, Any]) -> MagicMock:
    mock = MagicMock(**kwargs)
    mock.name = name
    return mock
