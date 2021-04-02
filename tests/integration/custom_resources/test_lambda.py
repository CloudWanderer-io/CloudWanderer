import unittest

from cloudwanderer import URN

from .helpers import CloudWandererCalls, MultipleResourceScenario, NoMotoMock, SingleResourceScenario


class TestLambdaResources(NoMotoMock, unittest.TestCase):
    expected_result = {
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
    function_payload = {
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

    mock = {
        "lambda": {
            "get_function.return_value": {"Configuration": function_payload},
            "get_paginator.return_value.paginate.return_value": [
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
                    "Functions": [function_payload],
                }
            ],
        }
    }

    single_resource_scenarios = [
        SingleResourceScenario(
            urn=URN.from_string("urn:aws:123456789012:eu-west-2:lambda:function:TestFunction"),
            expected_results=[expected_result],
        )
    ]
    multiple_resource_scenarios = [
        MultipleResourceScenario(
            arguments=CloudWandererCalls(regions=["eu-west-2"], service_names=["lambda"]),
            expected_results=[expected_result],
        )
    ]
