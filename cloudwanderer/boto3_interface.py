"""Code which abstracts away the majority of boto3 interrogation.

Provides simpler methods for :class:`~.cloud_wanderer.CloudWanderer` to call.
"""
from typing import List, Iterator
import logging
import boto3
import botocore
from botocore import xform_name
from boto3.resources.base import ServiceResource
from boto3.resources.model import Collection, ResourceModel
from .storage_connectors.base_connector import BaseStorageConnector
from .cloud_wanderer_resource import CloudWandererResource, SecondaryAttribute
from .custom_resource_definitions import CustomResourceDefinitions
from .service_mappings import ServiceMappingCollection, GlobalServiceResourceMappingNotFound
from .aws_urn import AwsUrn
logger = logging.getLogger(__name__)


class CloudWandererBoto3Interface:
    """Simplifies lookup of boto3 services and resources."""

    def __init__(self, boto3_session: boto3.session.Session = None) -> None:
        """Simplifies lookup of boto3 services and resources.

        Arguments:
            boto3_session (boto3.session.Session):
                A boto3 session, if not provided the default will be used.
        """
        self.boto3_session = boto3_session or boto3.Session()
        self.service_maps = ServiceMappingCollection(boto3_session=self.boto3_session)
        self.custom_resource_definitions = CustomResourceDefinitions(boto3_session=boto3_session)
        self._enabled_regions = None
        self._account_id = None

    def get_resources(
        self, regions: List[str] = None, service_names: List[str] = None, resource_types: List[str] = None,
        exclude_resources: List[str] = None, **kwargs
    ) -> Iterator[CloudWandererResource]:
        """Get resources matching the arguments.

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
            kwargs:
                All additional keyword arguments will be passed down to the Boto3 client calls.
        """
        regions = regions or self.enabled_regions
        for region_name in regions:
            yield from self._get_resources_in_region(
                service_names=service_names,
                resource_types=resource_types,
                exclude_resources=exclude_resources,
                region_name=region_name,
                **kwargs
            )

    def _get_resources_in_region(
            self, service_names: List[str], resource_types: List[str] = None, exclude_resources: List[str] = None,
            region_name: str = None, **kwargs) -> None:
        """Get resources in region matching the resource types.

        Any additional args will be passed into the cloud interface's ``get_`` methods.

        Arguments:
            service_names (str):
                The names of the services to write resources for (e.g. ``['ec2']``)
            resource_types (list):
                A list of resource types to include (e.g. ``['instance']``)
            exclude_resources (list):
                exclude_resources (list): A list of service:resources to exclude (e.g. ``['ec2:instance']``)
            region_name (str):
                The name of the region to get resources from (defaults to session default if not specified)
            **kwargs: Additional keyword arguments will be passed down to the cloud interface methods.
        """
        exclude_resources = exclude_resources or []
        boto3_services = self.get_all_resource_services()
        if service_names is not None:
            boto3_services = [
                self.get_resource_service_by_name(service_name, **kwargs)
                for service_name in service_names
            ]
        for boto3_service in boto3_services:
            yield from self._get_resources_of_service_in_region(
                service_name=boto3_service.meta.service_name,
                resource_types=resource_types,
                exclude_resources=exclude_resources,
                region_name=region_name,
                **kwargs
            )

    def _get_resources_of_service_in_region(
            self, service_name: str, exclude_resources: List[str] = None,
            resource_types: List[str] = None, region_name: str = None, **kwargs) -> None:
        """Write all AWS resources in this region in this service to storage.

        Cleans up any resources in the StorageConnector that no longer exist.

        Any additional args will be passed into the cloud interface's ``get_`` methods.

        Arguments:
            service_name (str):
                The name of the service to write resources for (e.g. ``'ec2'``)
            exclude_resources (list):
                A list of service:resources to exclude (e.g. ``['ec2:instance']``)
            resource_types (list):
                A list of resource types to include (e.g. ``['instance']``)
            region_name (str):
                The name of the region to get resources from
                (defaults to session default if not specified)
            **kwargs: Additional keyword arguments will be passed down to the cloud interface methods.
        """
        region_name = region_name or self.region_name

        logger.info("Writing all %s resources in %s", service_name, region_name)
        exclude_resources = exclude_resources or []
        resource_types = self._get_valid_resource_types(service_name=service_name, resource_types=resource_types)
        for resource_type in resource_types:
            if f'{service_name}:{resource_type}' in exclude_resources:
                logger.info('Skipping %s as per exclude_resources', f'{service_name}:{resource_type}')
                continue
            yield from self._get_resources_of_type_in_region(
                service_name=service_name,
                resource_type=resource_type,
                region_name=region_name,
                **kwargs
            )

    def _get_valid_resource_types(self, service_name: str, resource_types: List[str]) -> List[str]:
        service_resource_types = list(self.get_service_resource_types(service_name=service_name))
        if resource_types:
            return [
                resource_type
                for resource_type in resource_types
                if resource_type in service_resource_types
            ]

        return service_resource_types

    def _get_resources_of_type_in_region(
            self, service_name: str, resource_type: str = None,
            region_name: str = None, **kwargs) -> None:
        """Write all AWS resources in this region in this service to storage.

        Cleans up any resources in the StorageConnector that no longer exist.

        Any additional args will be passed into the cloud interface's ``get_`` methods.

        Arguments:
            service_name (str):
                The name of the service to write resources for (e.g. ``'ec2'``)
            resource_type (str):
                The name of the type of the resource to write (e.g. ``'instance'``)
            region_name (str):
                The name of the region to get resources from
                (defaults to session default if not specified)
            **kwargs: Additional keyword arguments will be passed down to the cloud interface methods.
        """
        region_name = region_name or self.cloud_interface.region_name
        logger.info('Fetching %s %s from %s', service_name, resource_type, region_name)
        yield from self._get_resources_of_type(
            service_name=service_name, resource_type=resource_type, region_name=region_name, **kwargs)

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

    def _get_resources_of_type(
            self, service_name: str, resource_type: str, region_name: str = None, **kwargs) -> Iterator[ResourceModel]:
        """Return all resources of resource_type from all definition sources.

        Arguments:
            service_name (str): The name of the service to get resource for (e.g. ``'ec2'``)
            resource_type (str): The type of resource to get resources of (e.g. ``'instance'``)
            region_name (str): The region to get resources of (e.g. ``'eu-west-1'``)
            **kwargs: Additional keyword arguments will be passed down to the Boto3 client.
        """
        service_map = self.service_maps.get_service_mapping(service_name=service_name)
        region_name = region_name or self.region_name
        if service_map.is_global_service and service_map.global_service_region != region_name:
            logger.info("Skipping %s as it does not have resources in %s", service_name, region_name)
            return
        boto3_service = self.get_resource_service_by_name(service_name, **kwargs)
        boto3_resource_collection = next(self.get_resource_collection_by_resource_type(boto3_service, resource_type))
        resources = self.get_resource_from_collection(
            boto3_service=boto3_service,
            boto3_resource_collection=boto3_resource_collection
        )

        for resource in resources:
            urn = self._get_resource_urn(resource, region_name)
            logger.debug("Found %s", urn)
            yield CloudWandererResource(
                urn=urn,
                resource_data=self._prepare_boto3_resource_data(resource),
                secondary_attributes=list(self.get_secondary_attributes(resource)),
            )
            for subresource in self.get_subresources(resource):
                yield CloudWandererResource(
                    urn=self._get_resource_urn(subresource, region_name),
                    resource_data=self._prepare_boto3_resource_data(subresource),
                    secondary_attributes=list(self.get_secondary_attributes(subresource)),
                )

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

    def get_secondary_attributes(self, boto3_resource: boto3.resources.base.ServiceResource) -> SecondaryAttribute:
        """Return all secondary attributes resources for this resource.

        Subresources and collections on custom service resources may be secondary attribute definitions if
        specified in metadata.

        Arguments:
            boto3_resource (boto3.resources.base.ServiceResource): The :class:`boto3.resources.base.ServiceResource`
                to get secondary attributes from
        """
        secondary_attributes = self.get_child_resources(
            boto3_resource=boto3_resource, resource_type='secondaryAttribute')
        for secondary_attribute in secondary_attributes:
            yield SecondaryAttribute(
                name=xform_name(secondary_attribute.meta.resource_model.name),
                **self._clean_boto3_metadata(secondary_attribute.meta.data))

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

    def _get_resource_urn(self, resource: ResourceModel, region_name: str) -> 'AwsUrn':
        id_members = [x.name for x in resource.meta.resource_model.identifiers]
        resource_ids = []
        for id_member in id_members:
            id_part = getattr(resource, id_member)
            if id_part.startswith('arn:'):
                id_part = ''.join(id_part.split(':')[5:])
            resource_ids.append(id_part)
        compound_resource_id = '/'.join(resource_ids)
        service_map = self.service_maps.get_service_mapping(resource.meta.service_name)
        return AwsUrn(
            account_id=self.account_id,
            region=service_map.get_resource_region(resource, region_name),
            service=resource.meta.service_name,
            resource_type=xform_name(resource.meta.resource_model.name),
            resource_id=compound_resource_id
        )

    def cleanup_resources(
            self, storage_connector: BaseStorageConnector, urns_to_keep: List[AwsUrn] = None,
            regions: List[str] = None, service_names: List[str] = None, resource_types: List[str] = None,
            exclude_resources: List[str] = None, **kwargs) -> None:
        """Delete records as appropriate from a storage connector based on the supplied arguments.

        All arguments are optional.

        Arguments:
            storage_connector (BaseStorageConnector):
                The storage connector to delete the records from.
            urns_to_keep (List[AwsUrn]):
                A list of AwsUrns which should not be removed from the storage_connector
            regions(list):
                The name of the region to get resources from (defaults to session default if not specified)
            service_names (str):
                The names of the services to write resources for (e.g. ``['ec2']``)
            resource_types (list):
                A list of resource types to include (e.g. ``['instance']``)
            exclude_resources (list):
                A list of service:resources to exclude (e.g. ``['ec2:instance']``)
            kwargs:
                All additional keyword arguments will be passed down to the Boto3 client calls.
        """
        regions = regions or self.enabled_regions
        boto3_services = self.get_all_resource_services()
        if service_names is not None:
            boto3_services = [
                self.get_resource_service_by_name(service_name, **kwargs)
                for service_name in service_names
            ]
        for region_name in regions:
            for boto3_service in boto3_services:
                resource_types = self._get_valid_resource_types(
                    service_name=boto3_service.meta.service_name, resource_types=resource_types)
                for resource_type in resource_types:
                    self._clean_resources_in_region(
                        storage_connector=storage_connector,
                        service_name=boto3_service.meta.service_name,
                        resource_type=resource_type,
                        region_name=region_name,
                        current_urns=urns_to_keep
                    )

    def _clean_resources_in_region(
            self, storage_connector: BaseStorageConnector, service_name: str, resource_type: str, region_name: str,
            current_urns: List[AwsUrn]) -> None:
        """Remove all resources of this type in this region which no longer exist.

        Arguments:
            storage_connector (BaseStorageConnector):
                The storage connector that resources will be deleted from.
            service_name (str):
                The name of the service to write resources for (e.g. ``'ec2'``)
            resource_type (str):
                The name of the type of the resource to write (e.g. ``'instance'``)
            region_name (str):
                The name of the region to get resources from
                (defaults to session default if not specified)
            current_urns (List[AwsUrn]):
                A list of URNs which are still current and should not be deleted.
        """
        regions_returned = self.resource_regions_returned_from_api_region(service_name, region_name)
        for region_name in regions_returned:
            logger.info('---> Deleting %s %s from %s', service_name, resource_type, region_name)
            storage_connector.delete_resource_of_type_in_account_region(
                service=service_name,
                resource_type=resource_type,
                account_id=self.account_id,
                region=region_name,
                urns_to_keep=current_urns
            )

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

    def _prepare_boto3_resource_data(self, boto3_resource: boto3.resources.base.ServiceResource) -> dict:
        result = {attribute: None for attribute in self._get_resource_attributes(boto3_resource).keys()}
        result.update(boto3_resource.meta.data or {})
        return self._clean_boto3_metadata(result)

    def _get_resource_attributes(
            self, boto3_resource: boto3.resources.base.ServiceResource, snake_case: bool = False) -> dict:
        if snake_case:
            return boto3_resource.meta.resource_model.get_attributes(self.get_shape(boto3_resource))
        return self.get_shape(boto3_resource).members

    def get_shape(self, boto3_resource: boto3.resources.base.ServiceResource) -> botocore.model.Shape:
        """Return the Botocore shape of a boto3 Resource.

        Parameters:
            boto3_resource (boto3.resources.base.ServiceResource):
                The resource to get the shape of.
        """
        service_model = boto3_resource.meta.client.meta.service_model
        shape = service_model.shape_for(boto3_resource.meta.resource_model.shape)
        return shape

    def _clean_boto3_metadata(self, boto3_metadata: dict) -> dict:
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
