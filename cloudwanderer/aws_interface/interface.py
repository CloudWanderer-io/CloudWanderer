"""A standardised interface for interacting with AWS.

Provides simpler methods for :class:`~.cloud_wanderer.CloudWanderer` to call.
"""

import logging
from typing import TYPE_CHECKING, Iterator, List, Optional, cast

import botocore
from botocore.exceptions import ClientError
from ..cloud_wanderer_resource import CloudWandererResource

from ..exceptions import BadRequestError, ResourceNotFoundError, UnsupportedResourceTypeError
from ..models import ActionSet, ServiceResourceType, TemplateActionSet

from ..urn import URN
from .aws_services import AWS_SERVICES
from .session import CloudWandererBoto3Session

if TYPE_CHECKING:

    from .stubs.resource import CloudWandererServiceResource

from .boto3_loaders import ResourceMap

logger = logging.getLogger(__name__)


class CloudWandererAWSInterface:
    """Simplifies lookup of Boto3 services and resources."""

    limit_resources = None

    def __init__(
        self,
        cloudwanderer_boto3_session: Optional[CloudWandererBoto3Session] = None,
    ) -> None:
        """Simplifies lookup of Boto3 services and resources.

        Arguments:
            cloudwanderer_boto3_session:
                A CloudWandererBoto3Session session, if not provided the default will be used.
        """
        self.cloudwanderer_boto3_session = cloudwanderer_boto3_session or CloudWandererBoto3Session()

    def get_resource(self, urn: URN, include_dependent_resources: bool = True) -> Iterator[CloudWandererResource]:
        """Yield the resource picked out by this URN and optionally its subresources.

        #     Arguments:
        #         urn (URN): The urn of the resource to get.
        #         include_dependent_resources: Whether or not to additionally yield the dependent_resources of the resource.
        """

        try:

            service = self.cloudwanderer_boto3_session.resource(service_name=urn.service, region_name=urn.region)
            resource = service.resource(resource_type=urn.resource_type, identifiers=urn.resource_id_parts)
            if not hasattr(resource, 'load' ):
                raise UnsupportedResourceTypeError(f"Resource type {urn.resource_type} doesn't support get_resource()")

            resource.load()
            
        except ClientError as ex:
            error_code = ex.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if error_code == 404:
                return None
            if error_code >= 400 and error_code < 500:
                return None
            raise ex
        if not resource.meta.data:
            return None
            
        dependent_resource_urns = []
        if include_dependent_resources:
            for dependent_resource_type in resource.dependent_resource_types:
                for dependent_resource in resource.collection(resource_type=dependent_resource_type):
                    dependent_resource.load()
                    urn = dependent_resource.get_urn()
                    dependent_resource_urns.append(urn)
                    yield CloudWandererResource(
                        urn=urn,
                        resource_data=dependent_resource.normalized_raw_data,
                        parent_urn=resource.get_urn(),
                        relationships=dependent_resource.relationships,
                        secondary_attributes=list(dependent_resource.get_secondary_attributes()),
                    )
        yield CloudWandererResource(
            urn=resource.get_urn(),
            resource_data=resource.normalized_raw_data,
            dependent_resource_urns=dependent_resource_urns,
            relationships=resource.relationships,
            secondary_attributes=list(resource.get_secondary_attributes()),
        )

    def get_resources(
        self,
        service_name: str,
        resource_type: str,
        region: str,
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
        service_name = cast(AWS_SERVICES, service_name)
        logger.info("Getting %s %s resources from %s", service_name, resource_type, region)
        service = self.cloudwanderer_boto3_session.resource(service_name=service_name, region_name=region)
        resource_map: ResourceMap = service.service_map.get_resource_map(resource_type)

        try:
            for resource in service.collection(resource_type=resource_type, filters=resource_map.default_filters):
                dependent_resource_urns = []
                for dependent_resource_type in resource.dependent_resource_types:
                    for dependent_resource in resource.collection(resource_type=dependent_resource_type):
                        urn = dependent_resource.get_urn()
                        dependent_resource_urns.append(urn)
                        yield CloudWandererResource(
                            urn=urn,
                            resource_data=dependent_resource.normalized_raw_data,
                            parent_urn=resource.get_urn(),
                            relationships=dependent_resource.relationships,
                            secondary_attributes=list(dependent_resource.get_secondary_attributes()),
                        )
                yield CloudWandererResource(
                    urn=resource.get_urn(),
                    resource_data=resource.normalized_raw_data,
                    dependent_resource_urns=dependent_resource_urns,
                    relationships=resource.relationships,
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
        self, regions: List[str] = None, service_resource_types: List[ServiceResourceType] = None
    ) -> List[ActionSet]:
        service_resource_types = service_resource_types or []
        discovery_regions = regions or self.cloudwanderer_boto3_session.get_enabled_regions()

        service_names = [resource_type.service_name for resource_type in service_resource_types]
        action_sets = []
        service_names = service_names or self.cloudwanderer_boto3_session.get_available_resources()
        logger.debug("Getting actions for: %s", service_names)
        for service_name in service_names:
            service_specific_resource_types = [
                resource_type.name
                for resource_type in service_resource_types
                if resource_type.service_name == service_name
            ]
            service = self.cloudwanderer_boto3_session.resource(service_name=cast(AWS_SERVICES, service_name))
            action_sets.extend(
                self._get_discovery_action_templates_for_service(
                    service=service, resource_types=service_specific_resource_types, discovery_regions=discovery_regions
                )
            )

        return self._inflate_action_set_regions(action_sets)

    def _inflate_action_set_regions(self, action_set_templates: List[TemplateActionSet]) -> List[ActionSet]:
        enabled_regions = self.cloudwanderer_boto3_session.get_enabled_regions()
        result = []
        for action_set_template in action_set_templates:
            result.append(
                action_set_template.inflate(
                    regions=enabled_regions, account_id=self.cloudwanderer_boto3_session.get_account_id()
                )
            )

        return result

    def _get_discovery_action_templates_for_service(
        self, service: "CloudWandererServiceResource", resource_types: List[str], discovery_regions: List[str]
    ) -> List[TemplateActionSet]:
        logger.debug("Getting resource_types for %s", service.service_name)

        if resource_types:
            service_resource_types = list(set(resource_types) & set(service.resource_types))
        else:
            service_resource_types = service.resource_types
        action_templates = []
        for resource_type in service_resource_types:
            resource = service.resource(resource_type, empty_resource=True)
            action_templates.extend(
                self._get_discovery_action_templates_for_resource(
                    resource=resource, discovery_regions=discovery_regions
                )
            )
        return action_templates

    def _get_discovery_action_templates_for_resource(
        self, resource: "CloudWandererServiceResource", discovery_regions: List[str]
    ) -> List[TemplateActionSet]:
        action_templates = []

        logger.debug("Getting actions for %s in %s", resource.resource_type, discovery_regions)

        action_templates = resource.get_discovery_action_templates(discovery_regions=discovery_regions)
        if not action_templates:
            return []
        logger.debug("getting actions for: %s", resource.dependent_resource_types)
        for dependent_resource_type in resource.dependent_resource_types:
            dependent_resource = resource.get_dependent_resource(dependent_resource_type, empty_resource=True)
            action_templates.extend(
                dependent_resource.get_discovery_action_templates(discovery_regions=discovery_regions)
            )

        return action_templates

    @property
    def enabled_regions(self) -> List[str]:
        return self.cloudwanderer_boto3_session.get_enabled_regions()