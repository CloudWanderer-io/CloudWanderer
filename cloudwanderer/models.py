"""Models for CloudWanderer data."""
from .urn import URN, PartialUrn
from typing import Any, Dict, List, NamedTuple


class ActionSet(NamedTuple):
    """Define a list of partial URNs to discover and delete."""

    get_urns: List[PartialUrn]
    delete_urns: List[PartialUrn]


class TemplateActionSet(ActionSet):
    """An AWS specific set of actions.

    This differs from a regular ActionSet action insofar as it
    will probably contain actions with the region 'ALL'.
    These actions need to be unpacked into region specific actions that
    reflect the enabled regions in the AWS account in question
    before being placed into a non-cloud specific ActionSet class
    for CloudWanderer to consume.
    """

    def inflate(self, regions: List[str], account_id: str) -> ActionSet:
        new_action_set = ActionSet(get_urns=[], delete_urns=[])
        for partial_urn in self.get_urns:
            new_action_set.get_urns.extend(self._inflate_partial_urn(partial_urn, account_id, regions))

        for partial_urn in self.delete_urns:
            new_action_set.delete_urns.extend(self._inflate_partial_urn(partial_urn, account_id, regions))

        return new_action_set

    @staticmethod
    def _inflate_partial_urn(partial_urn: PartialUrn, account_id: str, regions: List[str]) -> List[PartialUrn]:
        if partial_urn.region != "ALL":
            return [partial_urn.copy(account_id=account_id)]

        inflated_partial_urns = []
        for region in regions:
            inflated_partial_urns.append(partial_urn.copy(account_id=account_id, region=region))
        return inflated_partial_urns


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


class ServiceResourceType(NamedTuple):
    """A resource type including a service that it is member of

    Attributes:
        service_name: The name of the service
        resource_type: The type of resource
    """

    service_name: str
    name: str


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
