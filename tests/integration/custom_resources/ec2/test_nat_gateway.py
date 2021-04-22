import unittest

from cloudwanderer import URN

from ..helpers import CloudWandererCalls, ExpectedCall, MultipleResourceScenario, NoMotoMock, SingleResourceScenario


class TestNatGateways(NoMotoMock, unittest.TestCase):

    nat_gateway_payload = {
        "CreateTime": "2021-04-13T09:39:49.000Z",
        "NatGatewayAddresses": [
            {
                "AllocationId": "eipalloc-11111111111111111",
                "NetworkInterfaceId": "eni-11111111111111111",
                "PrivateIp": "10.10.10.78",
            }
        ],
        "NatGatewayId": "nat-11111111111111111",
        "State": "pending",
        "SubnetId": "subnet-11111111",
        "VpcId": "vpc-11111111",
        "Tags": [{"Key": "Name", "Value": "test-gateway"}],
    }

    mock = {
        "ec2": {
            "describe_nat_gateways.return_value": {"NatGateways": [nat_gateway_payload]},
        }
    }

    single_resource_scenarios = [
        SingleResourceScenario(
            urn=URN.from_string("urn:aws:123456789012:eu-west-2:ec2:nat_gateway:nat-11111111111111111"),
            expected_results=[nat_gateway_payload],
            expected_call=ExpectedCall(
                "ec2", "describe_nat_gateways", [], {"NatGatewayIds": ["nat-11111111111111111"]}
            ),
        )
    ]
    multiple_resource_scenarios = [
        MultipleResourceScenario(
            arguments=CloudWandererCalls(regions=["eu-west-2"], service_names=["ec2"], resource_types=["nat_gateway"]),
            expected_results=[nat_gateway_payload],
        )
    ]
