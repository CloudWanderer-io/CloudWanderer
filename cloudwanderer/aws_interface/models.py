from typing import NamedTuple, Dict, Any


class ResourceFilter(NamedTuple):
    """A definition for filtering a resource."""

    service_name: str
    resource_type: str
    filters: Dict[str, Any]
