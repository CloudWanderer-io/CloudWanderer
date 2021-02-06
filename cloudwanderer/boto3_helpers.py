"""Helper classes and methods for interacting with boto3."""
from typing import List, Iterator
import logging
import boto3
import botocore
from botocore import xform_name
from boto3.resources.model import Collection, ResourceModel
from boto3.resources.base import ServiceResource
from .service_mappings import ServiceMappingCollection, GlobalServiceResourceMappingNotFound
from .custom_resource_definitions import CustomResourceDefinitions

logger = logging.getLogger(__name__)


class Boto3CommonAttributesMixin:
    """Mixin that provides common informational attributes unique to boto3."""

    _enabled_regions = None

    @property
    def account_id(self) -> str:
        """Return the AWS Account ID our Boto3 session is authenticated against."""
        if self._account_id is None:
            sts = self.boto3_session.client('sts')
            self._account_id = sts.get_caller_identity()['Account']
        return self._account_id

    @property
    def region_name(self) -> str:
        """Return the default AWS region."""
        return self.boto3_session.region_name

    @property
    def enabled_regions(self) -> List[str]:
        """Return a list of enabled regions in this account."""
        if not self._enabled_regions:
            regions = self.boto3_session.client('ec2').describe_regions()['Regions']
            self._enabled_regions = [
                region['RegionName']
                for region in regions
                if region['OptInStatus'] != 'not-opted-in'
            ]
        return self._enabled_regions


class Boto3Helper(Boto3CommonAttributesMixin):
    """Abstracts some common interactions with Boto3."""

    def __init__(self, boto3_session: boto3.session.Session, service_maps: ServiceMappingCollection) -> None:
        self.boto3_session = boto3_session
        self.service_maps = service_maps
        self.custom_resource_definitions = CustomResourceDefinitions(boto3_session=boto3_session)

    def get_valid_resource_types(self, service_name: str, resource_types: List[str]) -> List[str]:
        service_resource_types = list(self.get_service_resource_types(service_name=service_name))
        if resource_types:
            return [
                resource_type
                for resource_type in resource_types
                if resource_type in service_resource_types
            ]

        return service_resource_types

    def get_all_resource_services(self, **kwargs) -> Iterator[ServiceResource]:
        """Return all boto3 service Resource objects.

        Arguments:
            **kwargs: Additional keyword arguments will be passed down to the Boto3 client.
        """
        for service_name in self.custom_resource_definitions.definitions:
            yield self.get_resource_service_by_name(service_name, **kwargs)

    def get_resource_service_by_name(
            self, service_name: str, **kwargs) -> boto3.resources.model.ResourceModel:
        """Get the resource definition matching this service name.

        Arguments:
            service_name (str):
                The name of the service (e.g. ``'ec2'``) to get.
            **kwargs: Additional keyword arguments will be passed down to the Boto3 client.
        """
        return self.custom_resource_definitions.resource(service_name, **kwargs)

    def get_resource_collections(self, boto3_service: boto3.resources.base.ServiceResource) -> List[Collection]:
        """Return all resource types in this service.

        Arguments:
            boto3_service (boto3.resources.base.ServiceResource): The service resource from which to return collections
        """
        return boto3_service.meta.resource_model.collections

    def get_resource_collection_by_resource_type(
            self, boto3_service: boto3.resources.base.ServiceResource, resource_type: str) -> Iterator[Collection]:
        """Yield the resource collection that matches the resource_type (e.g. instance).

        This is as opposed to the collection name (e.g. instances)

        Arguments:
            boto3_service (boto3.resources.base.ServiceResource):
                The service resource from which to return collections
            resource_type (str):
                The resource type for which to return collections
        """
        for boto3_resource_collection in self.get_resource_collections(boto3_service):
            if xform_name(boto3_resource_collection.resource.model.name) != resource_type:
                continue
            yield boto3_resource_collection

    def get_resource_from_collection(
            self, boto3_service: boto3.resources.base.ServiceResource,
            boto3_resource_collection: boto3.resources.model.Collection) -> Iterator[ResourceModel]:
        """Return all resources of this resource type (collection) from this service.

        Arguments:
            boto3_service (boto3.resources.base.ServiceResource): The service resource from which to return resources.
            boto3_resource_collection (boto3.resources.model.Collection): The resource collection to get.

        Raises:
            botocore.exceptions.ClientError: A Boto3 client error.
        """
        if not hasattr(boto3_service, boto3_resource_collection.name):
            logger.warning('%s does not have %s', boto3_service.__class__.__name__, boto3_resource_collection.name)
            return
        try:
            yield from getattr(boto3_service, boto3_resource_collection.name).all()
        except botocore.exceptions.EndpointConnectionError as ex:
            logger.warning(ex)
        except botocore.exceptions.ClientError as ex:
            if ex.response['Error']['Code'] == 'InvalidAction':
                logger.warning(ex.response['Error']['Message'])
                return
            raise

    def get_service_resource_types(self, service_name: str) -> Iterator[str]:
        """Return all possible resource names for a given service.

        Returns resources for both native boto3 resources and custom cloudwanderer resources.

        Arguments:
            service_name: The name of the service to get resource types for (e.g. ``'ec2'``)
        """
        for collection in self.get_service_resource_collections(service_name):
            yield xform_name(collection.resource.model.name)

    def get_service_resource_types_from_collections(self, collections: List[Collection]) -> Iterator[str]:
        """Return all possible resource names for a given service.

        Returns resources for both native boto3 resources and custom cloudwanderer resources.

        Arguments:
            collections (List[Collection]): The list of collections from which to get resource names.
        """
        for collection in collections:
            yield xform_name(collection.resource.model.name)

    def get_service_resource_collections(self, service_name: str) -> Iterator[Collection]:
        """Return all the resource collections for a given service_name.

        This is crucial to return collections for both native boto3 resources and custom cloudwanderer resources.

        Arguments:
            service_name: The name of the service to get resource types for (e.g. ``'ec2'``)
        """
        boto3_service = self.get_resource_service_by_name(service_name)
        if boto3_service is not None:
            yield from self.get_resource_collections(boto3_service)

    def get_subresources(
            self, boto3_resource: boto3.resources.base.ServiceResource) -> boto3.resources.base.ServiceResource:
        """Return all subresources for this resource.

        Subresources and collections on custom service resources may be subresources we want to collect if
        they are specified in our custom resource definitions.

        Arguments:
            boto3_resource (boto3.resources.base.ServiceResource): The :class:`boto3.resources.base.ServiceResource`
                to get secondary attributes from
        """
        yield from self.get_child_resources(boto3_resource=boto3_resource, resource_type='resource')

    def get_child_resources(
            self, boto3_resource: boto3.resources.base.ServiceResource,
            resource_type: str) -> boto3.resources.base.ServiceResource:
        """Return all child resources of resource_type for this resource.

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

        for child_resource_collection in self.get_resource_collections(boto3_resource):
            try:
                resource_mapping = service_mapping.get_resource_mapping(child_resource_collection.resource.model.name)
            except GlobalServiceResourceMappingNotFound:
                continue
            if resource_mapping.resource_type != resource_type:
                continue
            child_resources = self.get_resource_from_collection(
                boto3_service=boto3_resource,
                boto3_resource_collection=child_resource_collection
            )
            for resource in child_resources:
                resource.load()
                yield resource

    def get_child_resource_definitions(
            self, service_name: str, boto3_resource_model: boto3.resources.model.ResourceModel,
            resource_type: str) -> boto3.resources.model.ResourceModel:
        """Return all secondary attributes models for this resource.

        Subresources and collections on custom service resources may be secondary attribute definitions if
        specified in metadata.

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
                    secondary_attribute_collection.resource.model.name)
            except GlobalServiceResourceMappingNotFound:
                continue
            if resource_mapping.resource_type != resource_type:
                continue
            yield secondary_attribute_collection

    def resource_regions_returned_from_api_region(
            self, service_name: str, region_name: str) -> Iterator[str]:
        """Return a list of regions which will be discovered for this resource type in this region.

        Usually this will just return the region which is passed in, but some resources are only queryable
        from a single region despite having resources from multiple regions (e.g. s3 buckets)

        Arguments:
            service_name (str): The name of the service to check (e.g. ``'ec2'``)
            region_name (str): The name of the region to check (e.g. ``'eu-west-1'``)
        """
        service_map = self.service_maps.get_service_mapping(service_name=service_name)
        if not service_map.is_global_service:
            yield region_name
            return

        if service_map.global_service_region != region_name:
            return
        elif not service_map.has_regional_resources:
            yield region_name
        else:
            yield from self.enabled_regions


def _get_resource_attributes(
        boto3_resource: boto3.resources.base.ServiceResource, snake_case: bool = False) -> dict:
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
    unwanted_keys = ['ResponseMetadata']
    for key in unwanted_keys:
        if key in boto3_metadata:
            del boto3_metadata[key]
    return boto3_metadata
