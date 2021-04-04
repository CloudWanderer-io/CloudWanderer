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
        results = self.resources_directive.get_boto3_resources()

        assert (
            results
            == """* :doc:`CloudFormation <resource_properties/cloudformation>`
    * :class:`Stacks<cloudformation.stack>`
* :doc:`CloudWatch <resource_properties/cloudwatch>`
    * :class:`Alarms<cloudwatch.alarm>`
    * :class:`Metrics<cloudwatch.metric>`
* :doc:`DynamoDB <resource_properties/dynamodb>`
    * :class:`Tables<dynamodb.table>`
* :doc:`EC2 <resource_properties/ec2>`
    * :class:`ClassicAddresses<ec2.classic_address>`
    * :class:`DhcpOptionsSets<ec2.dhcp_options>`
    * :class:`Images<ec2.image>`
    * :class:`Instances<ec2.instance>`
    * :class:`InternetGateways<ec2.internet_gateway>`
    * :class:`NetworkAcls<ec2.network_acl>`
    * :class:`NetworkInterfaces<ec2.network_interface>`
    * :class:`PlacementGroups<ec2.placement_group>`
    * :class:`RouteTables<ec2.route_table>`
    * :class:`SecurityGroups<ec2.security_group>`
    * :class:`Snapshots<ec2.snapshot>`
    * :class:`Subnets<ec2.subnet>`
    * :class:`Volumes<ec2.volume>`
    * :class:`VpcAddresses<ec2.vpc_address>`
    * :class:`VpcPeeringConnections<ec2.vpc_peering_connection>`
    * :class:`Vpcs<ec2.vpc>`
* :doc:`Glacier <resource_properties/glacier>`
    * :class:`Vaults<glacier.vault>`
* :doc:`IAM <resource_properties/iam>`
    * :class:`Groups<iam.group>`
         * :class:`Policies<iam.group.group_policy>`
    * :class:`InstanceProfiles<iam.instance_profile>`
    * :class:`Policies<iam.policy>`
         * :class:`Versions<iam.policy.policy_version>`
    * :class:`Roles<iam.role>`
         * :class:`Policies<iam.role.role_policy>`
    * :class:`SamlProviders<iam.saml_provider>`
    * :class:`ServerCertificates<iam.server_certificate>`
    * :class:`Users<iam.user>`
         * :class:`AccessKeys<iam.user.access_key>`
         * :class:`MfaDevices<iam.user.mfa_device>`
         * :class:`Policies<iam.user.user_policy>`
         * :class:`SigningCertificates<iam.user.signing_certificate>`
    * :class:`VirtualMfaDevices<iam.virtual_mfa_device>`
* :doc:`OpsWorks <resource_properties/opsworks>`
    * :class:`Stacks<opsworks.stack>`
* :doc:`S3 <resource_properties/s3>`
    * :class:`Buckets<s3.bucket>`
* :doc:`SNS <resource_properties/sns>`
    * :class:`PlatformApplications<sns.platform_application>`
    * :class:`Subscriptions<sns.subscription>`
    * :class:`Topics<sns.topic>`
* :doc:`SQS <resource_properties/sqs>`
    * :class:`Queues<sqs.queue>`
"""
        )
