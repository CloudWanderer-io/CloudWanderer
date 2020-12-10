"""Module containing abstract classes for CloudWanderer storage connectors."""
from abc import ABC, abstractmethod


class BaseConnector(ABC):
    """Abstract class for specification of the CloudWanderer storage connector interface."""

    @abstractmethod
    def write_resource(self, urn, resource):
        """Persist a single resource to storage."""

    @abstractmethod
    def read_all(self):
        """Return all records from storage."""

    @abstractmethod
    def read_resource(self, urn):
        """Return a resource matching the supplied urn from storage."""

    @abstractmethod
    def read_resource_of_type(self, service, resource_type):
        """Return all resources of this type from storage."""

    @abstractmethod
    def read_all_resources_in_account(self, account_id):
        """Return all resources from this AWS account."""

    @abstractmethod
    def read_resource_of_type_in_account(self, service, resource_type, account_id):
        """Return all resources of this type from this AWS account."""
