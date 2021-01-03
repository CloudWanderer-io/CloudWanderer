import unittest
from cloudwanderer.service_mappings import ServiceMappingCollection
from moto import mock_s3, mock_ec2, mock_iam
from ..mocks import generate_mock_session


@mock_s3
@mock_ec2
@mock_iam
class TestServiceMappings(unittest.TestCase):

    @mock_s3
    @mock_iam
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mock_session = generate_mock_session()
        self.mock_session_us_east_1 = generate_mock_session(region='us-east-1')
        self.maps = ServiceMappingCollection(boto3_session=self.mock_session)
        self.mock_session_us_east_1.resource('s3').Bucket('test-us-east-1').create()
        self.mock_session_us_east_1.resource('s3').Bucket('test-eu-west-1').create(
            CreateBucketConfiguration={'LocationConstraint': 'eu-west-1'})
        self.mock_session.resource('iam').Group('test-group').create()

    def test_s3_bucket_default_region(self):
        bucket = self.mock_session.resource('s3').Bucket('test-us-east-1')
        gsm = self.maps.get_service_mapping('s3')

        assert gsm.get_resource_region(bucket, self.mock_session.region_name) == 'us-east-1'

    def test_s3_bucket_eu_west_1(self):
        bucket = self.mock_session.resource('s3').Bucket('test-eu-west-1')
        gsm = self.maps.get_service_mapping('s3')

        assert gsm.get_resource_region(bucket, self.mock_session.region_name) == 'eu-west-1'

    def test_s3_has_resources_in_regions(self):
        gsm = self.maps.get_service_mapping('s3')

        assert gsm.has_global_resources_in_region('us-east-1') is False
        assert gsm.has_global_resources_in_region('eu-west-1') is False
        assert gsm.has_regional_resources

    def test_non_global_resource(self):
        vpc = next(iter(self.mock_session.resource('ec2').vpcs.all()))
        gsm = self.maps.get_service_mapping('ec2')

        assert gsm.get_resource_region(vpc, self.mock_session.region_name) == 'eu-west-2'
        assert gsm.has_global_resources_in_region('us-east-1') is False
        assert gsm.has_global_resources_in_region('eu-west-1') is False
        assert gsm.has_regional_resources

    def test_service_single_region_resource(self):
        iam_group = self.mock_session.resource('iam').Group('test-group')
        gsm = self.maps.get_service_mapping('iam')

        assert gsm.get_resource_region(iam_group, self.mock_session.region_name) == 'us-east-1'
        assert gsm.has_global_resources_in_region('us-east-1')
        assert gsm.has_regional_resources is False