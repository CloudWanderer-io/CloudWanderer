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


class AWSGetAndCleanUp(GetAndCleanUp):
    """An AWS specific set of GetAndCleanUp actions.

    This differs from a regular GetAndCleanUp action insofar as it
    will probably contain actions with the region 'ALL_REGIONS'.
    These actions need to be unpacked into region specific actions that
    reflect the enabled regions in the AWS account in question
    before being placed into a non-cloud specific GetAndCleanUp class
    for CloudWanderer to consume.
    """

    def inflate_actions(self, regions: List[str]) -> GetAndCleanUp:
        """Inflate the get and cleanup actions that are ALL_REGIONS.

        Arguments:
            regions: The list of enabled regions with which to inflate actions specified as ALL_REGIONS.
        """
        return GetAndCleanUp(
            get_actions=self._inflated_get_actions(regions), cleanup_actions=self._inflated_cleanup_actions(regions)
        )

    def _inflated_get_actions(self, regions: List[str]) -> List[GetAction]:
        get_actions = []
        for get_action in self.get_actions:
            if get_action.region != "ALL_REGIONS":
                get_actions.append(get_action)
                continue
            get_actions.extend(
                [
                    GetAction(
                        service_name=get_action.service_name, resource_type=get_action.resource_type, region=region
                    )
                    for region in regions
                ]
            )
        return get_actions

    def _inflated_cleanup_actions(self, regions: List[str]) -> List[CleanupAction]:
        cleanup_actions: List[CleanupAction] = []
        for cleanup_action in self.cleanup_actions:
            if cleanup_action.region != "ALL_REGIONS":
                cleanup_actions.append(cleanup_action)
                continue
            cleanup_actions.extend(
                [
                    CleanupAction(
                        service_name=cleanup_action.service_name,
                        resource_type=cleanup_action.resource_type,
                        region=region,
                    )
                    for region in regions
                ]
            )
        return cleanup_actions

    def __bool__(self) -> bool:
        """Return whether this GetAndCleanUp set is empty."""
        return bool(self.get_actions or self.cleanup_actions)


class ResourceFilter(NamedTuple):
    """A definition for filtering a resource."""

    service_name: str
    resource_type: str
    filters: Dict[str, Any]
