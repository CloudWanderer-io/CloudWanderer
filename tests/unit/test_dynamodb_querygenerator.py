import unittest
from cloudwanderer.storage_connectors.dynamodb import (
    DynamoDbQueryGenerator,
    IndexNotAvailableException,
    Key,
    Attr
)


class TestDynamoDbQueryGenerator(unittest.TestCase):

    def test_account_id(self):
        qg = DynamoDbQueryGenerator(account_id='111111111111')

        assert qg.index == 'account_id'
        assert next(qg.condition_expressions) == Key('_account_id_index').eq('111111111111#shard0')
        assert qg.filter_expression == Attr('_account_id').eq('111111111111')

    def test_region(self):
        qg = DynamoDbQueryGenerator(region='eu-west-2')

        self.assertRaises(IndexNotAvailableException, getattr, qg, 'index')

    def test_service(self):
        qg = DynamoDbQueryGenerator(service='ec2')

        self.assertRaises(IndexNotAvailableException, getattr, qg, 'index')

    def test_resource_type(self):
        qg = DynamoDbQueryGenerator(resource_type='vpc')

        self.assertRaises(IndexNotAvailableException, getattr, qg, 'index')

    def test_service_and_resource_type(self):
        qg = DynamoDbQueryGenerator(service='ec2', resource_type='vpc')

        assert qg.index == 'resource_type'
        self._validate_sharded_keys(key='_resource_type_index', value='ec2#vpc', expressions=qg.condition_expressions)
        assert qg.filter_expression == Attr('_service').eq('ec2') & Attr('_resource_type').eq('vpc')

    def test_account_id_and_service_and_resource_type(self):
        qg = DynamoDbQueryGenerator(account_id='111111111111', service='ec2', resource_type='vpc')

        assert qg.index == 'resource_type'
        assert next(qg.condition_expressions) == Key('_resource_type_index').eq(
            'ec2#vpc#shard0') & Key('_resource_type_range').begins_with('111111111111#')
        assert qg.filter_expression == Attr('_account_id').eq('111111111111') & Attr(
            '_service').eq('ec2') & Attr('_resource_type').eq('vpc')

    def _validate_sharded_keys(self, key, value, expressions) -> None:
        for i in range(9):
            expression = next(expressions)
            assert expression == Key('_resource_type_index').eq(f'{value}#shard{i}')
