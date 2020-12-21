"""Module containing abstract classes for CloudWanderer storage connectors."""
from abc import ABC, abstractmethod
from typing import List
from ..aws_urn import AwsUrn
from ..cloud_wanderer import CloudWandererResource


class BaseStorageConnector(ABC):
    """Abstract class for specification of the CloudWanderer storage connector interface."""

    @abstractmethod
    def write_resource(self, urn: AwsUrn, resource: str) -> None:
        """Persist a single resource to storage."""

    @abstractmethod
    def read_all(self) -> List[dict]:
        """Return all records from storage."""

    @abstractmethod
    def read_resource(self, urn: AwsUrn) -> List['CloudWandererResource']:
        """Return a resource matching the supplied urn from storage."""

    @abstractmethod
    def read_resource_of_type(self, service: str, resource_type: str) -> List['CloudWandererResource']:
        """Return all resources of this type from storage."""

    @abstractmethod
    def read_all_resources_in_account(self, account_id: str) -> List['CloudWandererResource']:
        """Return all resources from this AWS account."""

    @abstractmethod
    def read_resource_of_type_in_account(
            self, service: str, resource_type: str, account_id: str) -> List['CloudWandererResource']:
        """Return all resources of this type from this AWS account."""

    @abstractmethod
    def delete_resource(self, urn: AwsUrn) -> None:
        """Delete this resource and all its resource attributes."""

    @abstractmethod
    def delete_resource_of_type_in_account_region(
            self, service: str, resource_type: str, account_id: str, region: str, urns_to_keep: AwsUrn = None) -> None:
        """Delete resources of type in account and region unless in list of URNs.

        This is used primarily to clean up old resources.
        """
