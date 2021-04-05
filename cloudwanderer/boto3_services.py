"""Classes wrapping :class:`~boto3.resources.base.ServiceResource` objects.

The methods and arguments on these classes somtimes differ in name from those in Boto3's
Resources to make them easier to understand in this context..

Glossary:
    service_name:
        The snake_case name of an AWS service (e.g. ``ec2``)
    resource_type:
        The (unpluralised) snake_case name of the type of the resource in snake case (e.g. ``instance``)
    secondary_attribute:
        An attribute of a resource which requires a secondary API call to retrieve (e.g. VPC Attributes)
    subresource:
        A child resource which does not have its own ARN and must be queried by referencing
        its parent resource's ID (e.g. inline role policies). Different from Boto3 subresources which simply
        indicate a hierarchical relationship between resources (e.g. subnets are a child resource of vpcs).
"""

import logging
from functools import lru_cache
from typing import Generator, List, NamedTuple, Optional, Tuple, Type

import boto3
import botocore  # type: ignore
import jmespath  # type: ignore
from boto3.resources.base import ServiceResource
from boto3.resources.factory import ResourceFactory
from boto3.resources.model import Action, Collection, ResourceModel
from boto3.utils import ServiceContext

from .boto3_helpers import _clean_boto3_metadata, get_shape
from .boto3_loaders import MergedServiceLoader, ResourceMap, ServiceMap, ServiceMappingLoader
from .cloud_wanderer_resource import SecondaryAttribute
from .exceptions import (
    BadRequestError,
    BadUrnAccountIdError,
    BadUrnRegionError,
    BadUrnSubResourceError,
    ResourceNotFoundError,
    UnsupportedResourceTypeError,
)
from .models import CleanupAction, GetAction, GetAndCleanUp
from .typing_helpers import lru_cache_property
from .urn import URN

logger = logging.getLogger(__name__)


class CloudWandererBoto3ResourceFactory:
    """Factory class for generating Boto3 Resource objects."""

    def __init__(self, boto3_session: boto3.session.Session = None) -> None:
        """Initialise the ResourceFactory.

        Arguments:
            boto3_session (boto3.session.Session): The :class:`boto3.session.Session` object to use for any queries.
        """
        self.boto3_session = boto3_session or boto3.session.Session()
        self.emitter = self.boto3_session.events
        self.factory = ResourceFactory(self.emitter)

    def load(self, service_name: str, resource_definitions: dict, service_definition: dict) -> Type:
        """Load the specified resource definition dictionaries into a Resource object.

        Arguments:
            service_name (str):
                The name of the service to load (e.g. ``'ec2'``)
            resource_definitions (dict):
                A dict describing the resource definitions.
                This is the ``'resources'`` key in each ``resource_definition`` json.
            service_definition (dict):
                A dict describing the service definition.
                This is the ``'service'`` key in each ``resource_definition`` json.
        """
        service_context = ServiceContext(
            service_name=service_name,
            resource_json_definitions=resource_definitions,
            service_model=self._get_service_model(service_name),
            service_waiter_model=None,
        )

        return self.factory.load_from_definition(
            resource_name=service_name,
            single_resource_json_definition=service_definition,
            service_context=service_context,
        )

    @lru_cache()
    def _get_service_model(self, service_name: str) -> botocore.model.ServiceModel:
        """Return the botocore service model corresponding to this service.

        Arguments:
            service_name: The service name to get the service model of.
        """
        logger.debug("Getting service model for %s", service_name)
        client = self.boto3_session.client(service_name=service_name)  # type: ignore
        return client.meta.service_model


class Boto3Services:
    """Wraps Boto3 Session.

    Allows us to:

    1. Wrap Boto3 ServiceResource objects with CloudWandererBoto3Service objects.
    2. Inject custom service definitions into our :class:`CloudWandererBoto3ResourceFactory` \
        and return them alongside the default Boto3 ServiceResource objects.

    Used by :class:`~cloudwanderer.aws_interface.CloudWandererAWSInterface` to instantiate
    services and can be used to get resources from their URN.
    """

    def __init__(
        self,
        boto3_session: boto3.session.Session = None,
        service_loader: MergedServiceLoader = None,
        service_mapping_loader: ServiceMappingLoader = None,
        account_id: str = None,
    ) -> None:
        """Initialise the Boto3SessionWrapper.

        Arguments:
            boto3_session:
                The :class:`boto3.session.Session` object to use for any queries.
            service_loader:
                Optionally specify your own service loader if you wish to insert your own resources.
            service_mapping_loader:
                Optionally specify your own service mapping loader if you wish to insert your own service mappings.
            account_id:
                Optionally specify your account id to save a call to STS.
        """
        self.boto3_session = boto3_session or boto3.session.Session()
        self._factory = CloudWandererBoto3ResourceFactory(boto3_session=self.boto3_session)
        self._loader = service_loader or MergedServiceLoader()
        self._service_mapping_loader = service_mapping_loader or ServiceMappingLoader()
        self._account_id = account_id

    @property
    def available_services(self) -> List[str]:
        """Return a list of service names that can be loaded by :meth:`Boto3Services.get_service`."""
        return self._loader.available_services

    @property  # type: ignore
    @lru_cache_property
    def account_id(self) -> str:
        """Return the AWS Account ID our Boto3 session is authenticated against."""
        if self._account_id:
            return self._account_id
        sts = self.boto3_session.client("sts")
        return sts.get_caller_identity()["Account"]

    def get_service(self, service_name: str, region_name: str = None, **kwargs) -> "CloudWandererBoto3Service":
        """Return the :class`CloudWandererBoto3Service` by this name.

        Arguments:
            service_name: The name of the service to instantiate.
            region_name: The region to instantiate the service for.
            **kwargs: Additional keyword args will be passed to the Boto3 client.
        """
        service_method = self._get_service_method(service_name)
        return CloudWandererBoto3Service(
            boto3_service=service_method(client=self._get_client(service_name, region_name=region_name, **kwargs)),
            service_map=ServiceMap.factory(
                name=service_name,
                definition=self._service_mapping_loader.get_service_mapping(service_name=service_name),
            ),
            account_id=self.account_id,
            enabled_regions=self.enabled_regions,
            region_name=region_name,
            boto3_session=self.boto3_session,
        )

    def get_empty_service(self, service_name: str, region_name: str = None) -> "CloudWandererBoto3Service":
        """Return the :class`CloudWandererBoto3Service` by this name without a Boto3 Client instantiated.

        Useful for querying service/resource metadata.

        Arguments:
            service_name: The name of the service to instantiate.
            region_name: The region to instantiate the service for.
        """
        logger.debug("Getting empty service for %s in %s", service_name, region_name)
        service_method = self._get_service_method(service_name)
        return CloudWandererBoto3Service(
            boto3_service=service_method(client=self._get_default_client(service_name)),
            service_map=self._get_service_map(service_name),
            account_id=self.account_id,
            enabled_regions=self.enabled_regions,
            region_name=region_name,
            boto3_session=self.boto3_session,
        )

    @lru_cache()
    def _get_service_map(self, service_name: str) -> ServiceMap:
        logger.debug("Getting service map for %s", service_name)
        return ServiceMap.factory(
            name=service_name,
            definition=self._service_mapping_loader.get_service_mapping(service_name=service_name),
        )

    @lru_cache()
    def _get_default_client(self, service_name: str) -> botocore.client.BaseClient:
        logger.debug("Getting default client for %s", service_name)
        return self._get_client(service_name=service_name, region_name="us-east-1")

    def _get_client(self, service_name: str, region_name: str = None, **kwargs) -> botocore.client.BaseClient:
        return self.boto3_session.client(service_name, region_name=region_name, **kwargs)  # type: ignore

    @lru_cache()
    def _get_service_method(self, service_name: str) -> Type:
        logger.debug("Getting service_method for %s", service_name)
        service_definition = self._loader.get_service_definition(service_name=service_name)
        return self._factory.load(
            service_name=service_name,
            service_definition=service_definition["service"],
            resource_definitions=service_definition["resources"],
        )

    def get_resource_from_urn(self, urn: URN) -> "CloudWandererBoto3Resource":
        """Return the :class:`CloudWandererBoto3Resource` resource picked out by this urn.

        Arguments:
            urn (URN): The urn of the resource to get.

        Raises:
            BadUrnAccountIdError: When the account ID of the URN does not match the account id of the current session.
            BadUrnRegionError: When the region of the URN is not possible with the service and/or resource type.
        """
        if urn.account_id != self.account_id:
            raise BadUrnAccountIdError(f"{urn} exists in an account other than the current one ({self.account_id}).")

        service = self.get_service(urn.service, urn.region)
        if service.service_map.global_service_region != urn.region and not service.service_map.regional_resources:
            raise BadUrnRegionError(f"{urn}'s service does not have resources in {urn.region}")
        return service.get_resource_from_urn(urn)

    @property  # type: ignore
    @lru_cache_property
    def enabled_regions(self) -> List[str]:
        """Return a list of enabled regions in this account."""
        regions = self.boto3_session.client("ec2").describe_regions()["Regions"]
        return [region["RegionName"] for region in regions if region["OptInStatus"] != "not-opted-in"]


class CloudWandererBoto3Service:
    """Wraps Boto3 :class:`~boto3.resources.base.ServiceResource` service-level objects.

    Allows us to include additional CloudWanderer specific functionality.
    The object represents an AWS service (e.g. ``ec2``) in a specific region.
    Used to get resources from the API as well as get metadata about the resource type from Boto3.
    """

    def __init__(
        self,
        boto3_service: ServiceResource,
        service_map: ServiceMap,
        account_id: str,
        boto3_session: boto3.session.Session,
        region_name: str = None,
        enabled_regions: List[str] = None,
    ) -> None:
        """Instantiate CloudWandererBoto3Service.

        Arguments:
            boto3_service: The boto3 service object to wrap.
            service_map: The CloudWanderer service map that provides additional context about this service.
            account_id: The ID of the AWS account our session is in.
            region_name: The region to get resources from for this service.
            boto3_session: The Boto3 session that created this client.
            enabled_regions: The list of regions currently enabled.
        """
        self.boto3_service = boto3_service
        self.boto3_session = boto3_session
        self.service_map = service_map
        self.account_id = account_id
        self.region_name = region_name
        self._enabled_regions = enabled_regions

    @property
    def resource_types(self) -> List[str]:
        """Return a list of snake_case resource types available on this service."""
        collection_resource_types = [
            collection.resource.type for collection in self._collections if collection.resource
        ]
        return [
            botocore.xform_name(resource.name)
            for resource in self._subresources
            if resource.resource and resource.resource.type in collection_resource_types
        ]

    @property
    def resource_summary(self) -> List["ResourceSummary"]:
        """Return a summary of resource types in this service."""
        summaries = []
        service_model = self.boto3_service.meta.client.meta.service_model
        service_friendly_name = service_model.metadata["serviceId"]

        for resource_type in self.resource_types:
            resource = self._get_empty_resource(resource_type)
            if not resource:
                logger.debug("No %s resource type found %s", resource_type, self.name)
                continue
            summaries.append(
                ResourceSummary(
                    resource_type=resource_type,
                    resource_friendly_name=resource.boto3_resource.meta.resource_model.name,
                    service_friendly_name=service_friendly_name,
                    secondary_attribute_names=resource.secondary_attribute_names,
                    subresource_types=resource.subresource_types,
                )
            )
        return summaries

    def _get_empty_resource(self, resource_type: str) -> Optional["CloudWandererBoto3Resource"]:
        """Return a resource object of resource_type which is not associated with a specific AWS resource.

        Useful for interrogating metadata about that type of resource.

        Arguments:
            resource_type: The CloudWanderer style (snake_case) resource type.
        """
        boto3_resource = self._get_boto3_resource(resource_type)
        boto3_resource_getter = getattr(self.boto3_service, boto3_resource.name)
        if not boto3_resource.resource:
            return None
        blank_args = ["" for identifier in boto3_resource.resource.identifiers]
        return CloudWandererBoto3Resource(
            account_id=self.account_id,
            cloudwanderer_boto3_service=self,
            boto3_resource=boto3_resource_getter(*blank_args),
            service_map=self.service_map,
        )

    def get_resource_from_urn(self, urn: URN) -> "CloudWandererBoto3Resource":
        """Return the :class:`CloudWandererBoto3Resource` resource picked out by this urn.

        Arguments:
            urn (URN): The urn of the resource to get.

        Raises:
            BadUrnSubResourceError: Occurs when we try to fetch a subresource diretly.
            BadRequestError: Occurs when the AWS API returns a 4xx HTTP error other than 404.
            ResourceNotFoundError: Occurs when the AWS API Returns a 404 HTTP error.
            UnsupportedResourceTypeError: Occurs when the definition for the resource does not support loading by id.
            botocore.exceptions.ClientError: Boto3 Client Error
        """
        try:
            boto3_service_resource = self._get_boto3_resource(urn.resource_type)
            boto3_resource_getter = getattr(self.boto3_service, boto3_service_resource.name)
            if urn.is_subresource:
                boto3_resource = boto3_resource_getter(urn.parent_resource_id, urn.subresource_id)
            else:
                boto3_resource = boto3_resource_getter(urn.resource_id)
        except ValueError:
            raise BadUrnSubResourceError(f"{urn} is a sub resource, please call get_resource against its parent.")

        if not hasattr(boto3_resource, "load"):
            raise UnsupportedResourceTypeError(f"{urn.resource_type} does not support loading by ID.")

        try:
            boto3_resource.load()
        except botocore.exceptions.ClientError as ex:
            error_code = ex.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if error_code == 404:
                raise ResourceNotFoundError(f"{urn} was not found") from ex
            if error_code >= 400 and error_code < 500:
                raise BadRequestError(f"A request error was returned while fetching {urn}") from ex
            raise
        return CloudWandererBoto3Resource(
            account_id=self.account_id,
            cloudwanderer_boto3_service=self,
            boto3_resource=boto3_resource,
            service_map=self.service_map,
        )

    def _get_boto3_resource(self, resource_type: str) -> Action:
        """Return a callable Boto3 service resource of resource_type.

        Arguments:
            resource_type: The *snake_case singluar) resource type (e.g. ``instance``)
        """
        action = next(
            resource for resource in self._subresources if botocore.xform_name(resource.name) == resource_type
        )
        return action

    def get_resources(self, resource_type: str) -> Generator["CloudWandererBoto3Resource", None, None]:
        """Yield all resources of resource_type in this region.

        Arguments:
            resource_type: The snake_case resource type to get.
        """
        collection_class = self._get_collection_from_resource_type(resource_type)
        if not collection_class:
            return
        collection = getattr(self.boto3_service, collection_class.name)
        yield from (
            CloudWandererBoto3Resource(
                account_id=self.account_id,
                cloudwanderer_boto3_service=self,
                boto3_resource=boto3_resource,
                service_map=self.service_map,
            )
            for boto3_resource in collection.all()
        )

    def _get_collection_from_resource_type(self, resource_type: str) -> Optional[Collection]:
        """Return a collection given a CloudWanderer style (snake_case singular) resource type.

        The resource type we're passed in is NOT a Boto3 style resource type.
        It is actually a Boto3 subresource name that we need to first get the type of.

        Arguments:
            resource_type: The CloudWanderer style (snake_case) resource type name.
        """
        boto3_resource_type = self._get_boto3_resource_type_from_subresource_name(subresource_name=resource_type)
        if not boto3_resource_type:
            return None
        return self._get_collection_from_boto3_resource_type(boto3_resource_type)

    def _get_boto3_resource_type_from_subresource_name(self, subresource_name: str) -> Optional[str]:
        """Return the resource_type for a given subresource name.

        Resource names *almost* always match their resource type, but not always.
        I'm kooking at you EC2 KeyPair!

        Arguments:
            subresource_name: The snake_case CloudWanderer style subresource name.
        """
        return next(
            (
                resource.resource.type
                for resource in self._subresources
                if botocore.xform_name(resource.name) == subresource_name and resource.resource
            ),
            None,
        )

    def _get_collection_from_boto3_resource_type(self, boto3_resource_type: str) -> Collection:
        """Return the Collection corresponding to a given Boto3 style (PascalCase) resource type.

        Arguments:
            boto3_resource_type: The PascalCase name for the Boto3 resource type.
        """
        return next(
            collection
            for collection in self._collections
            if collection.resource and collection.resource.type == boto3_resource_type
        )

    @property
    def _collections(self) -> List[Collection]:
        return self.boto3_service.meta.resource_model.collections

    @property
    def _subresources(self) -> List[Action]:
        return self.boto3_service.meta.resource_model.subresources  # type: ignore

    @property
    def region(self) -> str:
        """Return the name of the region this service is querying."""
        if self.region_name is not None:
            return self.region_name
        client_region = self.boto3_service.meta.client.meta.region_name
        if client_region == "aws-global":
            return self.service_map.global_service_region or client_region
        return client_region

    @property
    def should_query_resources_in_region(self) -> bool:
        """Return whether this service's resources should be queried from this region."""
        if not self.service_map.is_global_service:
            return True
        return self.service_map.is_global_service and self.service_map.global_service_region == self.region

    @property
    def get_regions_discovered_from_region(self) -> List[str]:
        """Return a list of regions resources will have been discovered in by querying this resource in this region."""
        if not self.should_query_resources_in_region:
            return []
        if self.service_map.regional_resources and self.service_map.global_service_region == self.region:
            return self.enabled_regions
        return [self.region]

    @property
    def enabled_regions(self) -> List[str]:
        """Return a list of enabled regions in this account."""
        if not self._enabled_regions:
            regions = self.boto3_session.client("ec2").describe_regions()["Regions"]
            self._enabled_regions = [
                region["RegionName"] for region in regions if region["OptInStatus"] != "not-opted-in"
            ]
        return self._enabled_regions

    @property
    def name(self) -> str:
        """Return the snake_case name of this service."""
        return self.boto3_service.meta.service_name


class CloudWandererBoto3Resource:
    """Wraps Boto3 R:class:`~boto3.resources.base.ServiceResource` resource-level objects.

    Allows us to provide additional functionality specific to CloudWanderer.

    This is almost always tied to a specific resource that exists in AWS, but is occasionally instantiated
    abstractly in order to interrogate metadata about this resource type.
    """

    def __init__(
        self,
        account_id: str,
        boto3_resource: ServiceResource,
        cloudwanderer_boto3_service: CloudWandererBoto3Service,
        service_map: ServiceMap,
    ) -> None:
        self.account_id = account_id
        self.boto3_resource = boto3_resource
        self.cloudwanderer_boto3_service = cloudwanderer_boto3_service
        self.service_map = service_map
        self.resource_map = self.service_map.get_resource_map(self.boto3_resource.meta.resource_model.name)

    @property
    def resource_type(self) -> str:
        """Return the snake_case resource type of this resource."""
        return botocore.xform_name(self.boto3_resource.meta.resource_model.name)

    @property
    def service(self) -> str:
        """Return the snake_case service type for this resource."""
        return self.service_map.name

    @property
    def id(self) -> str:
        """Return the id of the resource.

        Used for URN generation.
        """
        id_members = [x.name for x in self.boto3_resource.meta.resource_model.identifiers]
        resource_ids = []
        for id_member in id_members:
            id_part = str(getattr(self.boto3_resource, id_member))
            if id_part.startswith("arn:"):
                id_part = "".join(id_part.split(":")[5:])
            resource_ids.append(id_part)
        return "/".join(resource_ids)

    @property
    def raw_data(self) -> dict:
        """Return the raw dictionary data for this resource."""
        return self.boto3_resource.meta.data

    @property
    def normalised_raw_data(self) -> dict:
        """Return the raw data ditionary for this resource, ensuring that all keys for this resource are present."""
        result = {attribute: None for attribute in get_shape(self.boto3_resource).members.keys()}
        result.update(self.boto3_resource.meta.data or {})
        return _clean_boto3_metadata(result)

    @property
    def urn(self) -> URN:
        """Return the resource's Universal Resource Name."""
        return URN(
            account_id=self.account_id,
            region=self.region,
            service=self.service,
            resource_type=self.resource_type,
            resource_id=self.id,
        )

    @property
    def region(self) -> str:
        """Return the region for this resource.

        Typically this just takes the region of the session the resource was discovered from.
        However for some resources (e.g. S3 buckets) it performs an API call to look it up.
        """
        if not self.service_map.is_global_service:
            return self._boto3_client.meta.region_name

        if not self.service_map.regional_resources:
            return self.service_map.global_service_region

        return self._get_region()

    @property
    def secondary_attribute_names(self) -> List[str]:
        """Return a list fof secondary attributes its possible for this resource type to have."""
        names = []
        for secondary_attribute_model in self.secondary_attribute_models:
            names.append(botocore.xform_name(secondary_attribute_model.name))
        return names

    def get_secondary_attributes(self) -> Generator[SecondaryAttribute, None, None]:
        """Return the secondary attributes for this resource."""
        for secondary_attribute_model in self.secondary_attribute_models:
            secondary_attribute = getattr(self.boto3_resource, secondary_attribute_model.name)()
            secondary_attribute.load()
            yield SecondaryAttribute(
                name=botocore.xform_name(secondary_attribute.meta.resource_model.name),
                **_clean_boto3_metadata(secondary_attribute.meta.data),
            )

    @property
    def secondary_attribute_models(self) -> Generator[Action, None, None]:
        """Return the secondary attribute models it's possible for this resource type to have."""
        for subresource_mapping, subresource_model in self._boto3_subresource_models:
            if subresource_mapping.type == "secondaryAttribute":
                yield subresource_model

    @property
    def _boto3_subresource_models(self) -> Generator[Tuple[ResourceMap, Action], None, None]:
        """Return the Boto3 subresource mappings and models that exist for this resource type.

        This is used exclusively for secondary attributes because secondary attributes have a 1:1 relationship with
        their parent resource.
        """
        subresource_models: List[Action] = self.boto3_resource.meta.resource_model.subresources  # type: ignore
        for subresource_model in subresource_models:
            subresource_mapping = self.service_map.get_resource_map(subresource_model.name)
            yield subresource_mapping, subresource_model

    @property
    def subresource_types(self) -> List[str]:
        """Return a list of CloudWanderer style subresource types it's possible for this resource type to have."""
        types = []
        for subresource_model in self.subresource_models:
            if not subresource_model.resource:
                continue
            types.append(botocore.xform_name(subresource_model.resource.model.name))
        return types

    def get_subresources(self) -> Generator["CloudWandererBoto3Resource", None, None]:
        """Return the CloudWanderer style subresources of this resource."""
        for subresource_model in self.subresource_models:
            collection = getattr(self.boto3_resource, subresource_model.name)
            for boto3_resource in collection.all():
                if hasattr(boto3_resource, "load"):
                    # If the resource does not have a `load` that means that the response returned
                    # by the collection request (e.g. listAccessKeys) contains all the information that is
                    # available for this resource.
                    # If it does have a load, then we need to get that additional data.
                    boto3_resource.load()
                yield CloudWandererBoto3Resource(
                    account_id=self.account_id,
                    cloudwanderer_boto3_service=self.cloudwanderer_boto3_service,
                    boto3_resource=boto3_resource,
                    service_map=self.service_map,
                )

    @property
    def subresource_models(self) -> Generator[Collection, None, None]:
        """Yield the Boto3 models for the CloudWanderer style subresources of this resource type."""
        models = {}
        for collection_resource_map, collection_model in self._boto3_collection_models:
            response_resource = collection_model.resource
            if not response_resource or not self._is_collection_model_a_subresource(
                collection_resource_map, response_resource.model
            ):
                continue

            collection_resource_name = botocore.xform_name(response_resource.model.name)
            models[collection_resource_name] = collection_model
        yield from models.values()

    @property
    def get_and_cleanup_actions(self) -> GetAndCleanUp:
        """Return the query and cleanup actions to be performed if getting this resource type in this region."""
        actions = GetAndCleanUp([], [])

        actions.get_actions.append(
            GetAction(
                service_name=self.service,
                region=self.cloudwanderer_boto3_service.region,
                resource_type=self.resource_type,
            )
        )
        for region in self.cloudwanderer_boto3_service.get_regions_discovered_from_region:
            actions.cleanup_actions.append(
                CleanupAction(
                    service_name=self.service,
                    region=region,
                    resource_type=self.resource_type,
                )
            )
            for subresource_type in self.subresource_types:
                actions.cleanup_actions.append(
                    CleanupAction(
                        service_name=self.service,
                        region=region,
                        resource_type=subresource_type,
                    )
                )
        return actions

    @property
    def parent_resource_type(self) -> str:
        """Return the resource type of the parent (if it has one)."""
        return self.resource_map.parent_resource_type

    @property
    def _boto3_collection_models(self) -> Generator[Tuple[ResourceMap, Collection], None, None]:
        """Yield the ResourceMaps and Collections for this resource type.

        This is used exclusively for subresources because subresources have a 1:many relationship with
        their parent resource.
        """
        for boto3_collection in self.boto3_resource.meta.resource_model.collections:
            if boto3_collection.resource is None:
                continue
            collection_resource_map = self.service_map.get_resource_map(boto3_collection.resource.model.name)
            yield collection_resource_map, boto3_collection

    def _is_collection_model_a_subresource(
        self, collection_resource_map: ResourceMap, resource_model: ResourceModel
    ) -> bool:
        if collection_resource_map.type == "secondaryAttribute" or resource_model is None:
            return False
        collection_resource_name = botocore.xform_name(resource_model.name)
        if len(resource_model.identifiers) != 2:
            logger.debug(
                "%s has %s identifiers, when valid subresources have 2, skipping",
                collection_resource_name,
                len(resource_model.identifiers),
            )
            return False
        if resource_model.name in self.resource_map.ignored_subresource_types:
            logger.debug(
                "% is defined as an ignored subresource type by the %s servicemap, skipping",
                collection_resource_name,
                self.service_map.name,
            )
            return False
        if collection_resource_name in self.cloudwanderer_boto3_service.resource_types:
            logger.debug("%s is an independent resource, not a subresource skipping", collection_resource_name)
            return False
        return True

    @lru_cache()
    def _get_region(self) -> str:
        """Return the region for a resource which requires an API call to determine its region."""
        region_request_definition = self.resource_map.region_request
        if region_request_definition is None:
            return self.region
        method = getattr(self._boto3_client, region_request_definition.operation)
        result = method(**region_request_definition.build_params(self.boto3_resource))
        return (
            jmespath.search(region_request_definition.path_to_region, result) or region_request_definition.default_value
        )

    @property
    def _boto3_client(self) -> botocore.client.BaseClient:
        return self.boto3_resource.meta.client


class ResourceSummary(NamedTuple):
    """A summary of a resource's subresource types and secondary attribute names."""

    resource_type: str
    resource_friendly_name: str
    service_friendly_name: str
    subresource_types: List[str]
    secondary_attribute_names: List[str]
