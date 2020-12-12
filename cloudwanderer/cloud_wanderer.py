"""Main cloudwanderer module."""
import logging
from botocore import xform_name
from botocore.exceptions import ClientError
from boto3.exceptions import ResourceNotExistsError
import boto3
from .custom_resource_definitions import CustomResourceDefinitions
from .aws_urn import AwsUrn
GLOBAL_SERVICE_REGIONAL_RESOURCE = [
    {
        'resource_name': 's3_bucket'
    }
]


class CloudWandererBoto3Interface():
    """Class of methods which expect boto3 resources and services rather than resource names and service names."""

    def __init__(self):
        """Class of methods which expect boto3 resources and services rather than resource names and service names."""
        self.custom_resource_definitions = CustomResourceDefinitions().load_custom_resource_definitions()
        self.custom_resource_attribute_definitions = CustomResourceDefinitions(
            definition_path='attribute_definitions'
        ).load_custom_resource_definitions()

    def _get_available_services(self):
        return boto3.Session().get_available_resources()

    def get_all_resource_services(self):
        """Return all the boto3 service Resource objects that are available, both built-in and custom."""
        for service_name in self._get_available_services():
            yield self.get_boto3_resource_service(service_name)
        for service_name in self.custom_resource_definitions:
            yield self.get_custom_resource_service(service_name)

    def get_boto3_resource_service(self, service_name):
        """Return the boto3 service Resource object matching this service_name."""
        try:
            return boto3.resource(service_name)
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
        logging.info(f'--> Fetching {boto3_service.meta.service_name} {boto3_resource_collection.name}')
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


class CloudWanderer():
    """CloudWanderer.

    Args:
        storage_connector: A CloudWanderer storage connector object.
    """

    def __init__(self, storage_connector):
        """Initialise CloudWanderer."""
        self.storage_connector = storage_connector
        self.boto3_interface = CloudWandererBoto3Interface()
        self._account_id = None
        self._client_region = None

    def write_all_resources(self, exclude_resources=None):
        """Write all AWS resources in this account from all services to storage."""
        exclude_resources = exclude_resources or []
        for boto3_service in self.boto3_interface.get_all_resource_services():
            for boto3_resource_collection in self.boto3_interface.get_resource_collections(boto3_service):
                if boto3_resource_collection.name in exclude_resources:
                    logging.info('Skipping %s as per exclude_resources', boto3_resource_collection.name)
                    continue
                resources = self.boto3_interface.get_resource_from_collection(
                    boto3_service,
                    boto3_resource_collection
                )
                for boto3_resource in resources:
                    self.storage_connector.write_resource(self._get_resource_urn(boto3_resource), boto3_resource)

    def write_resources(self, service_name, exclude_resources=None):
        """Write all AWS resources in this account in this service to storage.

        Arguments:
            service_name (str): The name of the service to write resources for (e.g. ``'ec2'``)
            exclude_resources (list): A list of resources to exclude (e.g. `['instances']`)
        """
        logging.info("Writing all %s resources in %s", service_name, self.client_region)
        exclude_resources = exclude_resources or []
        for boto3_service in self.boto3_interface.get_resource_service_by_name(service_name):
            for boto3_resource_collection in self.boto3_interface.get_resource_collections(boto3_service):
                if boto3_resource_collection.name in exclude_resources:
                    logging.info('Skipping %s as per exclude_resources', boto3_resource_collection.name)
                    continue
                resources = self.boto3_interface.get_resource_from_collection(boto3_service, boto3_resource_collection)
                for boto3_resource in resources:
                    self.storage_connector.write_resource(self._get_resource_urn(boto3_resource), boto3_resource)

    def write_resource_attributes(self, service_name):
        """Write all AWS resource attributes in this account in this service to storage.

        These custom resource attribute definitions allow us to fetch resource attributes that are not returned by the
        resource's default describe calls.

        Arguments:
            service_name (str): The name of the service to write the attributes of (e.g. ``ec2``)
        """
        services = self.boto3_interface.get_resource_attributes_service_by_name(service_name)
        for boto3_resource_attribute_service in services:
            collections = self.boto3_interface.get_resource_collections(boto3_resource_attribute_service)
            for boto3_resource_attribute_collection in collections:
                resource_attributes = self.boto3_interface.get_resource_attribute_from_collection(
                    boto3_resource_attribute_service,
                    boto3_resource_attribute_collection
                )
                for boto3_resource_attribute in resource_attributes:
                    self.storage_connector.write_resource_attribute(
                        urn=self._get_resource_urn(boto3_resource_attribute),
                        resource_attribute=boto3_resource_attribute,
                        attribute_type=boto3_resource_attribute_collection.name
                    )

    def read_resource_of_type(self, service, resource_type):
        """Return all resources of type.

        Args:
            service (str): Service name (e.g. ec2)
            resource_type (str): Resource Type (e.g. instance)
        """
        return self.storage_connector.read_resource_of_type(service, resource_type)

    def read_resource(self, urn):
        """Return a specific resource by its urn from storage."""
        try:
            return next(self.storage_connector.read_resource(urn))
        except StopIteration:
            return None

    def read_all_resources_in_account(self, account_id):
        """Return all resources in the provided AWS Account from storage."""
        return self.storage_connector.read_all_resources_in_account(account_id)

    def read_resource_of_type_in_account(self, service, resource_type, account_id):
        """Return all resources of this type in the provided AWS Account from storage."""
        return self.storage_connector.read_resource_of_type_in_account(service, resource_type, account_id)

    @property
    def account_id(self):
        """Return the AWS Account ID our boto3 client is authenticated against."""
        if self._account_id is None:
            sts = boto3.client('sts')
            self._account_id = sts.get_caller_identity()['Account']
        return self._account_id

    @property
    def client_region(self):
        """Return the region our boto3 client is authenticated against."""
        if self._client_region is None:
            self._client_region = boto3.session.Session().region_name
        return self._client_region

    def _get_resource_urn(self, resource):
        id_member_name = resource.meta.resource_model.identifiers[0].name
        resource_id = getattr(resource, id_member_name)
        if resource_id.startswith('arn:'):
            resource_id = ''.join(resource_id.split(':')[5:])
        return AwsUrn(
            account_id=self.account_id,
            region=self.client_region,
            service=resource.meta.service_name,
            resource_type=xform_name(resource.meta.resource_model.shape),
            resource_id=resource_id
        )


class ResourceDict(dict):
    """A dictionary representation of a resource that prevents any storage metadata polluting the resource dictionary.

    Use ``dict(my_resource_dict)`` to convert this object into a dictionary that
    contains *only* the resource's metadata.

    Attributes:
        urn (cloudwanderer.AwsUrn): The AWS URN of the resource.
        metadata (dict): The original storage representation of the resource as it was passed in.
    """

    def __init__(self, urn, resource):
        """Initialise the resource dict."""
        self.urn = urn
        self.metadata = resource
        super().__init__(**self._clean_resource)

    @property
    def _clean_resource(self):
        return {
            key: value
            for key, value in self.metadata.items()
            if not key.startswith('_')
        }

    def __repr__(self):
        """Return a code representation of this resource."""
        return f"{self.__class__.__name__}(urn={repr(self.urn)}, resource={self.metadata})"

    def __str__(self):
        """Return the string representation of this Resource."""
        return repr(self)
