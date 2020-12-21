"""Code which abstracts away the majority of boto3 interrogation.

Provides simpler methods for CloudWanderer to call.
"""
import logging
import boto3
from botocore import xform_name
from botocore.exceptions import ClientError
from boto3.exceptions import ResourceNotExistsError
from .custom_resource_definitions import CustomResourceDefinitions


class CloudWandererBoto3Interface:
    """Simplifies lookup of boto3 services and resources."""

    def __init__(self, boto3_session=None):
        """Simplifies lookup of boto3 services and resources."""
        self.boto3_session = boto3_session or boto3.Session()
        self.custom_resource_definitions = CustomResourceDefinitions(boto3_session=boto3_session)

    def _get_available_services(self):
        return self.boto3_session.get_available_resources()

    def get_all_resource_services(self, service_args=None):
        """Return all the boto3 service Resource objects that are available, both built-in and custom."""
        for service_name in self._get_available_services():
            yield self.get_boto3_resource_service(service_name, service_args)
        for service_name in self.custom_resource_definitions.definitions:
            yield self.get_custom_resource_service(service_name, service_args)

    def get_boto3_resource_service(self, service_name, service_args=None):
        """Return the boto3 service Resource object matching this service_name."""
        service_args = service_args or {}
        try:
            return self.boto3_session.resource(service_name, **service_args)
        except ResourceNotExistsError:
            return None

    def get_resource_service_by_name(self, service_name, region_name=None, service_args=None):
        """Return all services matching name, boto3 or custom."""
        service_args = service_args or {'region_name': region_name}
        boto3_resource_service = self.get_boto3_resource_service(service_name, service_args)
        if boto3_resource_service:
            yield boto3_resource_service
        custom_resource_service = self.custom_resource_definitions.resource(service_name, service_args)
        if custom_resource_service:
            yield custom_resource_service

    def get_resource_collections(self, boto3_service):
        """Return all resource types in this service."""
        return boto3_service.meta.resource_model.collections

    def get_resource_collection_by_resource_type(self, boto3_service, resource_type):
        """Return the resource collection that matches the resource_type (e.g. instance).

        This is as opposed to the collection name (e.g. instances)
        """
        for boto3_resource_collection in self.get_resource_collections(boto3_service):
            if xform_name(boto3_resource_collection.resource.model.shape) != resource_type:
                continue
            yield boto3_resource_collection

    def get_resource_from_collection(self, boto3_service, boto3_resource_collection):
        """Return all resources of this resource type (collection) from this service."""
        try:
            for resource in getattr(boto3_service, boto3_resource_collection.name).all():
                yield resource
        except ClientError as ex:
            if ex.response['Error']['Code'] == 'InvalidAction':
                logging.warning(ex.response['Error']['Message'])
                return
            raise ex

    def get_resources_of_type(self, service_name, resource_type, service_args):
        """Return all resources of resource_type."""
        for boto3_service in self.get_resource_service_by_name(service_name, service_args=service_args):
            boto3_resource_collection = next(
                self.get_resource_collection_by_resource_type(boto3_service, resource_type),
                None)
            logging.warning(boto3_resource_collection.__dict__)
            if boto3_resource_collection is not None:
                yield from self.get_resource_from_collection(
                    boto3_service=boto3_service,
                    boto3_resource_collection=boto3_resource_collection
                )

    def get_service_resource_collection_names(self, service_name):
        """Return all possible resource collection names for a given service.

        Returns collection names for both native boto3 resources and custom cloudwanderer resources.
        """
        for collection in self.get_service_resource_collections(service_name):
            yield collection.name

    def get_service_resource_names(self, service_name):
        """Return all possible resource names for a given service.

        Returns resources for both native boto3 resources and custom cloudwanderer resources.
        """
        for collection in self.get_service_resource_collections(service_name):
            yield xform_name(collection.resource.model.shape)

    def get_service_resource_collections(self, service_name):
        """Return all the resource collections for a given service_name.

        This is crucial to return collections for both native boto3 resources and custom cloudwanderer resources.
        """
        for boto3_service in self.get_resource_service_by_name(service_name):
            if boto3_service is not None:
                yield from self.get_resource_collections(boto3_service)


class CustomAttributesInterface(CloudWandererBoto3Interface):
    """Simplifies lookup of CloudWanderer custom attributes."""

    def __init__(self, boto3_session):
        """Simplifies lookup of CloudWanderer custom attributes."""
        super().__init__(boto3_session=boto3_session)
        self.custom_resource_attribute_definitions = CustomResourceDefinitions(
            boto3_session=boto3_session,
            definition_path='attribute_definitions'
        )

    def get_resource_from_collection(
            self, boto3_service, boto3_resource_collection):
        """Return a boto3.resource pertaining to a resource attribute defined by CloudWanderer.

        These custom resource attribute definitions allow us to fetch resource attributes that are not returned by the
        resource's default describe calls.

        Arguments:
            boto3_service: The boto3.resource service from
                self.get_resource_attributes_service_by_name
            boto3_resource_collection: The boto3 collection of attributes we want to retrieve.
        """
        logging.warning('getting resources from collection...')
        resource_attributes = super().get_resource_from_collection(
            boto3_service=boto3_service,
            boto3_resource_collection=boto3_resource_collection
        )
        for resource_attribute in resource_attributes:
            # A resource_attribute will initially be populated with its parent resource's data,
            # the attribute data is loaded on .load()
            resource_attribute.load()
            logging.warning(resource_attribute)
            # I'm fairly sure there must be a way to clean out the response metadata with botocore shapes but
            # I haven't figured out how yet.
            if 'ResponseMetadata' in resource_attribute.meta.data:
                del resource_attribute.meta.data['ResponseMetadata']
            yield resource_attribute

    def get_resource_service_by_name(self, service_name, service_args=None):
        """Overrides method from CloudWandererBoto3Interface so we can reuse its other methods which depend upon this one."""
        yield from self.get_resource_attributes_service_by_name(service_name, service_args)

    def get_resource_attributes_service_by_name(self, service_name, service_args=None):
        """Return the boto3.resource service containing a collection of resource attributes provided by CloudWanderer.

        These custom resource attribute definitions allow us to fetch resource attributes that are not returned by the
        resource's default describe calls.

        Arguments:
            service_name (str): The name of the service (e.g.``ec2``) to get.
        """
        yield self.custom_resource_attribute_definitions.resource(
            service_name=service_name, service_args=service_args)
