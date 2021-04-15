"""Models for CloudWanderer data."""
from typing import Any, Dict, List, NamedTuple


class GetAction(NamedTuple):
    """A get action for a specific resource_type in a specific region.

    Attributes:
        service_name: The name of the service to get
        resource_type: The type of resource to get
        region: The region to get it in
    """

    service_name: str
    region: str
    resource_type: str


class CleanupAction(NamedTuple):
    """A storage connector clean up action for a specific resource_type in a specific region.

    Attributes:
        service_name: The name of the service to cleanup
        resource_type: The type of resource to cleanup
        region: The region to cleanup from storage
    """

    service_name: str
    region: str
    resource_type: str


class GetAndCleanUp(NamedTuple):
    """A set of get and cleanup actions.

    The get and cleanup actions are paired together because the cleanup action must be performed after the get action
    in order to ensure that any stale resources are removed from the storage connectors.

    It's possible for there to be far more cleanup actions than get actions if a single region API
    discovers resources in multiple regions.

    Attributes:
        get_actions: The list of get actions
        cleanup_actions: The list of cleanup actions
    """

    get_actions: List[GetAction]
    cleanup_actions: List[CleanupAction]

    def __bool__(self) -> bool:
        """Return whether this GetAndCleanup set is empty."""
        return bool(self.get_actions or self.cleanup_actions)


class ResourceFilter(NamedTuple):
    """A definition for filtering a resource."""

    service_name: str
    resource_type: str
    filters: Dict[str, Any]
