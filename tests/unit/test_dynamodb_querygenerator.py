import re
import unittest
from cloudwanderer.storage_connectors.dynamodb import (
    DynamoDbQueryGenerator,
    gen_resource_type_index,
    IndexNotAvailableException
)


class TestDynamoDbQueryGenerator(unittest.TestCase):

    def test_account_id(self):
        qg = DynamoDbQueryGenerator(account_id='111111111111')
        assert qg.index == 'account_id'
        self._validate_hash_only_conditions('_account_id_index', '111111111111', list(qg.condition_expressions))

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
        self._validate_hash_only_conditions('_resource_type_index', gen_resource_type_index(
            'ec2', 'vpc'), list(qg.condition_expressions))

    def test_account_id_and_service_and_resource_type(self):
        qg = DynamoDbQueryGenerator(account_id='111111111111', service='ec2', resource_type='vpc')
        assert qg.index == 'resource_type'
        self._validate_hash_and_range_conditions(
            hash_key='_resource_type_index',
            hash_value=gen_resource_type_index('ec2', 'vpc'),
            range_key='_resource_type_range',
            range_value='111111111111#',
            expressions=list(qg.condition_expressions))

    def _validate_hash_only_conditions(self, key, value, expressions) -> None:
        assert len(expressions) > 0
        for expression in expressions:
            actual_key = expression._values[0].name
            actual_value = re.sub(r'#shard\d+', '', expression._values[1])
            assert key == actual_key
            assert value == actual_value

    def _validate_hash_and_range_conditions(self, hash_key, hash_value, range_key, range_value, expressions) -> None:
        assert len(expressions) > 0
        for expression in expressions:
            hash_condition = expression._values[0]
            actual_hash_key = hash_condition._values[0].name
            actual_hash_value = re.sub(r'#shard\d+', '', hash_condition._values[1])
            assert hash_key == actual_hash_key
            assert hash_value == actual_hash_value
            range_condition = expression._values[1]
            actual_range_key = range_condition._values[0].name
            actual_range_value = re.sub(r'#shard\d+', '', range_condition._values[1])
            assert range_key == actual_range_key
            assert range_value == actual_range_value
