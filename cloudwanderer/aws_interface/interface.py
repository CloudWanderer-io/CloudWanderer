"""A standardised interface for interacting with AWS.

Provides simpler methods for :class:`~.cloud_wanderer.CloudWanderer` to call.
"""

import logging
from typing import TYPE_CHECKING, Iterator, List, Optional

import botocore  # type: ignore


# from ..boto3_services import Boto3Services, CloudWandererBoto3Service, MergedServiceLoader
from ..cloud_wanderer_resource import CloudWandererResource
from ..exceptions import BadRequestError, ResourceNotFoundError
from ..models import ActionSet, TemplateActionSet, ServiceResourceType
from ..urn import URN
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

        cloudwanderer_boto3_session:
            boto3_session (boto3.session.Session):
                A CloudWandererBoto3Session session, if not provided the default will be used.
        """
        self.cloudwanderer_boto3_session = cloudwanderer_boto3_session or CloudWandererBoto3Session()

    # def get_resource(self, urn: URN, include_subresources: bool = True) -> Iterator[CloudWandererResource]:
    #     """Yield the resource picked out by this URN and optionally its subresources.

    #     Arguments:
    #         urn (URN): The urn of the resource to get.
    #         include_subresources: Whether or not to additionally yield the subresources of the resource.
    #     """
    #     try:
    #         resource = self.boto3_services.get_resource_from_urn(urn=urn)
    #     except ResourceNotFoundError:
    #         return None
    #     except BadRequestError:
    #         logger.debug(
    #             f"Got BadRequestError while getting {urn}, as AWS services commonly return 4xx errors other than 404 "
    #             "for resource non-existence we are interpreting this as the resource does not exist."
    #         )
    #         return None
    #     subresource_urns = []
    #     if include_subresources:
    #         for subresource in resource.get_subresources():
    #             subresource_urns.append(subresource.urn)
    #             yield CloudWandererResource(
    #                 urn=subresource.urn,
    #                 resource_data=subresource.normalized_raw_data,
    #                 secondary_attributes=list(subresource.get_secondary_attributes()),
    #             )
    #     yield CloudWandererResource(
    #         urn=urn,
    #         subresource_urns=subresource_urns,
    #         resource_data=resource.normalized_raw_data,
    #         secondary_attributes=list(resource.get_secondary_attributes()),
    #     )

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
        service = self.cloudwanderer_boto3_session.resource(service_name=service_name, region_name=region)
        resource_map: ResourceMap = service.service_map.get_resource_map(resource_type)
        try:
            for resource in service.collection(resource_type=resource_type, filters=resource_map.default_filters):
                for dependent_resource_type in resource.dependent_resource_types:
                    for dependent_resource in resource.collection(resource_type=dependent_resource_type):
                        yield CloudWandererResource(
                            urn=dependent_resource.get_urn(),
                            resource_data=dependent_resource.normalized_raw_data,
                            parent_urn=resource.get_urn(),
                            secondary_attributes=list(dependent_resource.get_secondary_attributes()),
                        )
                yield CloudWandererResource(
                    urn=resource.get_urn(),
                    resource_data=resource.normalized_raw_data,
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
            service = self.cloudwanderer_boto3_session.resource(service_name=service_name)
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
