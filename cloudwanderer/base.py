"""Base classes for subclassing."""
import abc
from typing import Any, Dict, Iterator, List, Optional

from .cloud_wanderer_resource import CloudWandererResource
from .models import ActionSet, ServiceResourceType
from .urn import URN


class ServiceResourceTypeFilter(abc.ABC):
    """Abstract Base Class for CloudInterfaces to subclass for resource filtering."""

    service_name: str
    resource_type: str


class CloudInterface(abc.ABC):
    """Base class for Cloud Interface classes."""

    @abc.abstractmethod
    def get_resource(
        self,
        urn: URN,
        service_resource_type_filters: Optional[List[ServiceResourceTypeFilter]] = None,
        include_dependent_resources: bool = True,
        client_args: Optional[Dict[str, Any]] = None,
    ) -> Iterator[CloudWandererResource]:
        """Yield the resource picked out by this URN and optionally its subresources.

        Arguments:
            urn (URN): The urn of the resource to get.
            service_resource_type_filters: A :class:`AWSResourceTypeFilter` list to filter resources.
            include_dependent_resources: Whether or not to additionally yield the dependent_resources of the resource.
            client_args: Additional keyword arguments will be passed down to the Boto3 client.
        """

    @abc.abstractmethod
    def get_resources(
        self,
        service_name: str,
        resource_type: str,
        region: str,
        service_resource_type_filters: Optional[List[ServiceResourceTypeFilter]] = None,
        client_args: Optional[Dict[str, Any]] = None,
    ) -> Iterator[CloudWandererResource]:
        """Return all resources of resource_type from Boto3.

        Arguments:
            service_name (str): The name of the service to get resource for (e.g. ``'ec2'``)
            resource_type (str): The type of resource to get resources of (e.g. ``'instance'``)
            region (str): The region to get resources of (e.g. ``'eu-west-1'``)
            service_resource_type_filters: A :class:`ServiceResourceTypeFilter` list to filter resources.
            client_args: Additional keyword arguments will be passed down to the Boto3 client.
        """

    @abc.abstractmethod
    def get_resource_discovery_actions(
        self, regions: List[str] = None, service_resource_types: List[ServiceResourceType] = None
    ) -> List[ActionSet]:
        """Return the ActionSets required to discover resources according to the params.

        Arguments:
            regions: List of regions to discover resources in
            service_resource_types: List of service resource types to discover

        """

    def get_enabled_regions(self) -> List[str]:
        """Return the list of regions enabled.

        Fulfils the interface requirements for :class:`cloudwanderer.cloud_wanderer.CloudWanderer` to call.
        """
