"""A standardised interface for interacting with AWS.

Provides simpler methods for :class:`~.cloud_wanderer.CloudWanderer` to call.
"""

import logging
from typing import TYPE_CHECKING, Any, Dict, Iterator, List, Optional, cast

import botocore

from ..base import CloudInterface, ServiceResourceTypeFilter
from ..cloud_wanderer_resource import CloudWandererResource
from ..exceptions import UnsupportedResourceTypeError
from ..models import ActionSet, ServiceResourceType, TemplateActionSet
from ..urn import URN
from .aws_services import AWS_SERVICES
from .models import AWSResourceTypeFilter, ResourceMap
from .session import CloudWandererBoto3Session

if TYPE_CHECKING:
    from .stubs.resource import CloudWandererServiceResource


logger = logging.getLogger(__name__)


def _get_service_resource_type_filter_from_list(
    service_resource_type_filters: List[AWSResourceTypeFilter], service: str, resource_type: str
) -> Optional[AWSResourceTypeFilter]:
    return next(
        iter(
            service_resource_type
            for service_resource_type in service_resource_type_filters
            if service_resource_type.service == service and service_resource_type.resource_type == resource_type
        ),
        None,
    )


class CloudWandererAWSInterface(CloudInterface):
    """Simplifies lookup of Boto3 services and resources."""

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

    def get_enabled_regions(self) -> List[str]:
        """Return the list of regions enabled.

        Fulfils the interface requirements for :class:`cloudwanderer.cloud_wanderer.CloudWanderer` to call.
        """
        return self.cloudwanderer_boto3_session.get_enabled_regions()

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

        Raises:
            UnsupportedResourceTypeError: Occurs when we try to get an unsupported resource type.
            botocore.exceptions.ClientError: Raises from Boto3 client.
        """
        validated_resource_type_filters = self._type_check_filter_objects(service_resource_type_filters or {})
        try:
            service = self.cloudwanderer_boto3_session.resource(
                service_name=cast(AWS_SERVICES, urn.service), region_name=urn.region, **(client_args or {})
            )
            if service.service_map.is_global_service and service.service_map.global_service_region != urn.region:
                logger.info(
                    "Creating service in %s instead of the resource's %s region because the service has a global API",
                    service.service_map.global_service_region,
                    urn.region,
                )
                service = self.cloudwanderer_boto3_session.resource(
                    service_name=cast(AWS_SERVICES, urn.service), region_name=service.service_map.global_service_region
                )
            resource = service.resource(resource_type=urn.resource_type, identifiers=urn.resource_id_parts)
            if not hasattr(resource, "load"):
                raise UnsupportedResourceTypeError(f"Resource type {urn.resource_type} doesn't support get_resource()")
            logger.info("Loading resource data.")
            resource.load()
            resource.fetch_secondary_attributes()

        except botocore.exceptions.ClientError as ex:
            error_code = ex.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if not error_code:
                raise
            if error_code == 404:
                return None
            if error_code >= 400 and error_code < 500:
                return None
            raise
        if not resource.meta.data:
            logger.warning("Found no data for %s", urn)
            return None

        dependent_resource_urns = []
        if include_dependent_resources:
            for dependent_resource in self._get_dependent_resources(resource, validated_resource_type_filters):
                dependent_resource_urns.append(dependent_resource.urn)
                yield dependent_resource
        yield CloudWandererResource(
            urn=resource.get_urn(),
            resource_data=resource.normalized_raw_data,
            dependent_resource_urns=dependent_resource_urns,
            relationships=resource.relationships,
        )

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
            service_resource_type_filters: A :class:`AWSResourceTypeFilter` list to filter resources.
            client_args: Additional keyword arguments will be passed down to the Boto3 client.

        Raises:
            botocore.exceptions.ClientError: Occurs if the Boto3 Client Errors.
        """
        validated_resource_type_filters = self._type_check_filter_objects(service_resource_type_filters or {})
        service_name = cast(AWS_SERVICES, service_name)
        logger.info("Getting %s %s resources from %s", service_name, resource_type, region)
        service = self.cloudwanderer_boto3_session.resource(
            service_name=service_name, region_name=region, **(client_args or {})
        )
        resource_map: ResourceMap = service.service_map.get_resource_map(resource_type)
        base_resource_filter = (
            _get_service_resource_type_filter_from_list(
                service_resource_type_filters=validated_resource_type_filters,
                service=service_name,
                resource_type=resource_type,
            )
            or resource_map.default_aws_resource_type_filter
        )
        try:
            for resource in service.collection(
                resource_type=resource_type, filters=base_resource_filter.botocore_filters
            ):
                resource.fetch_secondary_attributes()
                if not next(base_resource_filter.filter_jmespath(resources=[resource]), None):
                    logger.info(
                        "Skipping %s because it did not match one of the jmespath filters for this resource type",
                        resource,
                    )
                    continue
                dependent_resource_urns = []
                for dependent_resource in self._get_dependent_resources(resource, validated_resource_type_filters):
                    dependent_resource_urns.append(dependent_resource.urn)
                    yield dependent_resource
                yield CloudWandererResource(
                    urn=resource.get_urn(),
                    resource_data=resource.normalized_raw_data,
                    dependent_resource_urns=dependent_resource_urns,
                    relationships=resource.relationships,
                )
        except botocore.exceptions.EndpointConnectionError:
            logger.info("%s %s not supported in %s", service_name, resource_type, region)
            return
        except botocore.exceptions.ClientError as ex:
            if ex.response["Error"]["Code"] == "InvalidAction":
                logger.info("%s %s not supported in %s", service_name, resource_type, region)
                return
            raise

    def _get_dependent_resources(
        self,
        resource: "CloudWandererServiceResource",
        service_resource_type_filters: Optional[List[AWSResourceTypeFilter]],
    ) -> Iterator[CloudWandererResource]:
        for dependent_resource_type in resource.dependent_resource_types:
            logger.info(
                "Getting %s %s dependent resources from %s for %s",
                resource.service_name,
                dependent_resource_type,
                resource.get_region(),
                resource.get_urn().resource_id,
            )
            dependent_resource_map = resource.service_map.get_resource_map(dependent_resource_type)
            dependent_resource_filter = (
                _get_service_resource_type_filter_from_list(
                    service_resource_type_filters=service_resource_type_filters or [],
                    service=resource.service_name,
                    resource_type=dependent_resource_type,
                )
                or dependent_resource_map.default_aws_resource_type_filter
            )
            for dependent_resource in resource.collection(
                resource_type=dependent_resource_type,
                filters=dependent_resource_filter.botocore_filters,
            ):
                dependent_resource.fetch_secondary_attributes()

                if not next(dependent_resource_filter.filter_jmespath(resources=[dependent_resource]), None):
                    logger.info(
                        "Skipping %s because it did not match one of the jmespath " "filters for this resource type",
                        dependent_resource,
                    )
                    continue
                logger.debug("Found %s", dependent_resource)
                if dependent_resource.resource_map.requires_load or (
                    not dependent_resource.meta.data and hasattr(dependent_resource, "load")
                ):
                    dependent_resource.load()
                urn = dependent_resource.get_urn()
                yield CloudWandererResource(
                    urn=urn,
                    resource_data=dependent_resource.normalized_raw_data,
                    parent_urn=resource.get_urn(),
                    relationships=dependent_resource.relationships,
                )

    def get_resource_discovery_actions(
        self, regions: List[str] = None, service_resource_types: List[ServiceResourceType] = None
    ) -> List[ActionSet]:
        """Return the ActionSets required to discover resources according to the params.

        Arguments:
            regions: List of regions to discover resources in
            service_resource_types: List of service resource types to discover

        """
        service_resource_types = service_resource_types or []
        discovery_regions = regions or self.cloudwanderer_boto3_session.get_enabled_regions()

        service_names = [resource_type.service for resource_type in service_resource_types]
        action_sets = []
        service_names = service_names or self.cloudwanderer_boto3_session.get_available_resources()
        logger.debug("Getting actions for: %s", service_names)
        for service_name in service_names:
            service_specific_resource_types = [
                resource_type.resource_type
                for resource_type in service_resource_types
                if resource_type.service == service_name
            ]
            service = self.cloudwanderer_boto3_session.resource(service_name=cast(AWS_SERVICES, service_name))
            action_sets.extend(
                self._get_discovery_action_templates_for_service(
                    service=service, resource_types=service_specific_resource_types, discovery_regions=discovery_regions
                )
            )

        return self._inflate_action_set_regions(action_sets)

    def _type_check_filter_objects(
        self, service_resource_type_filters=List[ServiceResourceTypeFilter]
    ) -> List[AWSResourceTypeFilter]:
        """Raise exception if not all :class:`ServiceResourceTypeFilter` in the list are :class:`AWSResourceTypeFilter`.

        Parameters:
            service_resource_type_filters: The filters to validate they are the correct type.

        Raises:
            ValueError: If not all service_resource_type_filters are :class:`AWSResourceTypeFilter`
        """
        if not all(
            isinstance(service_resource_type_filter, AWSResourceTypeFilter)
            for service_resource_type_filter in service_resource_type_filters
        ):
            raise ValueError(
                "All service_resource_type_filters must be " "AWSResourceTypeFilter when using the aws cloud interface."
            )
        return service_resource_type_filters

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
                    service=service, resource=resource, discovery_regions=discovery_regions
                )
            )
        return action_templates

    def _get_discovery_action_templates_for_resource(
        self,
        service: "CloudWandererServiceResource",
        resource: "CloudWandererServiceResource",
        discovery_regions: List[str],
    ) -> List[TemplateActionSet]:
        action_templates = []

        logger.debug("Getting actions for %s in %s", resource.resource_type, discovery_regions)

        action_templates = resource.get_discovery_action_templates(discovery_regions=discovery_regions)
        if not action_templates:
            return []
        logger.debug("getting actions for: %s", resource.dependent_resource_types)
        for dependent_resource_type in resource.dependent_resource_types:
            dependent_resource = service.resource(dependent_resource_type, empty_resource=True)
            action_templates.extend(
                dependent_resource.get_discovery_action_templates(discovery_regions=discovery_regions)
            )

        return action_templates
