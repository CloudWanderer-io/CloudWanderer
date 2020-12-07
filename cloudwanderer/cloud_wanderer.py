"""Main cloudwanderer module."""
import logging
from botocore import xform_name
from botocore.exceptions import ClientError
from boto3.exceptions import ResourceNotExistsError
import boto3
from .custom_resource_definitions import CustomResourceDefinitions
GLOBAL_SERVICE_REGIONAL_RESOURCE = [
    {
        'resource_name': 's3_bucket'
    }
]


class AwsUrn():
    """A dataclass for building and querying AWS URNs.

    Args:
        account_id (str): AWS Account ID (e.g. ``111111111111``).
        region (str): AWS region (e.g. ``eu-west-1``).
        service (str): AWS Service (e.g. ``ec2``).
        resource_type (str): AWS Resource Type (e.g. ``instance``)
        resource_id (str): AWS Resource Id (e.g. ``i-11111111``)
    """

    def __init__(self, account_id, region, service, resource_type, resource_id):
        """Initialise an AWS Urn."""
        self.account_id = account_id
        self.region = region
        self.service = service
        self.resource_type = resource_type
        self.resource_id = resource_id

    @classmethod
    def from_string(cls, urn_string):
        """Create an AwsUrn Object from an AwsUrn string."""
        parts = urn_string.split(':')
        return cls(
            account_id=parts[2],
            region=parts[3],
            service=parts[4],
            resource_type=parts[5],
            resource_id=parts[6]
        )

    def __eq__(self, other):
        """Allow comparison of one AwsUrn to another."""
        return str(self) == str(other)

    def __repr__(self):
        """Return a class representation of the AwsUrn."""
        return str(
            f"{self.__class__.__name__}("
            f"account_id='{self.account_id}', '"
            f"region='{self.region}', '"
            f"service='{self.service}', '"
            f"resource_type='{self.resource_type}', '"
            f"resource_id='{self.resource_id}')"
        )

    def __str__(self):
        """Return a string representation of the AwsUrn."""
        return str(
            f"urn:aws:{self.account_id}:{self.region}:{self.service}:{self.resource_type}:{self.resource_id}"
        )


class CloudWanderer():
    """CloudWanderer.

    Args:
        storage_connector: A CloudWanderer storage connector object.
    """

    def __init__(self, storage_connector):
        """Initialise CloudWanderer."""
        self.storage_connector = storage_connector
        self._account_id = None
        self._client_region = None
        self.custom_resource_definitions = CustomResourceDefinitions().load_custom_resource_definitions()

    def get_resource_collections(self, boto3_resource):
        """Return all resource types in this service."""
        return boto3_resource.meta.resource_model.collections

    def write_all_resources(self):
        """Write all AWS resources in this account from all services to storage."""
        for service_name in self._get_available_services():
            self.write_resources(service_name)
        for service_name in self.custom_resource_definitions:
            self.write_resources(service_name)

    def write_resources(self, service_name):
        """Write all AWS resources in this account in this service to storage."""
        try:
            boto3_resource = boto3.resource(service_name)
        except ResourceNotExistsError:
            boto3_resource = self.custom_resource_definitions[service_name]
        resources = self.get_resources(boto3_resource)
        for resource in resources:
            self.storage_connector.write(self._get_resource_urn(resource), resource)

    def _get_resource_urn(self, resource):
        id_member_name = resource.meta.resource_model.identifiers[0].name
        resource_id = getattr(resource, id_member_name)
        if resource_id.startswith('arn:'):
            resource_id = ''.join(resource_id.split(':')[5:])
        return AwsUrn(
            account_id=self.account_id,
            region=self.client_region,
            service=resource.meta.service_name,
            resource_type=xform_name(resource.meta.resource_model.name),
            resource_id=resource_id
        )

    def _get_available_services(self):
        return boto3.Session().get_available_resources()

    def get_resources(self, boto3_resource):
        """Return all resources for this service from the AWS API."""
        for collection in self.get_resource_collections(boto3_resource):
            logging.info(f'--> Fetching {boto3_resource.meta.service_name} {collection.name}')
            if collection.name in ['images', 'snapshots']:
                continue

            try:
                for resource in getattr(boto3_resource, collection.name).all():
                    yield resource
            except ClientError as ex:
                if ex.response['Error']['Code'] == 'InvalidAction':
                    logging.warning(ex.response['Error']['Message'])
                    continue
                raise ex

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
        """The AWS Account ID our boto3 client is authenticated against."""
        if self._account_id is None:
            sts = boto3.client('sts')
            self._account_id = sts.get_caller_identity()['Account']
        return self._account_id

    @property
    def client_region(self):
        """The region our boto3 client is authenticated against."""
        if self._client_region is None:
            self._client_region = boto3.session.Session().region_name
        return self._client_region


class ResourceDict(dict):
    """A dictionary representation of a resource that prevents any storage metadata polluting the resource dictionary.

    Use ``dict(my_resource_dict)`` to convert this object into a dictionary that contains *only* the resource's metadata.

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
