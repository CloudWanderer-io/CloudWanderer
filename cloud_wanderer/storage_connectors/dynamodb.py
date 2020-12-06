import logging
import os
import pathlib
import boto3
import json
from datetime import datetime
from random import randrange
from .base_connector import BaseConnector
from boto3.dynamodb.conditions import Key
from ..cloud_wanderer import ResourceDict, AwsUrn


def gen_resource_type_index(service, resource_type):
    return f"{service}#{resource_type}"


def gen_shard(key, shard_id=None):
    shard_id = shard_id if shard_id is not None else randrange(10)
    return f"{key}#shard{shard_id}"


def primary_key_from_urn(urn):
    return f"resource#{urn}"


def urn_from_primary_key(pk):
    return AwsUrn.from_string(pk.split('#')[1])


def dynamodb_items_to_resources(items):
    for item in items:
        yield ResourceDict(
            urn=urn_from_primary_key(item['_id']),
            resource=item
        )


class DynamoDbConnector(BaseConnector):

    def __init__(self, table_name='cloud_wanderer', endpoint_url=None):
        self.endpoint_url = endpoint_url
        self.table_name = table_name
        self.dynamodb = boto3.resource('dynamodb', endpoint_url=endpoint_url)
        self.dynamodb_table = self.dynamodb.Table(table_name)

    def init(self):
        table_creator = DynamoDbTableCreator(
            boto3_dynamodb_resource=self.dynamodb,
            table_name=self.table_name
        )
        table_creator.create_table()

    def write(self, urn, resource):
        logging.debug(f"Writing: {urn} to {self.table_name}")
        self.dynamodb_table.put_item(
            Item={
                **{
                    '_id': primary_key_from_urn(urn),
                    '_resourcetypeindex': f"{gen_shard(gen_resource_type_index(urn.service, urn.resource_type))}"
                },
                **self._standardise_data_types(resource.meta.data)
            }
        )

    def _standardise_data_types(self, resource):
        result = resource.copy()
        for k, v in resource.items():
            if isinstance(v, datetime):
                result[k] = v.isoformat()
        return result

    def read_resource(self, urn):
        result = self.dynamodb_table.query(
            KeyConditionExpression=Key('_id').eq(primary_key_from_urn(urn))
        )
        yield from dynamodb_items_to_resources(result['Items'])

    def read_resource_of_type(self, service, resource_type):
        for shard_id in range(0, 9):
            key = gen_shard(gen_resource_type_index(service, resource_type), shard_id)
            logging.debug("Fetching shard %s", key)
            result = self.dynamodb_table.query(
                IndexName='resourcetype',
                Select='ALL_PROJECTED_ATTRIBUTES',
                KeyConditionExpression=Key('_resourcetypeindex').eq(key)
            )
            yield from dynamodb_items_to_resources(result['Items'])

    def dump(self):
        return self.dynamodb_table.scan()['Items']


class DynamoDbTableCreator():
    schema_file = os.path.join(
        pathlib.Path(__file__).parent.absolute(),
        'dynamodb_schema.json'
    )

    def __init__(self, boto3_dynamodb_resource, table_name):
        self.dynamodb = boto3_dynamodb_resource
        self.dynamodb_table = self.dynamodb.Table(table_name)
        self.table_name = table_name
        self._schema = None

    def create_table(self):
        try:
            self.dynamodb.create_table(**{
                **self.schema['table'],
                **{'TableName': self.table_name}
            })
        except self.dynamodb_table.meta.client.exceptions.ResourceInUseException:
            logging.warning(
                'Table %s already exists, skipping creation.',
                self.table_name)

    @property
    def schema(self):
        if not self._schema:
            with open(self.schema_file) as schema_file:
                self._schema = json.load(schema_file)
        return self._schema
