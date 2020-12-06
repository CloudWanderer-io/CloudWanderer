import logging
import os
import pathlib
import boto3
import json
from datetime import datetime
from .base_connector import BaseConnector


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
                **{'_id': f"resource#{urn}"},
                **self._standardise_data_types(resource.meta.data)
            }
        )

    def _standardise_data_types(self, resource):
        result = resource.copy()
        for k, v in resource.items():
            if isinstance(v, datetime):
                result[k] = v.isoformat()
        return result

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
        print(self._schema)
        return self._schema
