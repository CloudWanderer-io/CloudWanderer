import unittest

from supported_resources import Boto3ResourcesDirective

pytest_plugins = "sphinx.testing.fixtures"


class TestCloudWandererResourcesDirective(unittest.TestCase):
    def setUp(self) -> None:
        self.resources_directive = Boto3ResourcesDirective(
            name="",
            arguments={},
            options=None,
            content=None,
            lineno=1,
            content_offset=None,
            block_text="",
            state=None,
            state_machine=None,
        )

    def test_get_boto3_resources(self):
        results = [str(x) for x in self.resources_directive.get_boto3_resources()]

        expected_results = [
            "<list_item>CloudFormation<bullet_list><list_item>Stacks</list_item></bullet_list></list_item>",
            "<list_item>CloudWatch<bullet_list><list_item>Alarms</list_item><list_item>Metrics</list_item></bullet_list></list_item>",
            "<list_item>DynamoDB<bullet_list><list_item>Tables</list_item></bullet_list></list_item>",
            "<list_item>EC2<bullet_list><list_item>ClassicAddresses</list_item><list_item>DhcpOptionsSets</list_item><list_item>Images</list_item><list_item>Instances</list_item><list_item>InternetGateways</list_item><list_item>KeyPairs</list_item><list_item>NetworkAcls</list_item><list_item>NetworkInterfaces</list_item><list_item>PlacementGroups</list_item><list_item>RouteTables</list_item><list_item>SecurityGroups</list_item><list_item>Snapshots</list_item><list_item>Subnets</list_item><list_item>Volumes</list_item><list_item>VpcAddresses</list_item><list_item>VpcPeeringConnections</list_item><list_item>Vpcs</list_item></bullet_list></list_item>",
            "<list_item>Glacier<bullet_list><list_item>Vaults</list_item></bullet_list></list_item>",
            "<list_item>IAM<bullet_list><list_item>Groups</list_item><list_item>InstanceProfiles</list_item><list_item>Policies</list_item><list_item>Roles</list_item><list_item>SamlProviders</list_item><list_item>ServerCertificates</list_item><list_item>Users</list_item><list_item>VirtualMfaDevices</list_item></bullet_list></list_item>",
            "<list_item>OpsWorks<bullet_list><list_item>Stacks</list_item></bullet_list></list_item>",
            "<list_item>S3<bullet_list><list_item>Buckets</list_item></bullet_list></list_item>",
            "<list_item>SNS<bullet_list><list_item>PlatformApplications</list_item><list_item>Subscriptions</list_item><list_item>Topics</list_item></bullet_list></list_item>",
            "<list_item>SQS<bullet_list><list_item>Queues</list_item></bullet_list></list_item>",
        ]
        for expected_result in expected_results:
            assert expected_result in results
