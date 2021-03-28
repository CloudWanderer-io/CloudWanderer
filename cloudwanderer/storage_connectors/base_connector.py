"""Module containing abstract classes for CloudWanderer storage connectors."""
from abc import ABC, abstractmethod
from typing import Iterator, List, Optional

from ..cloud_wanderer_resource import CloudWandererResource
from ..urn import URN


class BaseStorageConnector(ABC):
    """Abstract class for specification of the CloudWanderer storage connector interface."""

    @abstractmethod
    def init(self) -> None:
        """Initialise the storage backend whatever it is."""

    @abstractmethod
    def write_resource(self, resource: CloudWandererResource) -> None:
        """Persist a single resource to storage.

        Arguments:
            resource (CloudWandererResource): The CloudWandererResource to write.
        """

    @abstractmethod
    def read_all(self) -> Iterator[dict]:
        """Return all records from storage."""

    @abstractmethod
    def read_resource(self, urn: URN) -> Optional[CloudWandererResource]:
        """Return a resource matching the supplied urn from storage.

        Arguments:
            urn (URN): The AWS URN of the resource to return
        """

    @abstractmethod
    def read_resources(
        self,
        account_id: str = None,
        region: str = None,
        service: str = None,
        resource_type: str = None,
        urn: URN = None,
    ) -> Iterator["CloudWandererResource"]:
        """Yield a resource matching the supplied urn from storage.

        All arguments are optional.

        Arguments:
            urn: The AWS URN of the resource to return
            account_id: AWS Account ID
            region: AWS region (e.g. ``'eu-west-2'``)
            service: Service name (e.g. ``'ec2'``)
            resource_type: Resource Type (e.g. ``'instance'``)
        """

    @abstractmethod
    def delete_resource(self, urn: URN) -> None:
        """Delete this resource and all its resource attributes.

        Arguments:
            urn (URN): The URN of the resource to delete
        """

    @abstractmethod
    def delete_resource_of_type_in_account_region(
        self, service: str, resource_type: str, account_id: str, region: str, urns_to_keep: List[URN] = None
    ) -> None:
        """Delete resources of type in account and region unless in list of URNs.

        This is used primarily to clean up old resources.

        Arguments:
            account_id (str): AWS Account ID
            region (str): AWS region (e.g. ``'eu-west-2'``)
            service (str): Service name (e.g. ``'ec2'``)
            resource_type (str): Resource Type (e.g. ``'instance'``)
            urns_to_keep (List[cloudwanderer.urn.URN]): A list of resources not to delete
        """
