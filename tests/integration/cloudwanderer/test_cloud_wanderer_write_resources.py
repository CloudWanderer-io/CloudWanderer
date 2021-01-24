import unittest
from unittest.mock import ANY
from ..helpers import MockStorageConnectorMixin, get_default_mocker
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


class TestCloudWandererWriteResources(unittest.TestCase, MockStorageConnectorMixin):

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
            self.assert_resource_exists(
                region=region_name,
                service='ec2',
                resource_type='instance',
                attributes_dict={
                    'vpc_id': ANY,
                    'subnet_id': ANY,
                    'instance_id': ANY
                }
            )

            self.assert_resource_exists(
                region=region_name,
                service='s3',
                resource_type='bucket',
                attributes_dict={
                    'name': f'test-{region_name}'
                }
            )
            if region_name == 'us-east-1':
                self.assert_resource_exists(
                    region=region_name,
                    service='iam',
                    resource_type='role',
                    attributes_dict={
                        'role_name': 'test-role',
                        'path': '/'
                    },
                    secondary_attributes_dict={
                        "[].PolicyNames[0]": ['test-role-policy'],
                        "[].AttachedPolicies[0].PolicyName": ['APIGatewayServiceRolePolicy']
                    }
                )
            else:
                self.assert_resource_not_exists(
                    region=region_name,
                    service='iam',
                    resource_type='role',
                    attributes_dict={
                        'role_name': 'test-role',
                        'path': '/'
                    },
                )

    def test_write_resources_in_region_default_region(self):

        self.wanderer.write_resources_in_region()

        self.assert_resource_exists(
            region='eu-west-2',
            service='ec2',
            resource_type='instance',
            attributes_dict={
                'vpc_id': ANY,
                'subnet_id': ANY,
                'instance_id': ANY
            }
        )
        self.assert_resource_not_exists(
            region='eu-west-2',
            service='s3',
            resource_type='bucket',
            attributes_dict={
                'name': 'test-eu-west-2'
            }
        )
        self.assert_resource_not_exists(
            region='us-east-1',
            service='iam',
            resource_type='role',
            attributes_dict={
                'role_name': 'test-role',
                'path': '/'
            },
        )

    def test_write_resources_in_region_specify_region(self):
        self.wanderer.write_resources_in_region(region_name='us-east-1')

        self.assert_resource_exists(
            region='us-east-1',
            service='ec2',
            resource_type='instance',
            attributes_dict={
                'vpc_id': ANY,
                'subnet_id': ANY,
                'instance_id': ANY
            }
        )
        self.assert_resource_exists(
            region='us-east-1',
            service='s3',
            resource_type='bucket',
            attributes_dict={
                'name': 'test-us-east-1'
            }
        )
        self.assert_resource_exists(
            region='us-east-1',
            service='iam',
            resource_type='role',
            attributes_dict={
                'role_name': 'test-role',
                'path': '/'
            },
            secondary_attributes_dict={
                "[].PolicyNames[0]": ['test-role-policy'],
                "[].AttachedPolicies[0].PolicyName": ['APIGatewayServiceRolePolicy']
            }
        )
        self.assert_resource_exists(
            region='us-east-1',
            service='iam',
            resource_type='role',
            attributes_dict={
                'role_name': 'test-role',
                'path': '/'
            },
            secondary_attributes_dict={
                "[].PolicyNames[0]": ['test-role-policy'],
                "[].AttachedPolicies[0].PolicyName": ['APIGatewayServiceRolePolicy']
            }
        )
        self.assert_resource_not_exists(
            region='us-east-1',
            service='iam',
            resource_type='role',
            attributes_dict={
                'role_name': 'test-role',
                'path': '/'
            },
        )
        self.assert_resource_exists(
            region='us-east-1',
            service='iam',
            resource_type='role_policy',
            attributes_dict={
                'policy_name': 'test-role-policy',
                'policy_document': ANY
            }
        )

    def test_write_resources_of_service_default_region(self):
        self.wanderer.write_resources_of_service_in_region(service_name='ec2')
        self.wanderer.write_resources_of_service_in_region(service_name='s3')

        self.assert_resource_exists(
            region='eu-west-2',
            service='ec2',
            resource_type='instance',
            attributes_dict={
                'vpc_id': ANY,
                'subnet_id': ANY,
                'instance_id': ANY
            }
        )
        self.assert_resource_not_exists(
            region='eu-west-2',
            service='s3',
            resource_type='bucket',
            attributes_dict={
                'name': 'test-eu-west-2'
            }
        )
        self.assert_resource_not_exists(
            region='us-east-1',
            service='iam',
            resource_type='role',
            attributes_dict={
                'role_name': 'test-role',
                'path': '/'
            },
        )

    def test_write_resources_of_service_specify_region(self):
        self.wanderer.write_resources_of_service_in_region(service_name='ec2', region_name='us-east-1')
        self.wanderer.write_resources_of_service_in_region(service_name='s3', region_name='us-east-1')
        self.wanderer.write_resources_of_service_in_region(service_name='iam', region_name='us-east-1')

        self.assert_resource_exists(
            region='us-east-1',
            service='ec2',
            resource_type='instance',
            attributes_dict={
                'vpc_id': ANY,
                'subnet_id': ANY,
                'instance_id': ANY
            }
        )
        self.assert_resource_exists(
            region='us-east-1',
            service='s3',
            resource_type='bucket',
            attributes_dict={
                'name': 'test-us-east-1'
            }
        )
        self.assert_resource_exists(
            region='us-east-1',
            service='iam',
            resource_type='role',
            attributes_dict={
                'role_name': 'test-role',
                'path': '/'
            },
            secondary_attributes_dict={
                "[].PolicyNames[0]": ['test-role-policy'],
                "[].AttachedPolicies[0].PolicyName": ['APIGatewayServiceRolePolicy']
            }
        )

    def test_write_resources_of_type_in_region_default_region(self):
        self.wanderer.write_resources_of_type_in_region(service_name='s3', resource_type='bucket')
        self.wanderer.write_resources_of_type_in_region(service_name='ec2', resource_type='instance')
        self.wanderer.write_resources_of_type_in_region(service_name='iam', resource_type='role')

        self.assert_resource_exists(
            region='eu-west-2',
            service='ec2',
            resource_type='instance',
            attributes_dict={
                'vpc_id': ANY,
                'subnet_id': ANY,
                'instance_id': ANY
            }
        )
        self.assert_resource_not_exists(
            region='eu-west-2',
            service='s3',
            resource_type='bucket',
            attributes_dict={
                'name': 'test-eu-west-2'
            }
        )
        self.assert_resource_not_exists(
            region='us-east-1',
            service='iam',
            resource_type='role',
            attributes_dict={
                'role_name': 'test-role',
                'path': '/'
            },
        )

    def test_write_resources_of_type_in_region_specify_region(self):
        self.wanderer.write_resources_of_type_in_region(
            service_name='s3', resource_type='bucket', region_name='us-east-1')
        self.wanderer.write_resources_of_type_in_region(
            service_name='ec2', resource_type='instance', region_name='us-east-1')
        self.wanderer.write_resources_of_type_in_region(
            service_name='iam', resource_type='role', region_name='us-east-1')

        self.assert_resource_exists(
            region='us-east-1',
            service='ec2',
            resource_type='instance',
            attributes_dict={
                'vpc_id': ANY,
                'subnet_id': ANY,
                'instance_id': ANY
            }
        )
        self.assert_resource_exists(
            region='us-east-1',
            service='s3',
            resource_type='bucket',
            attributes_dict={
                'name': 'test-us-east-1'
            }
        )
        self.assert_resource_exists(
            region='us-east-1',
            service='iam',
            resource_type='role',
            attributes_dict={
                'role_name': 'test-role',
                'path': '/'
            },
            secondary_attributes_dict={
                "[].PolicyNames[0]": ['test-role-policy'],
                "[].AttachedPolicies[0].PolicyName": ['APIGatewayServiceRolePolicy']
            }
        )

    def assert_resource_exists(self, *args, **kwargs):
        results, resources = self.resource_exists(*args, **kwargs)
        assert len(results) > 0
        for comparison in results:
            self.assertTrue(
                comparison[0],
                f"{comparison[2]} was not found at '{comparison[1]}' in any of {resources}"
            )

    def assert_resource_not_exists(self, *args, **kwargs):
        results, resources = self.resource_exists(*args, **kwargs)
        assert all(x[0] for x in results)

    def resource_exists(self, region, service, resource_type, attributes_dict, secondary_attributes_dict=None):
        secondary_attributes_dict = secondary_attributes_dict or {}
        resources = list(self.storage_connector.read_resources(
            region=region,
            service=service,
            resource_type=resource_type
        ))

        matches = []
        for resource in resources:
            resource.load()
            # No resource should have the ResponseMetadata attribute recorded.
            self.assertRaises(AttributeError, getattr, resource, 'response_metadata')
            for attribute, value in attributes_dict.items():
                result = False
                try:
                    result = getattr(resource, attribute) == value
                except AttributeError:
                    pass
                matches.append((result, resource.urn, attribute, value))
            for jmes_path, value in secondary_attributes_dict.items():
                result = False
                matches.append((
                    resource.get_secondary_attribute(jmes_path=jmes_path) == value,
                    jmes_path,
                    value
                ))
        return matches, resources
