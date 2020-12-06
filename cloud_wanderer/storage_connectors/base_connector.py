from abc import ABC, abstractmethod


class BaseConnector(ABC):

    @abstractmethod
    def write(self, urn, resource):
        """Persist a single resource to storage."""

    @abstractmethod
    def dump(self):
        """Return all records from storage."""

    @abstractmethod
    def read_resource(self, urn):
        """Return a resource matching the supplied urn from storage."""

    @abstractmethod
    def read_resource_of_type(self, service, resource_type):
        """Return all resources of this type from storage."""

    @abstractmethod
    def read_resource_from_account(self, account_id):
        """Return all resources from this AWS account."""

    @abstractmethod
    def read_resource_of_type_from_account(self, service, resource_type, account_id):
        """Return all resources of this type from this AWS account."""
