"""Allows CloudWanderer to store resources in DynamoDB."""
import itertools
import json
import logging
import operator
import os
import pathlib
import sys
from functools import reduce
from random import randrange
from typing import TYPE_CHECKING, Any, Callable, Dict, Generator, Iterable, Iterator, List, Optional, Union

if sys.version_info >= (3, 8):
    from typing import Literal, TypedDict
else:
    from typing_extensions import Literal, TypedDict

import boto3
from boto3.dynamodb.conditions import Attr, ConditionBase, Key

if TYPE_CHECKING:
    from mypy_boto3_dynamodb import DynamoDBServiceResource
else:
    DynamoDBServiceResource = object

from ..cloud_wanderer_resource import CloudWandererResource, SecondaryAttribute
from ..urn import URN
from ..utils import standardise_data_types
from .base_connector import BaseStorageConnector

logger = logging.getLogger(__name__)


class DynamoDBQueryArgs(TypedDict, total=False):
    """Valid DynamoDB Query args to facilitate type hinting."""

    Select: Union[
        Literal["ALL_ATTRIBUTES"],
        Literal["ALL_PROJECTED_ATTRIBUTES"],
        Literal["SPECIFIC_ATTRIBUTES"],
        Literal["COUNT"],
        None,
    ]
    KeyConditionExpression: Optional[Union[str, ConditionBase]]
    FilterExpression: Optional[Union[str, ConditionBase]]
    IndexName: Optional[str]


def _gen_resource_type_index(service: str, resource_type: str) -> str:
    """Generate a hash key for the resource type index.

    Arguments:
        service (str): The service name (e.g. ``'ec2'``)
        resource_type (str): The resource type (e.g. ``'instance'``)
    """
    return f"{service}#{resource_type}"


def _gen_resource_type_range(account_id: str, region: Optional[str]) -> str:
    """Generate a range key for the resource type index.

    Arguments:
        account_id (str): The AWS Account ID
        region (str): The AWS region (e.g. ``'eu-west-1'``

    """
    return f"{account_id}#{region or ''}"


def _gen_resource_type_condition_expression(
    hash_key: str, account_id: str = None, region: str = None
) -> Union[ConditionBase]:
    """Generate a condition expression for the resource type index.

    Will match ONLY on hash_key if neither ``account_id`` nor ``region`` are specified.
    If ``account_id`` is specified without region it will match all records matching ``account_id``.
    If ``account_id`` and region are specified it will match records matching both.
    If region is specified without ``account_id`` it will match nothing.

    Arguments:
        hash_key (str): The key to match for ``_resource_type_index``
        account_id (str): The AWS account id to search for.
        region (str): The AWS region to search for (e.g. ``'eu-west-1'``)
    """
    condition_expression = Key("_resource_type_index").eq(hash_key)
    if not account_id:
        return condition_expression
    range_key = _gen_resource_type_range(account_id=account_id, region=region)
    return condition_expression & Key("_resource_type_range").begins_with(range_key)


def _primary_key_from_urn(urn: URN) -> str:
    """Create a DynamoDB Primary Key from a resource's URN.

    Arguments:
        urn (URN): The URN to generate the primary key from.
    """
    return f"resource#{urn}"


def _urn_from_primary_key(pk: str) -> URN:
    """Create an URN from a resource's primary key.

    Arguments:
        pk (str): The primary key from which to parse the URN.
    """
    return URN.from_string(pk.split("#")[1])


def _dynamodb_items_to_resources(items: Iterable[dict], loader: Callable) -> Iterator[CloudWandererResource]:
    """Convert a resource and its attributes dynamodb records to a ResourceDict.

    Arguments:
        items (Iterable[dict]): The list of records retrieved from dynamodb.
        loader (Callable): The method which can be used to fulfil the :meth:`CloudWandererResource.load`

    """
    for _, group in itertools.groupby(items, lambda x: x["_id"]):
        grouped_items = list(group)
        attributes = [
            SecondaryAttribute(name=attribute["_attr"], **_strip_dynamodb_attrs(attribute))
            for attribute in grouped_items
            if attribute["_attr"] != "BaseResource"
        ]
        base_resource = next(resource for resource in grouped_items if resource["_attr"] == "BaseResource")
        subresource_urns = [URN.from_string(urn) for urn in base_resource.get("_subresource_urns", [])]
        yield CloudWandererResource(
            urn=_urn_from_primary_key(base_resource["_id"]),
            subresource_urns=subresource_urns,
            resource_data=_strip_dynamodb_attrs(base_resource),
            secondary_attributes=attributes,
            loader=loader,
        )


def _strip_dynamodb_attrs(raw_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Remove any underscore prefixed keys as these are attributes we use to identify the DynamoDB record.

    Arguments:
        raw_dict: The raw dictionary of the DynamoDB record that needs cleaning.
    """
    return {k: v for k, v in raw_dict.items() if not k.startswith("_")}


class DynamoDbConnector(BaseStorageConnector):
    """CloudWanderer Storage Connector for DynamoDB.

    Arguments:
        table_name (str):
            The name of the table to store resources in.
        endpoint_url (str):
            Optional override endpoint url for DynamoDB.
        boto3_session (boto3.session.Session):
            Optional boto3 session to use to interact with DynamoDB.
            Useful if your DynamoDB table is in a different account/region to your configured defaults.
        number_of_shards (int):
            The number of shards to break records across low-cardinality indices.
            Prevents hot-partitions. If you don't know what this means, ignore this setting.
        client_args (dict): Arguments to pass into the boto3 client.
            See: :meth:`boto3.session.Session.client`

    Example:
        >>> import cloudwanderer
        >>> cloud_wanderer = cloudwanderer.CloudWanderer(
        ...     storage_connectors=[cloudwanderer.storage_connectors.DynamoDbConnector(
        ...         endpoint_url='http://localhost:8000'
        ...     )]
        ... )
    """

    def __init__(
        self,
        table_name: str = "cloud_wanderer",
        endpoint_url: str = None,
        boto3_session: boto3.session.Session = None,
        client_args: dict = None,
        number_of_shards: int = 10,
    ) -> None:
        """Initialise the DynamoDbConnector.

        Arguments:
            table_name (str):
                The name of the table to read/write from/to.
            endpoint_url (str):
                Optional endpoint url (useful primarily to write to a local DynamoDB).
            boto3_session (str):
                Optional boto3 session to use to persist params.
            client_args (dict):
                Optional dictionary of arguments to be passed to the boto3 dynamodb client.
            number_of_shards (int):
                Optional specification of the number of shards to create for low-cardinality indexes.

        """
        self.client_args = client_args or {}
        if endpoint_url:
            self.client_args["endpoint_url"] = endpoint_url
        self.boto3_session = boto3_session or boto3.session.Session()
        self.table_name = table_name
        self.number_of_shards = number_of_shards
        self.dynamodb: DynamoDBServiceResource = self.boto3_session.resource("dynamodb", **self.client_args)
        self.dynamodb_table = self.dynamodb.Table(table_name)

    def init(self) -> None:
        """Create the DynamoDB Database."""
        table_creator = DynamoDbTableCreator(boto3_dynamodb_resource=self.dynamodb, table_name=self.table_name)
        table_creator.create_table()

    def write_resource(self, resource: CloudWandererResource) -> None:
        logger.debug(f"Writing: {resource.urn} to {self.table_name}")
        item = {
            **self._generate_urn_index_values(resource.urn),
            **standardise_data_types(resource.cloudwanderer_metadata.resource_data or {}),
            **{"_subresource_urns": [str(urn) for urn in resource.subresource_urns]},
        }
        if resource.is_subresource:
            item["_parent_urn"] = str(resource.parent_urn)
        self.dynamodb_table.put_item(Item=item)
        for secondary_attribute in resource.cloudwanderer_metadata.secondary_attributes:
            self._write_secondary_attribute(
                urn=resource.urn, attribute_type=secondary_attribute.name, secondary_attribute=secondary_attribute
            )

    def _write_secondary_attribute(self, urn: URN, attribute_type: str, secondary_attribute: Dict[str, Any]) -> None:
        """Write the specified resource attribute to DynamoDb.

        Arguments:
            urn (URN): The resource whose attribute to write.
            attribute_type (str): The type of the resource attribute to write (usually the boto3 client method name)
            secondary_attribute (boto3.resources.base.ServiceResource): The resource attribute to write to storage.

        """
        logger.debug(f"Writing: {attribute_type} of {urn} to {self.table_name}")
        item = {
            **self._generate_urn_index_values(urn, attribute_type),
            **standardise_data_types(secondary_attribute or {}),
        }
        self.dynamodb_table.put_item(Item=item)

    def _generate_urn_index_values(self, urn: URN, attr: str = "BaseResource") -> Dict[str, Any]:
        values = {
            "_id": _primary_key_from_urn(urn),
            "_attr": attr,
            "_urn": str(urn),
            "_resource_type": urn.resource_type,
            "_account_id": urn.account_id,
            "_region": urn.region,
            "_service": urn.service,
            "_resource_type_range": _gen_resource_type_range(urn.account_id, urn.region),
        }
        if attr == "BaseResource":
            values.update(
                {
                    "_resource_type_index": self._gen_shard(_gen_resource_type_index(urn.service, urn.resource_type)),
                    "_account_id_index": self._gen_shard(urn.account_id),
                }
            )
        return values

    def read_resource(self, urn: URN) -> Optional[CloudWandererResource]:
        """Return the resource with the specified :class:`cloudwanderer.urn.URN`.

        Arguments:
            urn (URN): The AWS URN of the resource to return
        """
        result = self._paginated_query(
            DynamoDBQueryArgs(KeyConditionExpression=Key("_id").eq(_primary_key_from_urn(urn)))
        )
        return next(_dynamodb_items_to_resources(result, loader=self.read_resource), None)

    def read_resources(
        self,
        account_id: str = None,
        region: str = None,
        service: str = None,
        resource_type: str = None,
        urn: URN = None,
    ) -> Iterator["CloudWandererResource"]:
        query_generator = DynamoDbQueryGenerator(account_id, region, service, resource_type, urn)
        for condition_expression in query_generator.condition_expressions:
            query_args = DynamoDBQueryArgs(
                Select="ALL_PROJECTED_ATTRIBUTES",
                KeyConditionExpression=condition_expression,
            )
            if query_generator.index is not None:
                query_args["IndexName"] = query_generator.index
            if query_generator.condition_expressions is not None:
                query_args["FilterExpression"] = query_generator.filter_expression

            yield from _dynamodb_items_to_resources(self._paginated_query(query_args), loader=self.read_resource)

    def _paginated_query(self, query_args: DynamoDBQueryArgs) -> Generator[Dict[str, Any], None, None]:
        paginator = self.dynamodb.meta.client.get_paginator("query")
        pages = paginator.paginate(TableName=self.dynamodb_table.name, **query_args)
        yield from (item for result in pages for item in result["Items"])

    def read_all(self) -> Iterator[dict]:
        """Return raw data from all DynamoDB table records (not just resources)."""
        paginator = self.dynamodb_table.meta.client.get_paginator("scan")
        yield from (item for page in paginator.paginate(TableName=self.dynamodb_table.name) for item in page["Items"])

    def delete_resource(self, urn: URN) -> None:
        """Delete the resource and all its resource attributes from DynamoDB.

        Arguments:
            urn (URN): The URN of the resource to delete from Dynamo
        """
        resource_records = itertools.chain(
            self._paginated_query(DynamoDBQueryArgs(KeyConditionExpression=Key("_id").eq(_primary_key_from_urn(urn)))),
            self._paginated_query(
                DynamoDBQueryArgs(IndexName="parent_urn", KeyConditionExpression=Key("_parent_urn").eq(str(urn)))
            ),
        )
        with self.dynamodb_table.batch_writer() as batch:
            for record in resource_records:
                logger.debug("Deleting %s", record["_id"])
                batch.delete_item(Key={"_id": record["_id"], "_attr": record["_attr"]})

    def delete_resource_of_type_in_account_region(
        self, service: str, resource_type: str, account_id: str, region: str, urns_to_keep: List[URN] = None
    ) -> None:
        urns_to_keep = urns_to_keep or []
        logger.debug("Deleting any %s not in %s", resource_type, str([x.resource_id for x in urns_to_keep]))
        urns_to_keep = urns_to_keep or []
        resource_records = self.read_resources(
            service=service, resource_type=resource_type, account_id=account_id, region=region
        )
        for resource in resource_records:
            if resource.urn in urns_to_keep:
                logger.debug("Skipping deletion of %s as we were told to keep it.", resource.urn)
                continue
            self.delete_resource(urn=resource.urn)

    def _gen_shard(self, key: str, shard_id: int = None) -> str:
        """Append a shard designation to the end of a supplied key.

        Arguments:
            key (str): The key to which to append a shard id.
            shard_id (int): An optional shard id to append. If omitted a random shard will be generated.

        """
        shard_id = shard_id if shard_id is not None else randrange(self.number_of_shards - 1)
        return f"{key}#shard{shard_id}"

    def __repr__(self) -> str:
        """Return an instantiable string representation of this class."""
        return (
            f"{self.__class__.__name__}("
            f'table_name="{self.table_name}", '
            f'endpoint_url="{self.client_args.get("endpoint_url")}", '
            f'boto3_session="{self.boto3_session}", '
            f'client_args="{self.client_args}, '
            f"number_of_shards={self.number_of_shards}"
            ")"
        )

    def __str__(self) -> str:
        """Return a string representation of this class."""
        return f"<{self.__class__.__name__}={self.table_name}>"


class DynamoDbQueryGenerator:
    """Generate ConditionExpression and index name based on init params."""

    def __init__(
        self,
        account_id: str = None,
        region: str = None,
        service: str = None,
        resource_type: str = None,
        urn: URN = None,
        number_of_shards: int = 10,
    ) -> None:
        """Initialise QueryGenerator.

        Arguments:
            account_id (str): AWS Account ID
            region (str): AWS region (e.g. ``'eu-west-2'``)
            service (str): Service name (e.g. ``'ec2'``)
            resource_type (str): Resource Type (e.g. ``'instance'``)
            urn (URN): Urn of the resource to retrieve
            number_of_shards (int): The number of shards we need to query in the table
        """
        self.account_id = account_id
        self.region = region
        self.service = service
        self.resource_type = resource_type
        self.urn = urn
        self.number_of_shards = number_of_shards

    @property
    def index(self) -> Optional[str]:
        """Return the DynamoDB index to query.

        Raises:
            IndexNotAvailableException: Occurs when there is a no index that can fulfil this query.
                You will need to use a different set of arguments to query your resource if you receive this error.
        """
        index = None

        if self.service is not None and self.resource_type is not None:
            return "resource_type"
        if self.account_id is not None:
            return "account_id"
        if self.urn is not None:
            return index
        raise IndexNotAvailableException()

    @property
    def condition_expressions(self) -> Iterator[ConditionBase]:
        """Return the condition expression for the query.

        Raises:
            ValueError: If not all required arguments are passed for a given combination
        """
        if self.index is None and self.urn is not None:
            yield Key("_id").eq(_primary_key_from_urn(self.urn))
            return
        if self.index == "resource_type":
            if self.resource_type is None or self.service is None:
                raise ValueError("service, and resource_type must be specified when searching by resource type.")
            unsharded_key = _gen_resource_type_index(service=self.service, resource_type=self.resource_type)
            for sharded_key in self._yield_shards(unsharded_key):
                yield _gen_resource_type_condition_expression(
                    sharded_key, account_id=self.account_id, region=self.region
                )
            return
        if self.index == "account_id":
            if self.account_id is None:
                raise ValueError("account_id must be specified when searching by account id.")
            yield from [Key("_account_id_index").eq(shard) for shard in self._yield_shards(self.account_id)]
            return

    @property
    def filter_expression(self) -> ConditionBase:
        """Return a DynamoDB filter expression to use to filter out unwanted resources returned on our index."""
        query_args = ["account_id", "region", "service", "resource_type", "urn"]
        filter_elements = []
        for key in query_args:
            value = getattr(self, key)
            if value is not None:
                filter_elements.append(Attr(f"_{key}").eq(str(value)))
        return reduce(operator.and_, filter_elements)

    def _yield_shards(self, key: str) -> Generator[str, None, None]:
        for shard_id in range(0, self.number_of_shards):
            yield f"{key}#shard{shard_id}"


class DynamoDbTableCreator:
    """DynamoDB Table Creator class.

    Arguments:
        boto3_dynamodb_resource:
            The dynamodb resource object from boto3.
        table_name (str):
            The name of the table to create.

    """

    schema_file = os.path.join(pathlib.Path(__file__).parent.absolute(), "dynamodb_schema.json")

    def __init__(self, boto3_dynamodb_resource: DynamoDBServiceResource, table_name: str) -> None:
        """Initialise the DynamoDB Table Creator.

        Arguments:
            boto3_dynamodb_resource:
                The Boto3 DynamoDB resource object to use to create the table.
            table_name:
                The name we want the table to have.
        """
        self.dynamodb = boto3_dynamodb_resource
        self.dynamodb_table = self.dynamodb.Table(table_name)
        self.table_name = table_name
        self._schema = None

    def create_table(self) -> None:
        """Create the DynamoDB table."""
        try:
            self.dynamodb.create_table(**{**self.schema["table"], **{"TableName": self.table_name}})
        except self.dynamodb_table.meta.client.exceptions.ResourceInUseException:
            logger.info("Table %s already exists, skipping creation.", self.table_name)

    @property
    def schema(self) -> dict:
        """Return the DynamoDB Schema.

        Raises:
            FileNotFoundError: When we cannot find the schema file.
        """
        if not self._schema:
            with open(self.schema_file) as schema_file:
                self._schema = json.load(schema_file)
        if self._schema is None:
            raise FileNotFoundError(f"DynamoDB Scheme not found at {self.schema_file}")
        return self._schema


class IndexNotAvailableException(Exception):
    """There is no DynamoDB index available for this type of query."""
