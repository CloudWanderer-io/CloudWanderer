"""Storage connector to place data in memory."""
from collections import Callable
from typing import List
import boto3
from .base_connector import BaseStorageConnector
from ..aws_urn import AwsUrn
from ..cloud_wanderer import CloudWandererResource


class MemoryStorageConnector(BaseStorageConnector):
    """Storage connector to place data in memory.

    Useful for testing.

    Example:
        >>> import cloudwanderer
        >>> cloud_wanderer = cloudwanderer.CloudWanderer(
        ...     storage_connector=cloudwanderer.storage_connectors.MemoryStorageConnector()
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
            yield memory_item_to_resource(urn, self._data[str(urn)], loader=self.read_resource)
        except KeyError:
            pass

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

    def read_all_resources_in_account(self, account_id: str) -> List['CloudWandererResource']:
        """Return all resources in account.

        Args:
            account_id (str): AWS Account ID
        """
        for urn_str, items in self._data.items():
            urn = AwsUrn.from_string(urn_str)
            if urn.account_id != account_id:
                continue
            yield memory_item_to_resource(urn, loader=self.read_resource)

    def read_resource_of_type(self, service: str, resource_type: str) -> List['CloudWandererResource']:
        """Return all resources of type.

        Args:
            service (str): Service name (e.g. ``'ec2'``)
            resource_type (str): Resource Type (e.g. ``'instance'``)
        """
        for urn_str, items in self._data.items():
            urn = AwsUrn.from_string(urn_str)
            if urn.service != service:
                continue
            if urn.resource_type != resource_type:
                continue
            yield memory_item_to_resource(urn, loader=self.read_resource)

    def read_resource_of_type_in_account(
            self, service: str, resource_type: str, account_id: str) -> List['CloudWandererResource']:
        """Return all resources of the specified type in the specified AWS account.

        Args:
            service (str): Service name, e.g. ``'ec2'``
            resource_type (str): Resource type, e.g. ``'instance'``
            account_id (str): AWS Account ID
        """
        for urn_str, items in self._data.items():
            urn = AwsUrn.from_string(urn_str)
            if urn.service != service:
                continue
            if urn.account_id != account_id:
                continue
            if urn.resource_type != resource_type:
                continue
            yield memory_item_to_resource(urn, loader=self.read_resource)

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
