import unittest

import boto3
from cloudwanderer.global_service_mappings import GlobalServiceMappingFactory
from moto import mock_s3
from ..mocks import generate_mock_session

@mock_s3
class TestGlobalServiceMappings(unittest.TestCase):

    @mock_s3
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mock_session = generate_mock_session(region='us-east-1')
        self.mappings = GlobalServiceMappingFactory(boto3_session=self.mock_session).load_global_service_mappings()
        self.mock_session.resource('s3').Bucket('test-us-east-1').create()
        self.mock_session.resource('s3').Bucket('test-eu-west-1').create(CreateBucketConfiguration={'LocationConstraint':'eu-west-1'})

    def test_s3_bucket_default_region(self):
        bucket = self.mock_session.resource('s3').Bucket('test-us-east-1')

        region = self.mappings['s3'].get_resource_region(bucket)

        assert region == 'us-east-1'

    def test_s3_bucket_eu_west_1(self):
        bucket = self.mock_session.resource('s3').Bucket('test-eu-west-1')

        region = self.mappings['s3'].get_resource_region(bucket)

        assert region == 'eu-west-1'
