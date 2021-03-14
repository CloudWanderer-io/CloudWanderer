"""Models for CloudWanderer data."""
from typing import List, NamedTuple


class GetAction(NamedTuple):
    """A get action for a specific resource_type in a specific region."""

    service_name: str
    region: str
    resource_type: str


class CleanupAction(NamedTuple):
    """A clean up action for a specific resource_type in a specific region."""

    service_name: str
    region: str
    resource_type: str


class GetAndCleanUp(NamedTuple):
    """A set of get and cleanup actions.

    The get and cleanup actions are paired together because the cleanup action must be performed after the get action
    in order to ensure that any stale resources are removed from the storage connectors.
    """

    get_actions: List[GetAction]
    cleanup_actions: List[CleanupAction]

    def __bool__(self) -> bool:
        """Return whether this GetAndCleanup set is empty."""
        return bool(self.get_actions or self.cleanup_actions)
