"""Storage connector to place data in memory."""
import logging
from typing import Callable
from typing import List
import boto3
from .base_connector import BaseStorageConnector
from ..aws_urn import AwsUrn
from ..cloud_wanderer import CloudWandererResource

logger = logging.getLogger(__name__)


class MemoryStorageConnector(BaseStorageConnector):
    """Storage connector to place data in memory.

    Useful for testing.

    Example:
        >>> import cloudwanderer
        >>> cloud_wanderer = cloudwanderer.CloudWanderer(
        ...     storage_connectors=[cloudwanderer.storage_connectors.MemoryStorageConnector()]
        ... )

    """

    def __init__(self, *args, **kwargs) -> None:
        """Initialise MemoryStorageConnector."""
        self._data = {}

    def init(self) -> None:
        """Dummy method to fulfil interface requirements."""

    def read_resource(self, urn: AwsUrn) -> List['CloudWandererResource']:
        """Return the resource with the specified :class:`cloudwanderer.aws_urn.AwsUrn)`.

        Arguments:
            urn (cloudwanderer.aws_urn.AwsUrn): The AWS URN of the resource to return
        """
        try:
            return memory_item_to_resource(urn, self._data[str(urn)], loader=self.read_resource)
        except KeyError:
            return None

    def read_resources(self, **kwargs) -> List['CloudWandererResource']:
        """Return the resources matching the arguments.

        All arguments are optional

        Arguments:
            urn (cloudwanderer.aws_urn.AwsUrn): The AWS URN of the resource to return
            account_id (str): AWS Account ID
            region (str): AWS region (e.g. ``eu-west-2``)
            service (str): Service name (e.g. ``'ec2'``)
            resource_type (str): Resource Type (e.g. ``'instance'``)
        """
        for urn_str, items in self._data.items():
            urn = AwsUrn.from_string(urn_str)
            if kwargs.get('urn') is not None:
                if urn == kwargs['urn']:
                    yield memory_item_to_resource(urn, loader=self.read_resource)
                continue
            if self._urn_matches_kwargs(urn, **kwargs):
                yield memory_item_to_resource(urn, loader=self.read_resource)

    def _urn_matches_kwargs(self, urn: AwsUrn, **kwargs) -> bool:
        filter_items = ('account_id', 'region', 'service', 'resource_type')
        for item in filter_items:
            if kwargs.get(item) is not None and getattr(urn, item) != kwargs[item]:
                return False
        return True

    def read_all(self) -> dict:
        """Return the raw dictionaries stored in memory."""
        for urn_str, items in self._data.items():
            for item_type, item in items.items():
                yield {
                    **{
                        'urn': urn_str,
                        'attr': item_type,
                    },
                    **item
                }

    def write_resource(self, urn: AwsUrn, resource: boto3.resources.base.ServiceResource) -> None:
        """Write the specified resource to memory.

        Arguments:
            urn (cloudwanderer.aws_urn.AwsUrn): The URN of the resource.
            resource: The boto3 Resource object representing the resource.
        """
        self._data[str(urn)] = self._data.get(str(urn), {})
        self._data[str(urn)]['BaseResource'] = resource.meta.data

    def delete_resource(self, urn: AwsUrn) -> None:
        """Delete the resource and all its resource attributes from memory."""
        try:
            del self._data[str(urn)]
        except KeyError:
            pass

    def delete_resource_of_type_in_account_region(
            self, service: str, resource_type: str, account_id: str, region: str, urns_to_keep: AwsUrn = None) -> None:
        """Delete resources of type in account id unless in list of URNs."""
        urns_to_delete = []
        for urn_str, items in self._data.items():
            urn = AwsUrn.from_string(urn_str)
            if urn.service != service:
                continue
            if urn.account_id != account_id:
                continue
            if urn.resource_type != resource_type:
                continue
            if urn.region != region:
                continue
            if urn in urns_to_keep:
                continue
            urns_to_delete.append(urn)
        for urn in urns_to_delete:
            del self._data[str(urn)]


def memory_item_to_resource(urn: AwsUrn, items: dict = None, loader: Callable = None) -> CloudWandererResource:
    """Convert a resource and its attributes to a CloudWandererResource."""
    items = items or {}
    attributes = [attribute for item_type, attribute in items.items() if item_type != 'BaseResource']
    base_resource = next(iter(resource for item_type, resource in items.items() if item_type == 'BaseResource'), {})
    return CloudWandererResource(
        urn=urn,
        resource_data=base_resource,
        resource_attributes=attributes,
        loader=loader
    )
