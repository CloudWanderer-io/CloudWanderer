import logging
import unittest

import boto3
import botocore

from cloudwanderer import URN, CloudWanderer
from cloudwanderer.aws_interface import CloudWandererAWSInterface
from cloudwanderer.aws_interface.session import CloudWandererBoto3Session
from cloudwanderer.cloud_wanderer import CloudWandererConcurrentWriteThreadResult
from cloudwanderer.exceptions import BadUrnRegionError, BadUrnSubResourceError, UnsupportedResourceTypeError
from cloudwanderer.models import ServiceResourceType
from cloudwanderer.storage_connectors import GremlinStorageConnector


class TestFunctional(unittest.TestCase):
    identifier_mapping = {
        "layer_version:version": 1,
        "policy:arn": "arn:aws:iam::1234567890:policy/APIGatewayLambdaExecPolicy",
        "policy_version:arn": "arn:aws:iam::1234567890:policy/APIGatewayLambdaExecPolicy",
    }
    resources_not_supporting_load = [
        "lambda:layer",
        "iam:virtual_mfa_device",
        "iam:mfa_device",
        "iam:signing_certificate",
        "ec2:route",
        "iam:access_key",
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logging.basicConfig(level="debug")

    def setUp(self):
        self.storage_connector = GremlinStorageConnector(endpoint_url="wss://cloudwanderertest.cluster-cj4mow8tlcit.eu-west-1.neptune.amazonaws.com:8182", pool_size=1, max_workers=1)
        self.storage_connector.init()
        self.wanderer = CloudWanderer(storage_connectors=[self.storage_connector])

    # The _a_ in this test name ensures this test runs first so that subsequent read tests have values to read.
    # def test_a_write_resources_without_concurrency(self):
    #     """It is sufficient for this not to throw an exception."""
    #     self.wanderer.write_resources()

    def test_write_resources_in_region(self):
        """It is sufficient for this not to throw an exception."""
        self.wanderer.write_resources(regions=["eu-west-1"], exclude_resources=[])

    def test_write_resource_type(self):
        """It is sufficient for this not to throw an exception."""
        self.wanderer.write_resources(regions=["us-east-1"], service_resource_types=[ServiceResourceType("ec2", "vpc")])

    def test_write_custom_resource_definition(self):
        """It is sufficient for this not to throw an exception."""
        self.wanderer.write_resources(service_resource_types=[ServiceResourceType("iam", "role")])

    def test_write_single_non_existent_resource_of_every_type(self):

        for resource in self.wanderer.cloud_interface.get_all_empty_resources():
            logging.info("Testing %s %s", resource.service_name, resource.resource_type)
            identifiers = resource.meta.resource_model.identifiers
            args = [
                self.identifier_mapping.get(
                    f"{resource.resource_type}{identifier.name}test1111111",
                    f"{resource.resource_type}{identifier.name}test1111111",
                )
                for identifier in identifiers
            ]

            self._write_resource_with_fake_id(resource.service_name, resource.resource_type, args)

    def test_write_single_non_existent_dependent_resource_of_every_type(self):

        for empty_resource in self.wanderer.cloud_interface.get_all_empty_resources(include_dependent_resource=True):
            if not empty_resource.is_dependent_resource:
                continue
            resource_type = empty_resource.resource_type
            identifiers = empty_resource.meta.resource_model.identifiers
            args = [
                self.identifier_mapping.get(f"{resource_type}:{identifier.name}", f"{resource_type}:{identifier.name}")
                for identifier in identifiers
            ]
            logging.info("Testing %s %s", empty_resource.service_name, resource_type)
            self._write_resource_with_fake_id(empty_resource.service_name, resource_type, args)

    def _write_resource_with_fake_id(self, service_name, resource_type, args) -> None:
        urn = URN(
            account_id=self.wanderer.cloud_interface.cloudwanderer_boto3_session.get_account_id(),
            region="us-east-1",
            service=service_name,
            resource_type=resource_type,
            resource_id_parts=args,
        )
        try:
            self.wanderer.write_resource(urn=urn)
        except UnsupportedResourceTypeError:
            if f"{service_name}:{resource_type}" in self.resources_not_supporting_load:
                return
            raise

    def test_write_single_resource_of_every_found_type(self):
        for empty_resource in self.wanderer.cloud_interface.get_all_empty_resources():
            logging.info(f"service={empty_resource.service_name}, resource_type={empty_resource.resource_type}")
            try:
                resource = next(
                    self.storage_connector.read_resources(
                        cloud_name="aws",
                        service=empty_resource.service_name,
                        resource_type=empty_resource.resource_type,
                    )
                )
            except StopIteration:
                logging.info(
                    "No %s %s resources were found, skipping testing write_resource for this type",
                    empty_resource.service_name,
                    empty_resource.resource_type,
                )
                continue
            logging.info("Found %s, testing write_resource", resource.urn)
            try:
                self.wanderer.write_resource(urn=resource.urn)
            except UnsupportedResourceTypeError as ex:
                if (
                    f"{empty_resource.service_name}:{empty_resource.resource_type}"
                    in self.resources_not_supporting_load
                ):
                    continue
                raise ex
        for storage_connector in self.wanderer.storage_connectors:
            storage_connector.close()

    # def test_read_all(self):
    #     results = list(self.storage_connector.read_all())
    #     assert len(results) > 0
    #     for result in results:
    #         assert isinstance(result, dict)

    def test_read_resource_of_type(self):
        vpcs = [
            resource
            for resource in self.storage_connector.read_resources(cloud_name="aws", service="ec2", resource_type="vpc")
            if not resource.urn.is_partial
        ]
        assert len(vpcs) > 0
        assert all(isinstance(x, str) for x in vpcs[0].cloudwanderer_metadata.resource_data.values())
        # TODO: Add secondary attributes
        # assert isinstance(vpcs[0].get_secondary_attribute(name="vpc_enable_dns_support")[0], dict)
        logging.info(vpcs[0])
        assert vpcs[0].is_default in ['True', 'False']

    # def test_read_all_resources_in_account(self):
    #     resources = list(self.storage_connector.read_resources(account_id=self.wanderer.cloud_interface.account_id))
    #     service_resource_types = set()
    #     for resource in resources:
    #         service_resource_types.add(f"{resource.urn.service}:{resource.urn.resource_type}")

    #     expected_resource_types = {
    #         "apigateway:rest_api",
    #         "cloudformation:stack",
    #         "cloudwatch:alarm",
    #         "cloudwatch:metric",
    #         "dynamodb:table",
    #         "ec2:dhcp_options",
    #         "ec2:internet_gateway",
    #         "ec2:network_acl",
    #         "ec2:route_table",
    #         "ec2:security_group",
    #         "ec2:subnet",
    #         "ec2:vpc",
    #         "iam:group",
    #         "iam:role",
    #         "iam:role_policy",
    #         "iam:user",
    #         "lambda:function",
    #         "s3:bucket",
    #         "secretsmanager:secret",
    #         "sns:subscription",
    #         "sns:topic",
    #     }
    #     for resource_type in expected_resource_types:
    #         assert resource_type in service_resource_types

    # def test_read_resource_of_type_in_account(self):
    #     vpc = next(
    #         self.storage_connector.read_resources(
    #             service="ec2", resource_type="vpc", account_id=self.wanderer.cloud_interface.account_id
    #         )
    #     )
    #     vpc.load()
    #     assert isinstance(vpc.get_secondary_attribute(name="vpc_enable_dns_support")[0], dict)
    #     assert isinstance(vpc.is_default, bool)

    # def test_documentation_resource_example(self):
    #     """It's sufficient for this not to throw an exception."""
    #     storage_connector = self.storage_connector
    #     resources = storage_connector.read_resources(service="ec2", resource_type="vpc")
    #     for resource in resources:
    #         resource.load()
    #         print(resource.urn)
    #         print(resource.cidr_block)
    #         print(resource.cidr_block_association_set)
    #         print(resource.dhcp_options_id)
    #         print(resource.instance_tenancy)
    #         print(resource.ipv6_cidr_block_association_set)
    #         print(resource.is_default)
    #         print(resource.owner_id)
    #         print(resource.state)
    #         print(resource.tags)
    #         print(resource.vpc_id)

    # def test_documentation_secondary_attribute_example(self):
    #     """It's sufficient for this not to throw an exception."""
    #     storage_connector = self.storage_connector
    #     resources = storage_connector.read_resources(service="ec2", resource_type="vpc")
    #     for resource in resources:
    #         resource.get_secondary_attribute(name="vpc_enable_dns_support")

    # def test_documentation_subresource_example(self):
    #     """It's sufficient for this not to throw an exception."""
    #     storage_connector = self.storage_connector
    #     resources = storage_connector.read_resources(service="iam", resource_type="role")
    #     for resource in resources:
    #         resource.load()
    #         print(resource.urn)
    #         print(resource.arn)
    #         print(resource.assume_role_policy_document)
    #         print(resource.create_date)
    #         print(resource.description)
    #         print(resource.max_session_duration)
    #         print(resource.path)
    #         print(resource.permissions_boundary)
    #         print(resource.role_id)
    #         print(resource.role_last_used)
    #         print(resource.role_name)
    #         print(resource.tags)

    def test_write_single_nonexistent_resource(self):
        self._write_resource_with_fake_id(service_name="s3", resource_type="bucket", args=["testbucket"])
