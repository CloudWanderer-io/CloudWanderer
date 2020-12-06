import logging
from botocore import xform_name
import boto3

GLOBAL_SERVICE_REGIONAL_RESOURCE = [
    {
        'resource_name': 's3_bucket'
    }
]


class AwsUrn():

    def __init__(self, account_id, region, service, resource_type, resource_id):
        self.account_id = account_id
        self.region = region
        self.service = service
        self.resource_type = resource_type
        self.resource_id = resource_id

    @classmethod
    def from_string(cls, urn_string):
        parts = urn_string.split(':')
        return cls(
            account_id=parts[2],
            region=parts[3],
            service=parts[4],
            resource_type=parts[5],
            resource_id=parts[6]
        )

    def __eq__(self, other):
        return str(self) == str(other)

    def __repr__(self):
        return str(
            f"{self.__class__.__name__}("
            f"account_id='{self.account_id}', '"
            f"region='{self.region}', '"
            f"service='{self.service}', '"
            f"resource_type='{self.resource_type}', '"
            f"resource_id='{self.resource_id}')"
        )

    def __str__(self):
        return str(
            f"urn:aws:{self.account_id}:{self.region}:{self.service}:{self.resource_type}:{self.resource_id}"
        )


class CloudWanderer():

    def __init__(self, storage_connector, service_name):
        self.storage_connector = storage_connector
        self._account_id = None
        self._client_region = None
        self.resource = boto3.resource(service_name)

    def get_collections(self):
        return self.resource.meta.resource_model.collections

    def get_resource_model(self, resource_name):
        return self.resource.meta.resource_model[resource_name]

    def write_resources(self):
        for resource in self.get_resources():
            self.storage_connector.write(self._get_resource_urn(resource), resource)

    def _get_resource_urn(self, resource):
        id_member_name = resource.meta.resource_model.identifiers[0].member_name
        resource_id = getattr(resource, id_member_name)
        return AwsUrn(
            account_id=self.account_id,
            region=self.client_region,
            service=resource.meta.service_name,
            resource_type=xform_name(resource.meta.resource_model.name),
            resource_id=resource_id
        )

    def get_resources(self):
        for collection in self.get_collections():
            logging.info(f'--> Fetching {xform_name(collection.name)}')
            if collection.name in ['images', 'snapshots']:
                continue
            resources = getattr(
                self.resource, xform_name(collection.name)).all()
            for resource in resources:
                yield resource

    def read_resource_of_type(self, service, resource_type):
        return self.storage_connector.read_resource_of_type(service, resource_type)

    def read_resource(self, urn):
        """Read a specific resource by its urn."""
        try:
            return next(self.storage_connector.read_resource(urn))
        except StopIteration:
            return None

    def read_resource_from_account(self, account_id):
        """Return all resources from the provided AWS Account."""
        return self.storage_connector.read_resource_from_account(account_id)

    @property
    def account_id(self):
        if self._account_id is None:
            sts = boto3.client('sts')
            self._account_id = sts.get_caller_identity()['Account']
        return self._account_id

    @property
    def client_region(self):
        if self._client_region is None:
            self._client_region = boto3.session.Session().region_name
        return self._client_region


class ResourceDict(dict):
    """A dictionary representation of a resource that cleans out our metadata."""

    def __init__(self, urn, resource):
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
        return f"{self.__class__.__name__}(urn={repr(self.urn)}, resource={self.metadata})"

    def __str__(self):
        return repr(self)
