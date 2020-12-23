"""Classes for the CloudWanderer DynamoDB Storage Connector."""
from typing import List
import itertools
import logging
import os
import pathlib
import boto3
import json
from datetime import datetime
from random import randrange
from decimal import Decimal
from .base_connector import BaseStorageConnector
from boto3.dynamodb.conditions import Key
from ..cloud_wanderer import CloudWandererResource
from ..aws_urn import AwsUrn

logger = logging.getLogger(__name__)


def gen_resource_type_index(service: str, resource_type: str) -> str:
    """Generate a hash key for the resource type index."""
    return f"{service}#{resource_type}"


def gen_resource_type_range(account_id: str, region: str) -> str:
    """Generate a range key for the resource type index."""
    return f"{account_id}#{region}"


def gen_resource_type_condition_expression(hash_key: str, account_id: str = None, region: str = None) -> bool:
    """Generate a condition expression for the resource type index.

    Will match ONLY on hash_key if neither ``account_id`` nor ``region`` are specified.
    If ``account_id`` is specified without region it will match all records matching ``account_id``.
    If ``account_id`` and region are specified it will match records matching both.
    If region is specified without ``account_id`` it will match nothing.
    """
    condition_expression = Key('_resource_type_index').eq(hash_key)
    if not account_id and not region:
        return condition_expression
    range_key = gen_resource_type_range(account_id=account_id, region=region)
    return condition_expression & Key('_resource_type_range').begins_with(range_key)


def primary_key_from_urn(urn: AwsUrn) -> str:
    """Create a DynamoDB Primary Key from a resource's URN."""
    return f"resource#{urn}"


def urn_from_primary_key(pk: str) -> AwsUrn:
    """Create an AwsUrn from a resource's primary key."""
    return AwsUrn.from_string(pk.split('#')[1])


def dynamodb_items_to_resources(items: List[dict]) -> CloudWandererResource:
    """Convert a resource and its attributes dynamodb records to a ResourceDict."""
    for item_id, group in itertools.groupby(items, lambda x: x['_id']):
        grouped_items = list(group)
        attributes = [attribute for attribute in grouped_items if attribute['_attr'] != 'BaseResource']
        base_resource = next(iter(resource for resource in grouped_items if resource['_attr'] == 'BaseResource'))
        yield CloudWandererResource(
            urn=urn_from_primary_key(base_resource['_id']),
            resource_data=base_resource,
            resource_attributes=attributes
        )


def json_object_hook(dct: dict) -> dict:
    """Clean out empty strings to avoid ValidationException."""
    for key, value in dct.items():
        if value == '':
            dct[key] = None
    return dct


def json_default(item: object) -> object:
    """JSON object type converter that handles datetime objects."""
    if isinstance(item, datetime):
        return item.isoformat()


def standardise_data_types(resource: dict) -> dict:
    """Return a dictionary normalised to datatypes acceptable for DynamoDB."""
    result = json.loads(json.dumps(resource, default=json_default), object_hook=json_object_hook, parse_float=Decimal)
    return result


class DynamoDbConnector(BaseStorageConnector):
    """CloudWanderer Storage Connector for DynamoDB.

    Arguments:
        table_name (str): The name of the table to store resources in.
        endpoint_url (str): Optional override endpoint url for DynamoDB.
        boto3_session (boto3.session.Session):
            Optional boto3 session to use to interact with DynamoDB.
            Useful if your DynamoDB table is in a different account/region to your configured defaults.
        number_of_shards (int):
            The number of shards to break records across low-cardinality indices.
            Prevents hot-partitions. If you don't know what this means, ignore this setting.
        client_args (dict): Arguments to pass into the boto3 client.
            See: :meth:`boto3.session.Session.client`
    """

    def __init__(
            self, table_name: str = 'cloud_wanderer', endpoint_url: str = None,
            boto3_session: boto3.session.Session = None, client_args: dict = None, number_of_shards: int = 10) -> None:
        """Initialise the DynamoDbConnector."""
        client_args = client_args or {}
        if endpoint_url:
            client_args['endpoint_url'] = endpoint_url
        self.boto3_session = boto3_session or boto3.Session()
        self.table_name = table_name
        self.number_of_shards = number_of_shards
        self.dynamodb = self.boto3_session.resource('dynamodb', **client_args)
        self.dynamodb_table = self.dynamodb.Table(table_name)

    def init(self) -> None:
        """Create the DynamoDB Database."""
        table_creator = DynamoDbTableCreator(
            boto3_dynamodb_resource=self.dynamodb,
            table_name=self.table_name
        )
        table_creator.create_table()

    def write_resource(self, urn: AwsUrn, resource: boto3.resources.base.ServiceResource) -> None:
        """Write the specified resource to DynamoDB.

        Arguments:
            urn (cloudwanderer.aws_urn.AwsUrn): The URN of the resource.
            resource: The boto3 Resource object representing the resource.
        """
        logger.debug(f"Writing: {urn} to {self.table_name}")
        item = {
            **self._generate_index_values_for_write(urn),
            **standardise_data_types(resource.meta.data or {})
        }
        self.dynamodb_table.put_item(
            Item=item
        )

    def write_resource_attribute(
            self, urn: AwsUrn, attribute_type: str, resource_attribute: boto3.resources.base.ServiceResource) -> None:
        """Write the specified resource attribute to DynamoDb."""
        logger.debug(f"Writing: {attribute_type} of {urn} to {self.table_name}")
        item = {
            **self._generate_index_values_for_write(urn, attribute_type),
            **standardise_data_types(resource_attribute.meta.data or {})
        }
        self.dynamodb_table.put_item(
            Item=item
        )

    def _generate_index_values_for_write(self, urn: AwsUrn, attr: str = 'BaseResource') -> dict:
        values = {
            '_id': primary_key_from_urn(urn),
            '_attr': attr,
            '_urn': str(urn),
            '_resource_type': gen_resource_type_index(urn.service, urn.resource_type),
            '_account_id': f"{urn.account_id}",
            '_region': f"{urn.region}",
            '_resource_type_range': gen_resource_type_range(urn.account_id, urn.region)
        }
        if attr == 'BaseResource':
            values.update({
                '_resource_type_index': f"{self._gen_shard(gen_resource_type_index(urn.service, urn.resource_type))}",
                '_account_id_index': f"{self._gen_shard(urn.account_id)}"
            })
        return values

    def read_resource(self, urn: AwsUrn) -> List['CloudWandererResource']:
        """Return the resource with the specified :class:`cloudwanderer.aws_urn.AwsUrn)`.

        Arguments:
            urn (cloudwanderer.aws_urn.AwsUrn): The AWS URN of the resource to return
        """
        result = self.dynamodb_table.query(
            KeyConditionExpression=Key('_id').eq(primary_key_from_urn(urn))
        )
        yield from dynamodb_items_to_resources(result['Items'])

    def read_resource_of_type(self, service: str, resource_type: str) -> List['CloudWandererResource']:
        """Return all resources of type.

        Args:
            service (str): Service name (e.g. ``'ec2'``)
            resource_type (str): Resource Type (e.g. ``'instance'``)
        """
        yield from dynamodb_items_to_resources(self._read_from_resource_type_index(service, resource_type))

    def _read_from_resource_type_index(
            self, service: str, resource_type: str, account_id: str = None, region: str = None) -> None:

        for shard_id in range(0, self.number_of_shards):
            hash_key = self._gen_shard(gen_resource_type_index(service, resource_type), shard_id)
            logger.debug("Fetching shard %s", hash_key)
            result = self.dynamodb_table.query(
                IndexName='resource_type',
                Select='ALL_PROJECTED_ATTRIBUTES',
                KeyConditionExpression=gen_resource_type_condition_expression(
                    hash_key=hash_key,
                    account_id=account_id,
                    region=region
                )
            )
            yield from result['Items']

    def read_all_resources_in_account(self, account_id: str) -> List['CloudWandererResource']:
        """Return all resources in account.

        Args:
            account_id (str): AWS Account ID
        """
        for shard_id in range(0, self.number_of_shards):
            key = self._gen_shard(account_id, shard_id)
            logger.debug("Fetching shard %s", key)
            result = self.dynamodb_table.query(
                IndexName='account_id',
                Select='ALL_PROJECTED_ATTRIBUTES',
                KeyConditionExpression=Key('_account_id_index').eq(key)
            )
            yield from dynamodb_items_to_resources(result['Items'])

    def read_resource_of_type_in_account(
            self, service: str, resource_type: str, account_id: str) -> List['CloudWandererResource']:
        """Return all resources of the specified type in the specified AWS account.

        Args:
            service (str): Service name, e.g. ``'ec2'``
            resource_type (str): Resource type, e.g. ``'instance'``
            account_id (str): AWS Account ID
        """
        for shard_id in range(0, self.number_of_shards):
            key = self._gen_shard(account_id, shard_id)
            logger.debug("Fetching shard %s", key)
            result = self.dynamodb_table.query(
                IndexName='account_id',
                Select='ALL_PROJECTED_ATTRIBUTES',
                KeyConditionExpression=(
                    Key('_account_id_index').eq(key) & Key('_resource_type').eq(
                        gen_resource_type_index(service, resource_type))
                )
            )
            yield from dynamodb_items_to_resources(result['Items'])

    def read_all(self) -> List['CloudWandererResource']:
        """Return raw data from all DynamoDB table records (not just resources)."""
        yield from self.dynamodb_table.scan()['Items']

    def delete_resource(self, urn: AwsUrn) -> None:
        """Delete the resource and all its resource attributes from DynamoDB."""
        resource_records = self.dynamodb_table.query(
            KeyConditionExpression=Key('_id').eq(primary_key_from_urn(urn))
        )['Items']
        with self.dynamodb_table.batch_writer() as batch:
            for record in resource_records:
                logger.debug("Deleting %s", record['_id'])
                batch.delete_item(
                    Key={
                        '_id': record['_id'],
                        '_attr': record['_attr']
                    }
                )

    def delete_resource_of_type_in_account_region(
            self, service: str, resource_type: str, account_id: str, region: str, urns_to_keep: AwsUrn = None) -> None:
        """Delete resources of type in account id unless in list of URNs."""
        logger.debug('Deleting any %s not in %s', resource_type, str([x.resource_id for x in urns_to_keep]))
        urns_to_keep = urns_to_keep or []
        resource_records = dynamodb_items_to_resources(self._read_from_resource_type_index(
            service=service,
            resource_type=resource_type,
            account_id=account_id,
            region=region
        ))
        for resource in resource_records:
            if resource.urn in urns_to_keep:
                logger.debug('Skipping deletion of %s as we were told to keep it.', resource.urn)
                continue
            self.delete_resource(urn=resource.urn)

    def _gen_shard(self, key: str, shard_id: int = None) -> str:
        """Append a shard designation to the end of a supplied key."""
        shard_id = shard_id if shard_id is not None else randrange(self.number_of_shards - 1)
        return f"{key}#shard{shard_id}"


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

    def __init__(self, boto3_dynamodb_resource: boto3.session.Session.resource, table_name: str) -> None:
        """Initialise the DynamoDB Table Creator."""
        self.dynamodb = boto3_dynamodb_resource
        self.dynamodb_table = self.dynamodb.Table(table_name)
        self.table_name = table_name
        self._schema = None

    def create_table(self) -> None:
        """Create the DynamoDB table."""
        try:
            self.dynamodb.create_table(**{
                **self.schema['table'],
                **{'TableName': self.table_name}
            })
        except self.dynamodb_table.meta.client.exceptions.ResourceInUseException:
            logger.warning(
                'Table %s already exists, skipping creation.',
                self.table_name)

    @property
    def schema(self) -> dict:
        """Return the DynamoDB Schema."""
        if not self._schema:
            with open(self.schema_file) as schema_file:
                self._schema = json.load(schema_file)
        return self._schema
