"""Module containing abstract classes for CloudWanderer storage connectors."""
from abc import ABC, abstractmethod
from typing import List, Iterator
from ..aws_urn import AwsUrn
from ..cloud_wanderer_resource import CloudWandererResource


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
    def read_resource(self, urn: AwsUrn) -> 'CloudWandererResource':
        """Return a resource matching the supplied urn from storage.

        Arguments:
            urn (AwsUrn): The AWS URN of the resource to return
        """

    @abstractmethod
    def read_resources(self, **kwargs) -> Iterator['CloudWandererResource']:
        """Yield a resource matching the supplied urn from storage.

        All arguments are optional.

        Arguments:
            kwargs: Optional arguments narrowing the scope of the resources returned.

        Keyword Arguments:
            urn (~cloudwanderer.aws_urn.AwsUrn): The AWS URN of the resource to return
            account_id (:class:`str`): AWS Account ID
            region (:class:`str`): AWS region (e.g. ``'eu-west-2'``)
            service (:class:`str`): Service name (e.g. ``'ec2'``)
            resource_type (:class:`str`): Resource Type (e.g. ``'instance'``)
        """

    @abstractmethod
    def delete_resource(self, urn: AwsUrn) -> None:
        """Delete this resource and all its resource attributes.

        Arguments:
            urn (AwsUrn): The URN of the resource to delete
        """

    @abstractmethod
    def delete_resource_of_type_in_account_region(
            self, service: str, resource_type: str, account_id: str,
            region: str, urns_to_keep: List[AwsUrn] = None) -> None:
        """Delete resources of type in account and region unless in list of URNs.

        This is used primarily to clean up old resources.

        Arguments:
            account_id (str): AWS Account ID
            region (str): AWS region (e.g. ``'eu-west-2'``)
            service (str): Service name (e.g. ``'ec2'``)
            resource_type (str): Resource Type (e.g. ``'instance'``)
            urns_to_keep (List[cloudwanderer.aws_urn.AwsUrn]): A list of resources not to delete
        """
