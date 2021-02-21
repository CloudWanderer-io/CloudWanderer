import logging
import unittest

import boto3
import botocore

from cloudwanderer import URN, CloudWanderer
from cloudwanderer.aws_interface import CloudWandererAWSInterface
from cloudwanderer.cloud_wanderer import CloudWandererConcurrentWriteThreadResult
from cloudwanderer.storage_connectors import DynamoDbConnector


class TestFunctional(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logging.basicConfig(level="debug")

    def setUp(self):
        self.storage_connector = DynamoDbConnector(
            endpoint_url="http://localhost:8000",
            client_args={
                "config": botocore.config.Config(
                    max_pool_connections=100,
                )
            },
        )
        self.storage_connector.init()
        self.wanderer = CloudWanderer(storage_connectors=[self.storage_connector])

    # The _a_ in this test name ensures this test runs first so that subsequent read tests have values to read.
    def test_a_write_resources(self):
        thread_results = self.wanderer.write_resources_concurrently(
            exclude_resources=["ec2:image", "ec2:snapshot", "iam:policy"],
            concurrency=128,
            cloud_interface_generator=lambda: CloudWandererAWSInterface(boto3_session=boto3.session.Session()),
            storage_connector_generator=lambda: [
                DynamoDbConnector(
                    endpoint_url="http://localhost:8000",
                    client_args={
                        "config": botocore.config.Config(
                            max_pool_connections=100,
                        )
                    },
                ),
            ],
        )
        for result in thread_results:
            assert isinstance(result, CloudWandererConcurrentWriteThreadResult)

    def test_write_resources_in_region(self):
        """It is sufficient for this not to throw an exception."""
        self.wanderer.write_resources(
            regions=["eu-west-1"], exclude_resources=["ec2:image", "ec2:snapshot", "iam:policy"]
        )

    def test_write_custom_resource_definition(self):
        """It is sufficient for this not to throw an exception."""
        self.wanderer.write_resources(service_names=["lambda"])

    def test_write_single_resource(self):
        urn = URN(
            account_id=self.wanderer.cloud_interface.account_id,
            region="eu-west-2",
            service="ec2",
            resource_type="vpc",
            resource_id="vpc-d52bc4bc",
        )
        self.wanderer.write_resource(urn=urn)

    def test_read_all(self):
        results = list(self.storage_connector.read_all())
        assert len(results) > 0
        for result in results:
            assert isinstance(result, dict)

    def test_read_resource_of_type(self):
        vpcs = list(self.storage_connector.read_resources(service="ec2", resource_type="vpc"))
        vpcs[0].load()
        assert len(vpcs) > 0
        assert isinstance(vpcs[0].get_secondary_attribute(name="vpc_enable_dns_support")[0], dict)
        assert isinstance(vpcs[0].is_default, bool)

    def test_read_all_resources_in_account(self):
        resources = list(self.storage_connector.read_resources(account_id=self.wanderer.cloud_interface.account_id))
        service_resource_types = set()
        for resource in resources:
            service_resource_types.add(f"{resource.urn.service}:{resource.urn.resource_type}")

        assert {
            "apigateway:rest_api",
            "cloudformation:stack",
            "cloudwatch:alarm",
            "cloudwatch:metric",
            "dynamodb:table",
            "ec2:dhcp_options",
            "ec2:internet_gateway",
            "ec2:network_acl",
            "ec2:route_table",
            "ec2:security_group",
            "ec2:subnet",
            "ec2:vpc",
            "iam:group",
            "iam:role",
            "iam:role_policy",
            "iam:user",
            "iam:virtual_mfa_device",
            "lambda:function",
            "s3:bucket",
            "secretsmanager:secret",
            "sns:subscription",
            "sns:topic",
        }.issubset(service_resource_types)

    def test_read_resource_of_type_in_account(self):
        vpc = next(
            self.storage_connector.read_resources(
                service="ec2", resource_type="vpc", account_id=self.wanderer.cloud_interface.account_id
            )
        )
        vpc.load()
        assert isinstance(vpc.get_secondary_attribute(name="vpc_enable_dns_support")[0], dict)
        assert isinstance(vpc.is_default, bool)

    def test_documentation_resource_example(self):
        """It's sufficient for this not to throw an exception."""
        storage_connector = self.storage_connector
        resources = storage_connector.read_resources(service="ec2", resource_type="vpc")
        for resource in resources:
            resource.load()
            print(resource.urn)
            print(resource.cidr_block)
            print(resource.cidr_block_association_set)
            print(resource.dhcp_options_id)
            print(resource.instance_tenancy)
            print(resource.ipv6_cidr_block_association_set)
            print(resource.is_default)
            print(resource.owner_id)
            print(resource.state)
            print(resource.tags)
            print(resource.vpc_id)

    def test_documentation_secondary_attribute_example(self):
        """It's sufficient for this not to throw an exception."""
        storage_connector = self.storage_connector
        resources = storage_connector.read_resources(service="ec2", resource_type="vpc")
        for resource in resources:
            resource.get_secondary_attribute(name="vpc_enable_dns_support")

    def test_documentation_subresource_example(self):
        """It's sufficient for this not to throw an exception."""
        storage_connector = self.storage_connector
        resources = storage_connector.read_resources(service="iam", resource_type="role")
        for resource in resources:
            resource.load()
            print(resource.urn)
            print(resource.arn)
            print(resource.assume_role_policy_document)
            print(resource.create_date)
            print(resource.description)
            print(resource.max_session_duration)
            print(resource.path)
            print(resource.permissions_boundary)
            print(resource.role_id)
            print(resource.role_last_used)
            print(resource.role_name)
            print(resource.tags)
