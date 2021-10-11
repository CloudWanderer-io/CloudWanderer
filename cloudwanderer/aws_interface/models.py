"""Models specific to the CloudWanderer aws interface."""
from typing import Any, Dict, NamedTuple


class ResourceFilter(NamedTuple):
    """A definition for filtering a resource."""

    service_name: str
    resource_type: str
    filters: Dict[str, Any]
