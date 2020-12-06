from abc import ABC, abstractmethod


class BaseConnector(ABC):

    @abstractmethod
    def write(self, urn, resource):
        """Persist a single resource to the backend."""

    @abstractmethod
    def dump(self):
        """Return all records from the backend."""
