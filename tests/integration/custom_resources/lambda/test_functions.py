import unittest

from cloudwanderer import URN

from ..helpers import CloudWandererCalls, ExpectedCall, MultipleResourceScenario, NoMotoMock, SingleResourceScenario


class TestLambdaFunctions(NoMotoMock, unittest.TestCase):
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
            "list_functions.return_value": {
                "Functions": [function_payload],
            },
        }
    }

    single_resource_scenarios = [
        SingleResourceScenario(
            urn=URN.from_string("urn:aws:123456789012:eu-west-2:lambda:function:TestFunction"),
            expected_results=[expected_result],
            expected_call=ExpectedCall("lambda", "get_function", [], {"FunctionName": "TestFunction"}),
        )
    ]
    multiple_resource_scenarios = [
        MultipleResourceScenario(
            arguments=CloudWandererCalls(regions=["eu-west-2"], service_names=["lambda"]),
            expected_results=[expected_result],
        )
    ]
