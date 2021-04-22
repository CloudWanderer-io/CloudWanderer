import unittest

from cloudwanderer import URN

from ..helpers import CloudWandererCalls, ExpectedCall, MultipleResourceScenario, NoMotoMock, SingleResourceScenario


class TestEgressOnlyInternetGateways(NoMotoMock, unittest.TestCase):

    egress_only_internet_gateway_payload = {
        "Attachments": [{"State": "attached", "VpcId": "vpc-11111111"}],
        "EgressOnlyInternetGatewayId": "eigw-11111111111111111",
        "Tags": [{"Key": "Name", "Value": "test-eigw"}],
    }

    mock = {
        "ec2": {
            "describe_egress_only_internet_gateways.return_value": {
                "EgressOnlyInternetGateways": [egress_only_internet_gateway_payload]
            },
        }
    }

    single_resource_scenarios = [
        SingleResourceScenario(
            urn=URN.from_string(
                "urn:aws:123456789012:eu-west-2:ec2:egress_only_internet_gateway:eigw-11111111111111111"
            ),
            expected_results=[egress_only_internet_gateway_payload],
            expected_call=ExpectedCall(
                "ec2",
                "describe_egress_only_internet_gateways",
                [],
                {"EgressOnlyInternetGatewayIds": ["eigw-11111111111111111"]},
            ),
        )
    ]
    multiple_resource_scenarios = [
        MultipleResourceScenario(
            arguments=CloudWandererCalls(
                regions=["eu-west-2"], service_names=["ec2"], resource_types=["egress_only_internet_gateway"]
            ),
            expected_results=[egress_only_internet_gateway_payload],
        )
    ]
