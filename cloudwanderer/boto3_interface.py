"""Code which abstracts away the majority of boto3 interrogation.

Provides simpler methods for CloudWanderer to call.
"""
import logging
import boto3
from botocore.exceptions import ClientError
from boto3.exceptions import ResourceNotExistsError
from .custom_resource_definitions import CustomResourceDefinitions


class CloudWandererBoto3Interface():
    """Class of methods which expect boto3 resources and services rather than resource names and service names."""

    def __init__(self, boto3_session=None):
        """Class of methods which expect boto3 resources and services rather than resource names and service names."""
        self.boto3_session = boto3_session or boto3.Session()
        self.custom_resource_definitions = CustomResourceDefinitions().load_custom_resource_definitions()
        self.custom_resource_attribute_definitions = CustomResourceDefinitions(
            definition_path='attribute_definitions'
        ).load_custom_resource_definitions()

    def _get_available_services(self):
        return self.boto3_session.get_available_resources()

    def get_all_resource_services(self):
        """Return all the boto3 service Resource objects that are available, both built-in and custom."""
        for service_name in self._get_available_services():
            yield self.get_boto3_resource_service(service_name)
        for service_name in self.custom_resource_definitions:
            yield self.get_custom_resource_service(service_name)

    def get_boto3_resource_service(self, service_name):
        """Return the boto3 service Resource object matching this service_name."""
        try:
            return self.boto3_session.resource(service_name)
        except ResourceNotExistsError:
            return None

    def get_custom_resource_service(self, service_name):
        """Get the custom resource definition matching this service name."""
        return self.custom_resource_definitions.get(service_name)

    def get_resource_service_by_name(self, service_name):
        """Return all services matching name, boto3 or custom."""
        boto3_resource_service = self.get_boto3_resource_service(service_name)
        if boto3_resource_service:
            yield boto3_resource_service
        custom_resource_service = self.get_custom_resource_service(service_name)
        if custom_resource_service:
            yield custom_resource_service

    def get_resource_collections(self, boto3_service):
        """Return all resource types in this service."""
        return boto3_service.meta.resource_model.collections

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

    def get_resource_attribute_from_collection(
            self, boto3_resource_attribute_service, boto3_resource_attribute_collection):
        """Return a boto3.resource pertaining to a resource attribute defined by CloudWanderer.

        These custom resource attribute definitions allow us to fetch resource attributes that are not returned by the
        resource's default describe calls.

        Arguments:
            boto3_resource_attribute_service: The boto3.resource service from
                self.get_resource_attributes_service_by_name
            boto3_resource_attribute_collection: The boto3 collection of attributes we want to retrieve.
        """
        resource_attributes = self.get_resource_from_collection(
            boto3_service=boto3_resource_attribute_service,
            boto3_resource_collection=boto3_resource_attribute_collection
        )
        for resource_attribute in resource_attributes:
            # A resource_attribute will initially be populated with its parent resource's data,
            # the attribute data is loaded on .load()
            resource_attribute.load()
            # I'm fairly sure there must be a way to clean out the response metadata with botocore shapes but
            # I haven't figured out how yet.
            if 'ResponseMetadata' in resource_attribute.meta.data:
                del resource_attribute.meta.data['ResponseMetadata']
            yield resource_attribute

    def get_resource_attributes_service_by_name(self, service_name):
        """Return the boto3.resource service containing a collection of resource attributes provided by CloudWanderer.

        These custom resource attribute definitions allow us to fetch resource attributes that are not returned by the
        resource's default describe calls.

        Arguments:
            service_name (str): The name of the service (e.g.``ec2``) to get.
        """
        yield self.custom_resource_attribute_definitions.get(service_name)
