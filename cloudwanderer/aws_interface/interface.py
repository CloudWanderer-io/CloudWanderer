"""A standardised interface for interacting with AWS.

Provides simpler methods for :class:`~.cloud_wanderer.CloudWanderer` to call.
"""

import logging
from typing import Any, Dict, Iterator, List, Optional, Tuple

import boto3
import botocore  # type: ignore

from cloudwanderer.utils import snake_to_pascal

from ..boto3_helpers import Boto3CommonAttributesMixin
from .boto3_loaders import ServiceMappingLoader

# from ..boto3_services import Boto3Services, CloudWandererBoto3Service, MergedServiceLoader
from ..cloud_wanderer_resource import CloudWandererResource
from ..exceptions import BadRequestError, ResourceNotFoundError, UnsupportedResourceTypeError
from ..models import TemplateActionSet, GetAndCleanUp
from .models import ResourceFilter
from ..urn import URN, PartialUrn
from .session import CloudWandererBoto3Session
from boto3.resources.base import ServiceResource

logger = logging.getLogger(__name__)


class CloudWandererAWSInterface(Boto3CommonAttributesMixin):
    """Simplifies lookup of Boto3 services and resources."""

    limit_resources = None

    def __init__(
        self,
        cloudwanderer_boto3_session: CloudWandererBoto3Session,
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
        self.cloudwanderer_boto3_session = cloudwanderer_boto3_session or CloudWandererBoto3Session()

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

    def get_resource_discovery_actions(
        self, regions: List[str] = None, service_resources: List[str] = None
    ) -> List[GetAndCleanUp]:
        """ """
        services_resource_tuples = []

        discovery_regions = regions or self.cloudwanderer_boto3_session.enabled_regions

        if service_resources:
            services_resource_tuples = set(
                (service, resource_type)
                for service_resource in service_resources
                for service, resource_type in service_resource.split(":")
            )
        service_names = [service for service, _ in services_resource_tuples]
        action_sets = []
        service_names = service_names or self.cloudwanderer_boto3_session.available_services
        logger.debug("Getting actions for: %s", service_names)
        for service_name in service_names:
            resource_types = [resource_type for _, resource_type in services_resource_tuples]
            service = self.cloudwanderer_boto3_session.resource(service_name=service_name)
            action_sets.extend(
                self._get_discovery_action_templates_for_service(
                    service=service, resource_types=resource_types, discovery_regions=discovery_regions
                )
            )

        return self._inflate_action_set_regions(action_sets)

    def _inflate_action_set_regions(self, action_set_templates: List[TemplateActionSet]):
        enabled_regions = self.cloudwanderer_boto3_session.enabled_regions
        result = []
        for action_set_template in action_set_templates:
            result.append(
                action_set_template.inflate(
                    regions=enabled_regions, account_id=self.cloudwanderer_boto3_session.account_id
                )
            )

        return result

    def _get_discovery_action_templates_for_service(
        self, service: ServiceResource, resource_types: list[str], discovery_regions: List[str]
    ):
        logger.debug("Getting resource_types for %s", service.name)

        if resource_types:
            service_resource_types = list(set(resource_types) & set(service.resource_types))
        else:
            service_resource_types = service.resource_types
        action_templates = []
        for resource_type in service_resource_types:
            resource = service.resource(resource_type)
            action_templates.extend(
                self._get_discovery_action_templates_for_resource(
                    resource=resource, discovery_regions=discovery_regions
                )
            )
        return action_templates

    def _get_discovery_action_templates_for_resource(self, resource: ServiceResource, discovery_regions: List[str]):
        action_templates = []

        logger.debug("Getting actions for %s in %s", resource.resource_type, discovery_regions)

        action_templates = resource.get_discovery_action_templates(discovery_regions=["eu-west-1"])
        if not action_templates:
            return []
        logger.debug("getting actions for: %s", resource.dependent_resource_types)
        for dependent_resource_type in resource.dependent_resource_types:
            dependent_resource = resource.get_dependent_resource(dependent_resource_type)
            action_templates.extend(
                dependent_resource.get_discovery_action_templates(discovery_regions=discovery_regions)
            )

        return action_templates

    def _get_resource_filters(self, service_name: str, resource_type: str) -> Dict[str, Any]:
        if not self.resource_filters:
            return {}

        for resource_filter in self.resource_filters:
            if resource_filter.service_name == service_name and resource_filter.resource_type == resource_type:
                return resource_filter.filters
        return {}
