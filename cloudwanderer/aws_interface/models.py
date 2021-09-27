from ..urn import URN, PartialUrn
from typing import List, NamedTuple, Dict, Any
from ..models import ActionSet, GetAndCleanUp, GetAction, CleanupAction


class TemplateActionSet(ActionSet):
    """An AWS specific set of actions.

    This differs from a regular ActionSet action insofar as it
    will probably contain actions with the region 'ALL_REGIONS'.
    These actions need to be unpacked into region specific actions that
    reflect the enabled regions in the AWS account in question
    before being placed into a non-cloud specific ActionSet class
    for CloudWanderer to consume.
    """


# TODO: delete this class
class AWSGetAndCleanUp(GetAndCleanUp):
    """An AWS specific set of GetAndCleanUp actions.

    This differs from a regular GetAndCleanUp action insofar as it
    will probably contain actions with the region 'ALL_REGIONS'.
    These actions need to be unpacked into region specific actions that
    reflect the enabled regions in the AWS account in question
    before being placed into a non-cloud specific GetAndCleanUp class
    for CloudWanderer to consume.
    """

    def inflate_actions(self, account_id: str, enabled_regions: List[str]) -> GetAndCleanUp:
        """Inflate the get and cleanup actions that are ALL_REGIONS.

        Arguments:
            regions: The list of enabled regions with which to inflate actions specified as ALL_REGIONS.
        """
        return ActionSet(
            get_urns=self._inflated_get_urns(enabled_regions), delete_urns=self._inflated_delete_urns(enabled_regions)
        )

    def _inflated_get_urns(self, account_id: str, enabled_regions: List[str]) -> List[PartialUrn]:
        get_actions = []
        for get_action in self.get_actions:
            if get_action.region != "ALL_REGIONS":
                get_actions.append(get_action)
                continue
            get_actions.extend(
                [
                    PartialUrn(
                        service_name=get_action.service_name, resource_type=get_action.resource_type, region=region
                    )
                    for region in enabled_regions
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
