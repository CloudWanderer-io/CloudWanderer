import unittest
from unittest.mock import MagicMock, patch

import boto3

from cloudwanderer import URN, CloudWanderer
from cloudwanderer.aws_interface import CloudWandererAWSInterface
from cloudwanderer.storage_connectors import MemoryStorageConnector

from ..helpers import DEFAULT_SESSION, GenericAssertionHelpers

FUNCTION_PAYLOAD = {
    "FunctionName": "TestFunction",
    "FunctionArn": "arn:aws:lambda:eu-west-2:012345678912:function:TestFunction",
    "Runtime": "nodejs4.3",
    "Role": "arn:aws:iam::012345678912:role/TestRole",
    "Handler": "lambda.handler",
    "CodeSize": 4393,
    "Description": "",
    "Timeout": 6,
    "MemorySize": 1024,
    "LastModified": "2018-12-10T19:54:05.810+0000",
    "CodeSha256": "ROZQR3eU8ctjQ9yO7rNCC4po8W4/oF1dzR7Wq/d0yEw=",
    "Version": "$LATEST",
    "Environment": {"Variables": {}},
    "TracingConfig": {"Mode": "PassThrough"},
    "RevisionId": "6f5ac744-5971-4589-a695-51db02a283c4",
    "PackageType": "Zip",
}
FUNCTION_RESOURCE = {
    "FunctionName": "TestFunction",
    "FunctionArn": "arn:aws:lambda:eu-west-2:012345678912:function:TestFunction",
    "Runtime": "nodejs4.3",
    "Role": "arn:aws:iam::012345678912:role/TestRole",
    "Handler": "lambda.handler",
    "CodeSize": 4393,
    "Description": None,
    "Timeout": 6,
    "MemorySize": 1024,
    "CodeSha256": "ROZQR3eU8ctjQ9yO7rNCC4po8W4/oF1dzR7Wq/d0yEw=",
    "TracingConfig": {"Mode": "PassThrough"},
    "RevisionId": "6f5ac744-5971-4589-a695-51db02a283c4",
}


class TestLambdaResources(unittest.TestCase, GenericAssertionHelpers):
    def setUp(self):
        self.boto3_client_mock = MagicMock()
        add_caller_identity(self.boto3_client_mock)
        add_lambda_mock(self.boto3_client_mock)
        self.session_patch = patch("boto3.session.Session.client", new=self.boto3_client_mock)
        self.session_patch.start()
        self.storage_connector = MemoryStorageConnector()
        self.wanderer = CloudWanderer(
            storage_connectors=[self.storage_connector],
            cloud_interface=CloudWandererAWSInterface(DEFAULT_SESSION),
        )

    def tearDown(self) -> None:
        self.session_patch.stop()

    def test_write_function(self):

        self.wanderer.write_resource(
            urn=URN(
                account_id=self.wanderer.cloud_interface.account_id,
                region="eu-west-2",
                service="lambda",
                resource_type="function",
                resource_id="TestFunction",
            )
        )

        self.assert_dictionary_overlap(
            self.storage_connector.read_all(),
            [FUNCTION_RESOURCE],
        )

    def test_write_functions(self):

        self.wanderer.write_resources(regions=["eu-west-2"], service_names=["lambda"])
        self.assert_dictionary_overlap(
            self.storage_connector.read_all(),
            [FUNCTION_RESOURCE],
        )


def add_caller_identity(mock):
    mock.return_value.get_caller_identity.return_value = {"Account": "123456789012"}


def add_lambda_mock(mock):
    mock.return_value.meta = boto3.client("lambda").meta
    mock.return_value.get_function.return_value = {"Configuration": FUNCTION_PAYLOAD}
    mock.return_value.get_paginator.return_value.paginate.return_value = [
        {
            "ResponseMetadata": {
                "RequestId": "9aecdaee-943b-4c7f-906e-3f485269e951",
                "HTTPStatusCode": 200,
                "HTTPHeaders": {
                    "date": "Sun, 21 Feb 2021 15:07:55 GMT",
                    "content-type": "application/json",
                    "content-length": "15683",
                    "connection": "keep-alive",
                    "x-amzn-requestid": "9aecdaee-943b-4c7f-906e-3f485269e951",
                },
                "RetryAttempts": 0,
            },
            "Functions": [FUNCTION_PAYLOAD],
        }
    ]
