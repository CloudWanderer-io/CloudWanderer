import unittest
from unittest.mock import ANY
import re
from ..helpers import get_default_mocker, GenericAssertionHelpers
from ..mocks import (
    add_infra,
    MOCK_COLLECTION_INSTANCES,
    MOCK_COLLECTION_BUCKETS,
    MOCK_COLLECTION_IAM_GROUPS,
    MOCK_COLLECTION_IAM_ROLES,
    MOCK_COLLECTION_IAM_ROLE_POLICIES
)
from cloudwanderer import CloudWanderer
from cloudwanderer.storage_connectors import MemoryStorageConnector


class TestCloudWandererWriteResources(unittest.TestCase, GenericAssertionHelpers):
    eu_west_2_resources = [{
        'urn': 'urn:aws:.*:eu-west-2:ec2:instance:.*',
        'attr': 'BaseResource',
        'VpcId': 'vpc-.*',
        'SubnetId': 'subnet-.*',
        'InstanceId': 'i-.*'
    }]
    us_east_1_resources = [{
        'urn': 'urn:aws:.*:us-east-1:iam:role:.*',
        'attr': 'BaseResource',
        'RoleName': 'test-role',
        'Path': re.escape('/')
    }, {
        'urn': 'urn:aws:.*:us-east-1:iam:role:.*',
        'attr': 'role_inline_policy_attachments',
        'PolicyNames': ['test-role-policy'],
    }, {
        'urn': 'urn:aws:.*:us-east-1:iam:role:.*',
        'attr': 'role_managed_policy_attachments',
        'AttachedPolicies': [{
                'PolicyName': 'APIGatewayServiceRolePolicy',
                'PolicyArn': 'arn:aws:iam::aws:policy/aws-service-role/APIGatewayServiceRolePolicy'
        }],
        'IsTruncated': False
    }, {
        'urn': 'urn:aws:.*:us-east-1:iam:role_policy:.*',
        'attr': 'BaseResource',
        'PolicyName': 'test-role-policy',
        'PolicyDocument': ANY
    }, {
        # This is a us-east-1 resource because s3 buckets are discovered from us-east-1 irrespective of their region.
        'urn': 'urn:aws:.*:eu-west-2:s3:bucket:.*',
        'attr': 'BaseResource',
        'Name': 'test-eu-west-2',
    }]

    @classmethod
    def setUpClass(cls):
        cls.enabled_regions = ['eu-west-2', 'us-east-1', 'ap-east-1']
        get_default_mocker().start_general_mock(
            restrict_regions=cls.enabled_regions,
            restrict_services=['ec2', 's3', 'iam'],
            restrict_collections=[
                MOCK_COLLECTION_INSTANCES, MOCK_COLLECTION_BUCKETS,
                MOCK_COLLECTION_IAM_GROUPS, MOCK_COLLECTION_IAM_ROLES,
                MOCK_COLLECTION_IAM_ROLE_POLICIES
            ]
        )
        add_infra(regions=cls.enabled_regions)

    @classmethod
    def tearDownClass(cls):
        get_default_mocker().stop_general_mock()

    def setUp(self):
        self.storage_connector = MemoryStorageConnector()
        self.wanderer = CloudWanderer(
            storage_connectors=[self.storage_connector]
        )

    def test_write_resources(self):

        self.wanderer.write_resources()

        for region_name in self.enabled_regions:
            self.assert_dictionary_overlap(self.storage_connector.read_all(), [{
                'urn': f'urn:aws:.*:{region_name}:ec2:instance:.*',
                'attr': 'BaseResource',
                'VpcId': 'vpc-.*',
                'SubnetId': 'subnet-.*',
                'InstanceId': 'i-.*'
            }, {
                'urn': f'urn:aws:.*:{region_name}:s3:bucket:.*',
                'attr': 'BaseResource',
                'Name': f'test-{region_name}',
            }])

            if region_name == 'us-east-1':
                self.assert_dictionary_overlap(self.storage_connector.read_all(), self.us_east_1_resources)
            else:
                self.assert_no_dictionary_overlap(self.storage_connector.read_all(), [{
                    'urn': f'urn:aws:.*:{region_name}:iam:role:.*',
                    'attr': 'BaseResource',
                    'RoleName': 'test-role',
                    'Path': re.escape('/')
                }])

    def test_write_resources_exclude_resources(self):
        self.wanderer.write_resources(exclude_resources=['ec2:instance'])

        for region_name in self.enabled_regions:
            self.assert_no_dictionary_overlap(self.storage_connector.read_all(), [{
                'urn': f'urn:aws:.*:{region_name}:ec2:instance:.*',
                'attr': 'BaseResource',
                'VpcId': 'vpc-.*',
                'SubnetId': 'subnet-.*',
                'InstanceId': 'i-.*'
            }])
        self.assert_dictionary_overlap(self.storage_connector.read_all(), self.us_east_1_resources)

    def test_write_resources_eu_west_1(self):
        self.wanderer.write_resources(regions=['eu-west-2'], )

        self.assert_dictionary_overlap(self.storage_connector.read_all(), self.eu_west_2_resources)
        self.assert_no_dictionary_overlap(self.storage_connector.read_all(), self.us_east_1_resources)

    def test_write_resources_us_east_1(self):
        self.wanderer.write_resources(regions=['us-east-1'])

        self.assert_dictionary_overlap(self.storage_connector.read_all(), self.us_east_1_resources)
        self.assert_no_dictionary_overlap(self.storage_connector.read_all(), self.eu_west_2_resources)

    def test_write_resources_of_service_eu_west_1(self):
        self.wanderer.write_resources(regions=['eu-west-2'], service_names=['ec2'])
        self.wanderer.write_resources(regions=['eu-west-2'], service_names=['s3'])

        self.assert_dictionary_overlap(self.storage_connector.read_all(), self.eu_west_2_resources)
        self.assert_no_dictionary_overlap(self.storage_connector.read_all(), self.us_east_1_resources)

    def test_write_resources_of_service_us_east_1(self):
        self.wanderer.write_resources(service_names=['ec2'], regions=['us-east-1'])
        self.wanderer.write_resources(service_names=['s3'], regions=['us-east-1'])
        self.wanderer.write_resources(service_names=['iam'], regions=['us-east-1'])

        self.assert_dictionary_overlap(self.storage_connector.read_all(), self.us_east_1_resources)
        self.assert_no_dictionary_overlap(self.storage_connector.read_all(), self.eu_west_2_resources)

    def test_write_resources_of_type_eu_west_1(self):
        self.wanderer.write_resources(
            regions=['eu-west-2'], service_names=['s3'], resource_types=['bucket'])
        self.wanderer.write_resources(
            regions=['eu-west-2'], service_names=['ec2'], resource_types=['instance'])
        self.wanderer.write_resources(
            regions=['eu-west-2'], service_names=['iam'], resource_types=['role'])

        self.assert_dictionary_overlap(self.storage_connector.read_all(), self.eu_west_2_resources)
        self.assert_no_dictionary_overlap(self.storage_connector.read_all(), self.us_east_1_resources)

    def test_write_resources_of_type_us_east_1(self):
        self.wanderer.write_resources(
            service_names=['s3'], resource_types=['bucket'], regions=['us-east-1'])
        self.wanderer.write_resources(
            service_names=['ec2'], resource_types=['instance'], regions=['us-east-1'])
        self.wanderer.write_resources(
            service_names=['iam'], resource_types=['role'], regions=['us-east-1'])

        self.assert_dictionary_overlap(self.storage_connector.read_all(), self.us_east_1_resources)
        self.assert_no_dictionary_overlap(self.storage_connector.read_all(), self.eu_west_2_resources)
