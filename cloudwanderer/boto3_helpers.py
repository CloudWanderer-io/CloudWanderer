"""Helper classes and methods for interacting with boto3."""
import logging
from functools import lru_cache
from typing import Iterator, List

import boto3
import botocore
from boto3.resources.model import Collection, ResourceModel
from botocore import xform_name

from .aws_urn import AwsUrn
from .cloud_wanderer_resource import SecondaryAttribute
from .custom_resource_definitions import CustomResourceDefinitions, get_resource_collections
from .service_mappings import GlobalServiceResourceMappingNotFound, ServiceMappingCollection

logger = logging.getLogger(__name__)


class Boto3CommonAttributesMixin:
    """Mixin that provides common informational attributes unique to boto3."""

    @property
    @lru_cache()
    def account_id(self) -> str:
        """Return the AWS Account ID our Boto3 session is authenticated against."""
        sts = self.boto3_session.client("sts")
        return sts.get_caller_identity()["Account"]

    @property
    @lru_cache()
    def region_name(self) -> str:
        """Return the default AWS region."""
        return self.boto3_session.region_name

    @property
    @lru_cache()
    def enabled_regions(self) -> List[str]:
        """Return a list of enabled regions in this account."""
        regions = self.boto3_session.client("ec2").describe_regions()["Regions"]
        return [region["RegionName"] for region in regions if region["OptInStatus"] != "not-opted-in"]


class Boto3Getter(Boto3CommonAttributesMixin):
    """Gets Boto3 resources, subresources, and secondary attributes."""

    def __init__(self, boto3_session: boto3.session.Session, service_maps: ServiceMappingCollection) -> None:
        self.boto3_session = boto3_session
        self.service_maps = service_maps
        self.custom_resource_definitions = CustomResourceDefinitions(boto3_session=boto3_session)

    def get_subresources(
        self, boto3_resource: boto3.resources.base.ServiceResource
    ) -> boto3.resources.base.ServiceResource:
        """Return all subresources for this resource.

        Subresources and collections on custom service resources may be subresources we want to collect if
        they are specified in our custom resource definitions.

        Arguments:
            boto3_resource (boto3.resources.base.ServiceResource): The :class:`boto3.resources.base.ServiceResource`
                to get secondary attributes from
        """
        yield from self.get_child_resources(boto3_resource=boto3_resource, resource_type="resource")

    def get_secondary_attributes(self, boto3_resource: boto3.resources.base.ServiceResource) -> SecondaryAttribute:
        """Return all secondary attributes resources for this resource.

        Subresources and collections on custom service resources may be secondary attribute definitions if
        specified in metadata.

        Arguments:
            boto3_resource (boto3.resources.base.ServiceResource): The :class:`boto3.resources.base.ServiceResource`
                to get secondary attributes from
        """
        secondary_attributes = self.get_child_resources(
            boto3_resource=boto3_resource, resource_type="secondaryAttribute"
        )
        for secondary_attribute in secondary_attributes:
            yield SecondaryAttribute(
                name=xform_name(secondary_attribute.meta.resource_model.name),
                **_clean_boto3_metadata(secondary_attribute.meta.data)
            )

    def get_child_resources(
        self, boto3_resource: boto3.resources.base.ServiceResource, resource_type: str
    ) -> boto3.resources.base.ServiceResource:
        """Return all child resources of resource_type for this resource.

        This method contextualises the ``has`` and ``hasMany`` relationships that Boto3 uses to specify subresources.
        If they are found in the service map, then they are subresources or secondary attributes that CloudWanderer
        needs to record into storage. Anything that is not in the servicemap probably represents a relationship between
        base resources (i.e. resources that have ARNs) and that subresource will be captured separately as
        a base resource.

        Arguments:
            boto3_resource (boto3.resources.base.ServiceResource):
                The :class:`boto3.resources.base.ServiceResource`
                to get secondary attributes from
            resource_type (str):
                The resource types to return (either 'secondaryAttribute' or 'resource')
        """
        service_mapping = self.service_maps.get_service_mapping(boto3_resource.meta.service_name)

        for subresource in boto3_resource.meta.resource_model.subresources:
            try:
                resource_mapping = service_mapping.get_resource_mapping(subresource.name)
            except GlobalServiceResourceMappingNotFound:
                continue

            if resource_mapping.resource_type != resource_type:
                continue
            subresource = getattr(boto3_resource, subresource.name)()
            subresource.load()
            yield subresource

        for child_resource_collection in get_resource_collections(boto3_resource):
            try:
                resource_mapping = service_mapping.get_resource_mapping(child_resource_collection.resource.model.name)
            except GlobalServiceResourceMappingNotFound:
                continue
            if resource_mapping.resource_type != resource_type:
                continue
            child_resources = get_resource_from_collection(
                boto3_service=boto3_resource, boto3_resource_collection=child_resource_collection
            )
            for resource in child_resources:
                resource.load()
                yield resource

    def get_child_resource_definitions(
        self, service_name: str, boto3_resource_model: boto3.resources.model.ResourceModel, resource_type: str
    ) -> boto3.resources.model.ResourceModel:
        """Return all child resource models for this resource.

        This method contextualises the ``has`` and ``hasMany`` relationships that Boto3 uses to specify subresources.
        If they are found in the service map, then they are subresources or secondary attributes that CloudWanderer
        needs to record into storage. Anything that is not in the servicemap probably represents a relationship between
        base resources (i.e. resources that have ARNs) and that subresource will be captured separately as
        a base resource.

        Arguments:
            service_name (str):
                The name of the service this model resides in (e.g. ``'ec2'``)
            boto3_resource_model (boto3.resources.model.ResourceModel):
                The :class:`boto3.resources.model.ResourceModel` to get secondary attributes models from
            resource_type (str):
                The resource types to return (either 'secondaryAttribute' or 'resource')
        """
        service_mapping = self.service_maps.get_service_mapping(service_name)

        for subresource in boto3_resource_model.subresources:
            try:
                resource_mapping = service_mapping.get_resource_mapping(subresource.name)
            except GlobalServiceResourceMappingNotFound:
                continue
            if resource_mapping.resource_type != resource_type:
                continue
            yield subresource

        for secondary_attribute_collection in boto3_resource_model.collections:
            try:
                resource_mapping = service_mapping.get_resource_mapping(
                    secondary_attribute_collection.resource.model.name
                )
            except GlobalServiceResourceMappingNotFound:
                continue
            if resource_mapping.resource_type != resource_type:
                continue
            yield secondary_attribute_collection

    def get_resource_urn(self, resource: ResourceModel, region_name: str) -> "AwsUrn":
        service_map = self.service_maps.get_service_mapping(resource.meta.service_name)
        return AwsUrn(
            account_id=self.account_id,
            region=service_map.get_resource_region(resource, region_name),
            service=resource.meta.service_name,
            resource_type=xform_name(resource.meta.resource_model.name),
            resource_id=normalise_resource_id(resource=resource),
        )


def normalise_resource_id(resource: ResourceModel) -> str:
    """Return a resource id suitable for use in a URN.

    Parameters:
        resource (ResourceModel): The resource to generate an ID from.
    """
    id_members = [x.name for x in resource.meta.resource_model.identifiers]
    resource_ids = []
    for id_member in id_members:
        id_part = getattr(resource, id_member)
        if id_part.startswith("arn:"):
            id_part = "".join(id_part.split(":")[5:])
        resource_ids.append(id_part)
    return "/".join(resource_ids)


def _get_resource_attributes(boto3_resource: boto3.resources.base.ServiceResource, snake_case: bool = False) -> dict:
    if snake_case:
        return boto3_resource.meta.resource_model.get_attributes(get_shape(boto3_resource))
    return get_shape(boto3_resource).members


def get_shape(boto3_resource: boto3.resources.base.ServiceResource) -> botocore.model.Shape:
    """Return the Botocore shape of a boto3 Resource.

    Parameters:
        boto3_resource (boto3.resources.base.ServiceResource):
            The resource to get the shape of.
    """
    service_model = boto3_resource.meta.client.meta.service_model
    shape = service_model.shape_for(boto3_resource.meta.resource_model.shape)
    return shape


def _prepare_boto3_resource_data(boto3_resource: boto3.resources.base.ServiceResource) -> dict:
    result = {attribute: None for attribute in _get_resource_attributes(boto3_resource).keys()}
    result.update(boto3_resource.meta.data or {})
    return _clean_boto3_metadata(result)


def _clean_boto3_metadata(boto3_metadata: dict) -> dict:
    """Remove unwanted keys from boto3 metadata dictionaries.

    Arguments:
        boto3_metadata (dict): The raw dictionary of metadata typically found in resource.meta.data
    """
    boto3_metadata = boto3_metadata or {}
    unwanted_keys = ["ResponseMetadata"]
    for key in unwanted_keys:
        if key in boto3_metadata:
            del boto3_metadata[key]
    return boto3_metadata


def get_service_resource_types_from_collections(collections: List[Collection]) -> Iterator[str]:
    """Return all resource names from a list of collections.

    Returns resource names from a list of collections.

    Arguments:
        collections (List[Collection]): The list of collections from which to get resource names.
    """
    for collection in collections:
        yield xform_name(collection.resource.model.name)


def get_resource_collection_by_resource_type(
    boto3_service: boto3.resources.base.ServiceResource, resource_type: str
) -> Collection:
    """Return the resource collection that matches the resource_type (e.g. instance).

    This is as opposed to the collection name (e.g. instances)

    Arguments:
        boto3_service (boto3.resources.base.ServiceResource):
            The service resource from which to return collections
        resource_type (str):
            The resource type for which to return collections
    """
    for boto3_resource_collection in get_resource_collections(boto3_service=boto3_service):
        if xform_name(boto3_resource_collection.resource.model.name) != resource_type:
            continue

        return boto3_resource_collection


def get_resource_from_collection(
    boto3_service: boto3.resources.base.ServiceResource, boto3_resource_collection: boto3.resources.model.Collection
) -> Iterator[ResourceModel]:
    """Return all resources of this resource type (collection) from this service.

    Arguments:
        boto3_service (boto3.resources.base.ServiceResource): The service resource from which to return resources.
        boto3_resource_collection (boto3.resources.model.Collection): The resource collection to get.

    Raises:
        botocore.exceptions.ClientError: A Boto3 client error.
    """
    if not hasattr(boto3_service, boto3_resource_collection.name):
        logger.warning("%s does not have %s", boto3_service.__class__.__name__, boto3_resource_collection.name)
        return
    try:
        yield from getattr(boto3_service, boto3_resource_collection.name).all()
    except botocore.exceptions.EndpointConnectionError as ex:
        logger.warning(ex)
    except botocore.exceptions.ClientError as ex:
        if ex.response["Error"]["Code"] == "InvalidAction":
            logger.warning(ex.response["Error"]["Message"])
            return
        raise
