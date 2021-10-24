"""Models for CloudWanderer data."""
from enum import Enum, auto, unique
from typing import List, NamedTuple

from .urn import PartialUrn


class ActionSet(NamedTuple):
    """Define a list of partial URNs to discover and delete."""

    get_urns: List[PartialUrn]
    delete_urns: List[PartialUrn]


class TemplateActionSet(ActionSet):
    """An set of actions which have not yet had all their placeholders inflated.

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


class ServiceResourceType(NamedTuple):
    """A resource type including a service that it is member of.

    Attributes:
        service_name: The name of the service
        resource_type: The type of resource
    """

    service_name: str
    name: str


class Relationship(NamedTuple):
    """Specifying the relationship between two resources."""

    partial_urn: PartialUrn
    direction: "RelationshipDirection"


@unique
class RelationshipAccountIdSource(Enum):
    """Enum specifying the source of a relationship's Account ID."""

    UNKNOWN = auto()
    SAME_AS_RESOURCE = auto()


@unique
class RelationshipRegionSource(Enum):
    """Enum specifying the source of a relationship's Region."""

    UNKNOWN = auto()
    SAME_AS_RESOURCE = auto()


@unique
class RelationshipDirection(Enum):
    """Enum specifying the direction of a relationship."""

    OUTBOUND = auto()
    INBOUND = auto()
