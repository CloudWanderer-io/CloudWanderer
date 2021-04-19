"""A standardised interface for interacting with AWS.

Provides simpler methods for :class:`~.cloud_wanderer.CloudWanderer` to call.
"""

import logging
from typing import Any, Dict, Iterator, List, Optional

import boto3
import botocore  # type: ignore

from cloudwanderer.utils import snake_to_pascal

from .boto3_helpers import Boto3CommonAttributesMixin
from .boto3_loaders import ServiceMappingLoader
from .boto3_services import Boto3Services, CloudWandererBoto3Service, MergedServiceLoader
from .cloud_wanderer_resource import CloudWandererResource
from .exceptions import BadRequestError, ResourceNotFoundError, UnsupportedResourceTypeError
from .models import GetAndCleanUp, ResourceFilter
from .urn import URN

logger = logging.getLogger(__name__)


class CloudWandererAWSInterface(Boto3CommonAttributesMixin):
    """Simplifies lookup of Boto3 services and resources."""

    limit_resources = None

    def __init__(
        self,
        boto3_session: boto3.session.Session = None,
        service_loader: MergedServiceLoader = None,
        service_mapping_loader: ServiceMappingLoader = None,
        resource_filters: List[ResourceFilter] = None,
    ) -> None:
        """Simplifies lookup of Boto3 services and resources.

        Arguments:
            boto3_session (boto3.session.Session):
                A Boto3 session, if not provided the default will be used.
            service_loader:
                An optional loader to allow the injection of additional custom services
            service_mapping_loader:
                An optional loader to allow the injection of additional custom service mappings
            resource_filters:
                An optional list of resource filters to apply when getting those resources.
        """
        self.boto3_session = boto3_session or boto3.session.Session()
        self.boto3_services = Boto3Services(
            boto3_session=boto3_session, service_loader=service_loader, service_mapping_loader=service_mapping_loader
        )
        self.resource_filters = resource_filters or []

    def get_resource(self, urn: URN, include_subresources: bool = True) -> Iterator[CloudWandererResource]:
        """Yield the resource picked out by this URN and optionally its subresources.

        Arguments:
            urn (URN): The urn of the resource to get.
            include_subresources: Whether or not to additionally yield the subresources of the resource.
        """
        try:
            resource = self.boto3_services.get_resource_from_urn(urn=urn)
        except ResourceNotFoundError:
            return None
        except BadRequestError:
            logger.debug(
                f"Got BadRequestError while getting {urn}, as AWS services commonly return 4xx errors other than 404 "
                "for resource non-existence we are interpreting this as the resource does not exist."
            )
            return None
        subresource_urns = []
        if include_subresources:
            for subresource in resource.get_subresources():
                subresource_urns.append(subresource.urn)
                yield CloudWandererResource(
                    urn=subresource.urn,
                    resource_data=subresource.normalised_raw_data,
                    secondary_attributes=list(subresource.get_secondary_attributes()),
                )
        yield CloudWandererResource(
            urn=urn,
            subresource_urns=subresource_urns,
            resource_data=resource.normalised_raw_data,
            secondary_attributes=list(resource.get_secondary_attributes()),
        )

    def get_resources(
        self,
        service_name: str,
        resource_type: str,
        region: str = None,
        **kwargs,
    ) -> Iterator[CloudWandererResource]:
        """Return all resources of resource_type from Boto3.

        Arguments:
            service_name (str): The name of the service to get resource for (e.g. ``'ec2'``)
            resource_type (str): The type of resource to get resources of (e.g. ``'instance'``)
            region (str): The region to get resources of (e.g. ``'eu-west-1'``)
            **kwargs: Additional keyword arguments will be passed down to the Boto3 client.

        Raises:
            botocore.exceptions.ClientError: Occurs if the Boto3 Client Errors.
        """
        logger.info("Getting %s %s resources from %s", service_name, resource_type, region)
        service = self.boto3_services.get_service(service_name=service_name, region_name=region)
        resource_filters = self._get_resource_filters(service_name, resource_type)
        try:
            for resource in service.get_resources(resource_type=resource_type, resource_filters=resource_filters):
                logger.debug("Found %s", resource.urn)
                subresource_urns = []
                for subresource in resource.get_subresources():
                    logger.debug("Found subresource %s", subresource.urn)
                    subresource_urns.append(subresource.urn)
                    yield CloudWandererResource(
                        urn=subresource.urn,
                        resource_data=subresource.normalised_raw_data,
                        secondary_attributes=list(subresource.get_secondary_attributes()),
                    )
                yield CloudWandererResource(
                    urn=resource.urn,
                    subresource_urns=subresource_urns,
                    resource_data=resource.normalised_raw_data,
                    secondary_attributes=list(resource.get_secondary_attributes()),
                )
        except botocore.exceptions.EndpointConnectionError:
            logger.info("%s %s not supported in %s", service_name, resource_type, region)
            return
        except botocore.exceptions.ClientError as ex:
            if ex.response["Error"]["Code"] == "InvalidAction":
                logger.info("%s %s not supported in %s", service_name, resource_type, region)
                return
            raise

    def get_actions(
        self,
        regions: List[str] = None,
        service_names: List[str] = None,
        resource_types: List[str] = None,
        exclude_resources: List[str] = None,
    ) -> List[GetAndCleanUp]:
        """Return the query and cleanup actions to be performed based on the parameters provided.

        All arguments are optional.

        Arguments:
            regions(list):
                The name of the region to get resources from (defaults to session default if not specified)
            service_names (str):
                The names of the services to write resources for (e.g. ``['ec2']``)
            resource_types (list):
                A list of resource types to include (e.g. ``['instance']``)
            exclude_resources (list):
                A list of service:resources to exclude (e.g. ``['ec2:instance']``)

        Raises:
            UnsupportedResourceTypeError: When a resource type is requested that does not exist.
        """
        get_and_cleanup_actions = []
        regions = regions or self.boto3_services.enabled_regions
        exclude_resources = exclude_resources or []
        regions = regions or self.enabled_regions
        service_names = service_names or self.boto3_services.available_services

        for region_name in regions:
            for service_name in service_names:
                service = self.boto3_services.get_empty_service(service_name=service_name, region_name=region_name)
                service_resource_types = self._get_resource_types_for_service(service, resource_types)
                for resource_type in service_resource_types:
                    service_resource = f"{service_name}:{resource_type}"
                    logger.debug("Getting actions for %s %s in %s", service_resource, resource_type, region_name)
                    if service_resource in exclude_resources:
                        logger.debug("Skipping %s as per exclude_resources", service_resource)
                        continue
                    if self.limit_resources and service_resource not in self.limit_resources:
                        logger.debug("Skipping %s as it does not exist in limit_resources", service_resource)
                        continue
                    resource_map = service.service_map.get_resource_map(snake_to_pascal(resource_type))
                    if not resource_map:
                        raise UnsupportedResourceTypeError("No %s resource type found", service_resource)
                        continue
                    actions = resource_map.get_and_cleanup_actions(region_name)
                    if not actions:
                        continue
                    resource_actions = actions.inflate_actions(service.enabled_regions)
                    for subresource_type in resource_map.subresource_types:
                        subresource_map = service.service_map.get_resource_map(snake_to_pascal(subresource_type))
                        actions = subresource_map.get_and_cleanup_actions(region_name)
                        resource_actions += actions.inflate_actions(service.enabled_regions)
                    get_and_cleanup_actions.append(resource_actions)
        return get_and_cleanup_actions

    def _get_resource_types_for_service(
        self, service: CloudWandererBoto3Service, resource_types: Optional[List[str]]
    ) -> List[str]:
        if resource_types:
            logger.debug("Validating if %s are %s resource types", resource_types, service.name)
            return list(set(resource_types) & set(service.resource_types))

        return service.resource_types

    def _get_resource_filters(self, service_name: str, resource_type: str) -> Dict[str, Any]:
        if not self.resource_filters:
            return {}

        for resource_filter in self.resource_filters:
            if resource_filter.service_name == service_name and resource_filter.resource_type == resource_type:
                return resource_filter.filters
        return {}
