import logging
import json
from datetime import datetime
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

    def __str__(self):
        return str(
            f"urn:aws:{self.account_id}:{self.region}:{self.service}:{self.resource_type}:{self.resource_id}"
        )


class DynamoWriter():

    def __init__(self, table_name='cloud_wanderer', endpoint_url=None):
        self.endpoint_url = endpoint_url
        self.table_name = table_name
        self.dynamodb = boto3.resource('dynamodb', endpoint_url=endpoint_url)
        self.dynamodb_table = self.dynamodb.Table(table_name)

    def init(self):
        try:
            self.dynamodb.create_table(
                AttributeDefinitions=[
                    {
                        'AttributeName': 'urn',
                        'AttributeType': 'S'
                    },
                ],
                TableName=self.table_name,
                BillingMode='PAY_PER_REQUEST',
                KeySchema=[
                    {
                        'AttributeName': 'urn',
                        'KeyType': 'HASH'
                    },
                ],
            )
        except self.dynamodb_table.meta.client.exceptions.ResourceInUseException:
            logging.warning(
                'Table %s already exists, skipping creation.',
                self.table_name)

    def write(self, urn, resource):
        logging.debug(f"Writing: {urn} to {self.table_name}")
        item = {**{'urn': str(urn)}, **
                self._standardise_data_types(resource.meta.data)}
        self.dynamodb_table.put_item(
            Item=item
        )

    def _standardise_data_types(self, resource):
        result = resource.copy()
        for k, v in resource.items():
            if isinstance(v, datetime):
                result[k] = v.isoformat()
        return result

    def dump(self):
        return self.dynamodb_table.scan()['Items']


class Wanderer():

    def __init__(self, writer, service_name):
        self.writer = writer
        self._account_id = None
        self._client_region = None
        self.resource = boto3.resource(service_name)

    def get_collections(self):
        return self.resource.meta.resource_model._definition['hasMany'].keys()

    def get_resource_model(self, resource_name):
        return self.resource.meta.resource_model[resource_name]

    def get_collection_resource_type(self, collection_name):
        return self.resource.meta.resource_model._definition['hasMany'][collection_name]['resource']['type']

    def write_resources(self):
        resources = self.get_resources()
        for resource in resources:
            id_member_name = resource.meta.resource_model.identifiers[0].member_name
            resource_id = getattr(resource, id_member_name)
            urn = AwsUrn(
                account_id=self.account_id,
                region=self.client_region,
                service=resource.meta.service_name,
                resource_type=xform_name(resource.meta.resource_model.name),
                resource_id=resource_id)
            self.writer.write(urn, resource)

    def get_resources(self):
        for collection_name in self.get_collections():
            if collection_name == 'Images':
                continue
            logging.info(f'--> Fetching {collection_name}')
            resources = getattr(
                self.resource, xform_name(collection_name)).all()
            for resource in resources:
                yield resource

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
