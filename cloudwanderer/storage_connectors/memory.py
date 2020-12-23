from collections import defaultdict
from typing import List
import boto3
from .base_connector import BaseStorageConnector
from ..aws_urn import AwsUrn
from ..cloud_wanderer import CloudWandererResource


class MemoryStorageConnector(BaseStorageConnector):

    def __init__(self):
        self._data = defaultdict(dict)

    def read_resource(self, urn: AwsUrn) -> List['CloudWandererResource']:
        """Return the resource with the specified :class:`cloudwanderer.aws_urn.AwsUrn)`.

        Arguments:
            urn (cloudwanderer.aws_urn.AwsUrn): The AWS URN of the resource to return
        """
        yield from memory_item_to_resource(urn, self._data[str(urn)])

    def read_all(self):
        pass

    def read_all_resources_in_account(self):
        pass

    def read_resource_of_type(self):
        pass

    def read_resource_of_type_in_account(self):
        pass

    def write_resource(self, urn: AwsUrn, resource: boto3.resources.base.ServiceResource) -> None:
        """Write the specified resource to memory.

        Arguments:
            urn (cloudwanderer.aws_urn.AwsUrn): The URN of the resource.
            resource: The boto3 Resource object representing the resource.
        """
        self._data[str(urn)]['BaseResource'] = resource.meta.data

    def delete_resource(self):
        pass

    def delete_resource_of_type_in_account_region(self):
        pass


def memory_item_to_resource(urn: AwsUrn, items: dict) -> CloudWandererResource:
    """Convert a resource and its attributes to a CloudWandererResource."""
    attributes = [attribute for item_type, attribute in items.items() if item_type != 'BaseResource']
    base_resource = next(iter(resource for item_type, resource in items.items() if item_type == 'BaseResource'))
    yield CloudWandererResource(
        urn=urn,
        resource_data=base_resource,
        resource_attributes=attributes
    )
