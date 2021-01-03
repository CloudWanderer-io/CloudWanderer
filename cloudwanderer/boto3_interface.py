"""Code which abstracts away the majority of boto3 interrogation.

Provides simpler methods for :class:`~.cloud_wanderer.CloudWanderer` to call.
"""
from typing import List, Iterator
import logging
import boto3
from botocore import xform_name
from botocore.exceptions import ClientError, EndpointConnectionError
from boto3.resources.base import ServiceResource
from boto3.resources.model import Collection, ResourceModel
from .custom_resource_definitions import CustomResourceDefinitions
from .service_mappings import ServiceMappingCollection, GlobalServiceResourceMappingNotFound
logger = logging.getLogger(__name__)


class CloudWandererBoto3Interface:
    """Simplifies lookup of boto3 services and resources."""

    def __init__(self, boto3_session: boto3.session.Session = None) -> None:
        """Simplifies lookup of boto3 services and resources."""
        self.boto3_session = boto3_session or boto3.Session()
        self.service_maps = ServiceMappingCollection(boto3_session=self.boto3_session)
        self.custom_resource_definitions = CustomResourceDefinitions(boto3_session=boto3_session)

    def get_all_resource_services(self, client_args: dict = None) -> Iterator[ServiceResource]:
        """Return all boto3 service Resource objects.

        Arguments:
            client_args (dict): Arguments to pass into the boto3 client.
                See: :meth:`boto3.session.Session.client`
        """
        for service_name in self.custom_resource_definitions.definitions:
            yield self.get_resource_service_by_name(service_name, client_args)

    def get_resource_service_by_name(
            self, service_name: str, client_args: dict = None) -> ResourceModel:
        """Get the resource definition matching this service name.

        Arguments:
            service_name (str): The name of the service (e.g. ``'ec2'``) to get.
            client_args (dict): Arguments to pass into the boto3 client.
                See: :meth:`boto3.session.Session.client`
        """
        client_args = client_args or {}
        return self.custom_resource_definitions.resource(service_name, **client_args)

    def get_resource_collections(self, boto3_service: ServiceResource) -> List[Collection]:
        """Return all resource types in this service."""
        return boto3_service.meta.resource_model.collections

    def get_resource_collection_by_resource_type(
            self, boto3_service: ServiceResource,
            resource_type: str) -> Iterator[Collection]:
        """Return the resource collection that matches the resource_type (e.g. instance).

        This is as opposed to the collection name (e.g. instances)
        """
        for boto3_resource_collection in self.get_resource_collections(boto3_service):
            if xform_name(boto3_resource_collection.resource.model.shape) != resource_type:
                continue
            yield boto3_resource_collection

    def get_resource_from_collection(
            self, boto3_service: ServiceResource,
            boto3_resource_collection: Collection) -> Iterator[ResourceModel]:
        """Return all resources of this resource type (collection) from this service."""
        if not hasattr(boto3_service, boto3_resource_collection.name):
            logger.warning('%s does not have %s', boto3_service.__class__.__name__, boto3_resource_collection.name)
            return
        try:
            yield from getattr(boto3_service, boto3_resource_collection.name).all()
        except ClientError as ex:
            if ex.response['Error']['Code'] == 'InvalidAction':
                logger.warning(ex.response['Error']['Message'])
                return
            raise ex

    def get_resources_of_type(
            self, service_name: str, resource_type: str, client_args: dict) -> Iterator[ResourceModel]:
        """Return all resources of resource_type from all definition sources.

        Arguments:
            service_name: The name of the service to get resource for (e.g. ``'ec2'``)
            resource_type: The type of resource to get resources of (e.g. ``'instance'``
            client_args (dict): Arguments to pass into the boto3 client.
                See: :meth:`boto3.session.Session.client`
        """
        boto3_service = self.get_resource_service_by_name(service_name, client_args=client_args)
        yield from self.get_resources_of_type_from_service(
            boto3_service=boto3_service,
            resource_type=resource_type
        )

    def get_resources_of_type_from_service(self, boto3_service: ServiceResource, resource_type: str) -> None:
        """Return all resources of resource_type from boto3_service.

        Arguments:
            boto3_service (boto3.resources.base.ServiceResource): The :class:`boto3.resources.base.ServiceResource`
                to retrieve resources from.
            resource_type (str): The type of resource to get resources of (e.g. ``'instance'``
        """
        boto3_resource_collection = next(self.get_resource_collection_by_resource_type(boto3_service, resource_type))

        try:
            yield from self.get_resource_from_collection(
                boto3_service=boto3_service,
                boto3_resource_collection=boto3_resource_collection
            )
        except EndpointConnectionError as ex:
            logger.warning(ex)

    def get_service_resource_types(self, service_name: str) -> Iterator[str]:
        """Return all possible resource names for a given service.

        Returns resources for both native boto3 resources and custom cloudwanderer resources.

        Arguments:
            service_name: The name of the service to get resource types for (e.g. ``'ec2'``)
        """
        for collection in self.get_service_resource_collections(service_name):
            yield xform_name(collection.resource.model.shape)

    def get_service_resource_types_from_collections(self, collections: List[Collection]) -> Iterator[str]:
        """Return all possible resource names for a given service.

        Returns resources for both native boto3 resources and custom cloudwanderer resources.

        Arguments:
            collections (List[Collection]): The list of collections from which to get resource names.
        """
        for collection in collections:
            yield xform_name(collection.resource.model.shape)

    def get_service_resource_collections(self, service_name: str) -> Iterator[Collection]:
        """Return all the resource collections for a given service_name.

        This is crucial to return collections for both native boto3 resources and custom cloudwanderer resources.

        Arguments:
            service_name: The name of the service to get resource types for (e.g. ``'ec2'``)
        """
        boto3_service = self.get_resource_service_by_name(service_name)
        if boto3_service is not None:
            yield from self.get_resource_collections(boto3_service)

    def get_subresources(self, boto3_resource: ServiceResource) -> ServiceResource:
        """Return all subresources for this resource.

        Subresources and collections on custom service resources may be subresources we want to collect if
        they are specified in our custom resource definitions.

        Arguments:
            boto3_resource (boto3.resources.base.ServiceResource): The :class:`boto3.resources.base.ServiceResource`
                to get secondary attributes from
        """
        yield from self.get_child_resources(boto3_resource=boto3_resource, resource_type='resource')

    def get_secondary_attributes(self, boto3_resource: ServiceResource) -> ServiceResource:
        """Return all secondary attributes resources for this resource.

        Subresources and collections on custom service resources may be secondary attribute definitions if
        specified in metadata.

        Arguments:
            boto3_resource (boto3.resources.base.ServiceResource): The :class:`boto3.resources.base.ServiceResource`
                to get secondary attributes from
        """
        yield from self.get_child_resources(boto3_resource=boto3_resource, resource_type='secondaryAttribute')

    def get_child_resources(self, boto3_resource: ServiceResource, resource_type: str) -> ServiceResource:
        """Return all child resources of resource_type for this resource.

        Arguments:
            boto3_resource (boto3.resources.base.ServiceResource): The :class:`boto3.resources.base.ServiceResource`
                to get secondary attributes from
            resource_type (str): The resource types to return (either 'secondaryAttribute' or 'resource')
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
            yield from self.get_resource_from_collection(
                boto3_service=boto3_resource,
                boto3_resource_collection=child_resource_collection
            )

    def get_child_resource_definitions(
            self, service_name: str, boto3_resource_model: ResourceModel, resource_type: str) -> ServiceResource:
        """Return all secondary attributes models for this resource.

        Subresources and collections on custom service resources may be secondary attribute definitions if
        specified in metadata.

        Arguments:
            service_name (str): The name of the service this model resides in (e.g. ``'ec2'``)
            boto3_resource_model (boto3.resources.model.ResourceModel): The
                :class:`boto3.resources.model.ResourceModel` to get secondary attributes models from
            resource_type (str): The resource types to return (either 'secondaryAttribute' or 'resource')
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
