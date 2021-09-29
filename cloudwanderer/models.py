"""Models for CloudWanderer data."""
from .urn import URN, PartialUrn
from typing import Any, Dict, List, NamedTuple


class ActionSet(NamedTuple):
    """Define a list of partial URNs to discover and delete."""

    get_urns: List[PartialUrn]
    delete_urns: List[PartialUrn]


# TODO: Delete this class
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


# TODO: Delete this class
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


# TODO: Delete this class
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

    def __add__(self, other: Any) -> "GetAndCleanUp":
        """Combine the actions of two objects.

        Arguments:
            other: the other GetAndCleanUp objects whose actions we will add to this one.

        Raises:
            TypeError: If anything other than a GetAndCleanUp action is added.
        """
        if not isinstance(other, self.__class__):
            raise TypeError(
                f"unsupported operand type(s) for +: {self.__class__.__name__} and {other.__class__.__name__}"
            )
        self.get_actions.extend(other.get_actions)
        self.cleanup_actions.extend(other.cleanup_actions)
        return self
