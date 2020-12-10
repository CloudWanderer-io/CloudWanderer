"""Classes for the CloudWanderer DynamoDB Storage Connector."""
import logging
import itertools
import os
import pathlib
import boto3
import json
from datetime import datetime
from random import randrange
from decimal import Decimal
from .base_connector import BaseConnector
from boto3.dynamodb.conditions import Key
from ..cloud_wanderer import ResourceDict
from ..aws_urn import AwsUrn


def gen_resource_type_index(service, resource_type):
    """Generate a primary key for the resource type index."""
    return f"{service}#{resource_type}"


def gen_shard(key, shard_id=None):
    """Append a shard designation to the end of a supplied key."""
    shard_id = shard_id if shard_id is not None else randrange(9)
    return f"{key}#shard{shard_id}"


def primary_key_from_urn(urn):
    """Create a DynamoDB Primary Key from a resource's URN."""
    return f"resource#{urn}"


def urn_from_primary_key(pk):
    """Create an AwsUrn from a resource's primary key."""
    return AwsUrn.from_string(pk.split('#')[1])


def dynamodb_items_to_resources(items):
    """Convert a resource and its attributes dynamodb records to a ResourceDict."""
    for item_id, group in itertools.groupby(items, lambda x: x['_id']):
        item = {k: v for item in group for k, v in item.items()}
        yield ResourceDict(
            urn=urn_from_primary_key(item['_id']),
            resource=item
        )


def json_default(item):
    """JSON object type converter that handles datetime objects."""
    if isinstance(item, datetime):
        return item.isoformat()


def standardise_data_types(resource):
    """Return a dictionary normalised to datatypes acceptable for DynamoDB."""
    result = json.loads(json.dumps(resource, default=json_default), parse_float=Decimal)
    return result


class DynamoDbConnector(BaseConnector):
    """CloudWanderer Storage Connector for DynamoDB.

    Arguments:
        table_name (str): The name of the table to store resources in.
        endpoint_url (str): optional override endpoint url for DynamoDB.
    """

    def __init__(self, table_name='cloud_wanderer', endpoint_url=None):
        """Initialise the DynamoDbConnector."""
        self.endpoint_url = endpoint_url
        self.table_name = table_name
        self.dynamodb = boto3.resource('dynamodb', endpoint_url=endpoint_url)
        self.dynamodb_table = self.dynamodb.Table(table_name)

    def init(self):
        """Create the DynamoDB Database."""
        table_creator = DynamoDbTableCreator(
            boto3_dynamodb_resource=self.dynamodb,
            table_name=self.table_name
        )
        table_creator.create_table()

    def write_resource(self, urn, resource):
        """Write the specified resource to DynamoDB.

        Arguments:
            urn (cloudwanderer.AwsUrn): The URN of the resource.
            resource: The boto3 Resource object representing the resource.
        """
        logging.debug(f"Writing: {urn} to {self.table_name}")
        item = {
            **self._generate_index_values_for_write(urn),
            **standardise_data_types(resource.meta.data or {})
        }
        self.dynamodb_table.put_item(
            Item=item
        )

    def write_resource_attribute(self, urn, attribute_type, resource_attribute,):
        """Write the specified resource attribute to DynamoDb."""
        logging.debug(f"Writing: {attribute_type} of {urn} to {self.table_name}")
        item = {
            **self._generate_index_values_for_write(urn, attribute_type),
            **standardise_data_types(resource_attribute.meta.data or {})
        }
        self.dynamodb_table.put_item(
            Item=item
        )

    def _generate_index_values_for_write(self, urn, attr='BaseResource'):
        values = {
            '_id': primary_key_from_urn(urn),
            '_attr': attr,
            '_urn': str(urn),
            '_resource_type': f"{gen_resource_type_index(urn.service, urn.resource_type)}",
            '_account_id': f"{urn.account_id}",
        }
        if attr == 'BaseResource':
            values.update({
                '_resource_type_index': f"{gen_shard(gen_resource_type_index(urn.service, urn.resource_type))}",
                '_account_id_index': f"{gen_shard(urn.account_id)}"
            })
        return values

    def read_resource(self, urn):
        """Return the resource with the specified :class:`cloudwanderer.AwsUrn`.

        Arguments:
            urn (cloudwanderer.AwsUrn): The AWS URN of the resource to return
        """
        result = self.dynamodb_table.query(
            KeyConditionExpression=Key('_id').eq(primary_key_from_urn(urn))
        )
        yield from dynamodb_items_to_resources(result['Items'])

    def read_resource_of_type(self, service, resource_type):
        """Return all resources of type.

        Args:
            service (str): Service name (e.g. ec2)
            resource_type (str): Resource Type (e.g. instance)
        """
        for shard_id in range(0, 9):
            key = gen_shard(gen_resource_type_index(service, resource_type), shard_id)
            logging.debug("Fetching shard %s", key)
            result = self.dynamodb_table.query(
                IndexName='resource_type',
                Select='ALL_PROJECTED_ATTRIBUTES',
                KeyConditionExpression=Key('_resource_type_index').eq(key)
            )
            yield from dynamodb_items_to_resources(result['Items'])

    def read_all_resources_in_account(self, account_id):
        """Return all resources in account.

        Args:
            account_id (str): AWS Account ID
        """
        for shard_id in range(0, 9):
            key = gen_shard(account_id, shard_id)
            logging.debug("Fetching shard %s", key)
            result = self.dynamodb_table.query(
                IndexName='account_id',
                Select='ALL_PROJECTED_ATTRIBUTES',
                KeyConditionExpression=Key('_account_id_index').eq(key)
            )
            yield from dynamodb_items_to_resources(result['Items'])

    def read_resource_of_type_in_account(self, service, resource_type, account_id):
        """Return all resources of the specified type in the specified AWS account.

        Args:
            service (str): Service name, e.g. ``ec2``
            resource_type (str): Resouce type, e.g. ``instance``
            account_id (str): AWS Account ID
        """
        for shard_id in range(0, 9):
            key = gen_shard(account_id, shard_id)
            logging.debug("Fetching shard %s", key)
            result = self.dynamodb_table.query(
                IndexName='account_id',
                Select='ALL_PROJECTED_ATTRIBUTES',
                KeyConditionExpression=(
                    Key('_account_id_index').eq(key)
                    & Key('_resource_type').eq(gen_resource_type_index(service, resource_type))
                )
            )
            yield from dynamodb_items_to_resources(result['Items'])

    def read_all(self):
        """Return all DynamoDB table records (not just resources)."""
        return dynamodb_items_to_resources(self.dynamodb_table.scan()['Items'])


class DynamoDbTableCreator():
    """DynamoDB Table Creator class.

    Arguments:
        boto3_dynamodb_resource:
            The dynamodb resource object from boto3.
        table_name (str):
            The name of the table to create.

    """

    schema_file = os.path.join(
        pathlib.Path(__file__).parent.absolute(),
        'dynamodb_schema.json'
    )

    def __init__(self, boto3_dynamodb_resource, table_name):
        """Initialise the DynamoDB Table Creator."""
        self.dynamodb = boto3_dynamodb_resource
        self.dynamodb_table = self.dynamodb.Table(table_name)
        self.table_name = table_name
        self._schema = None

    def create_table(self):
        """Create the DynamoDB table."""
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
        """Return the DynamoDB Schema."""
        if not self._schema:
            with open(self.schema_file) as schema_file:
                self._schema = json.load(schema_file)
        return self._schema
