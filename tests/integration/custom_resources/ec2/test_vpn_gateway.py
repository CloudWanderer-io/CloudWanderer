import unittest

from cloudwanderer import URN

from ..helpers import CloudWandererCalls, ExpectedCall, MultipleResourceScenario, NoMotoMock, SingleResourceScenario


class TestVpnGateways(NoMotoMock, unittest.TestCase):

    vpn_gateway_payload = {
        "State": "available",
        "Type": "ipsec.1",
        "VpcAttachments": [],
        "VpnGatewayId": "vgw-11111111111111111",
        "AmazonSideAsn": 64512,
        "Tags": [{"Key": "Name", "Value": "test-vpn-gateway"}],
    }

    mock = {
        "ec2": {
            "describe_vpn_gateways.return_value": {"VpnGateways": [vpn_gateway_payload]},
        }
    }

    single_resource_scenarios = [
        SingleResourceScenario(
            urn=URN.from_string("urn:aws:123456789012:eu-west-2:ec2:vpn_gateway:vpn-11111111111111111"),
            expected_results=[vpn_gateway_payload],
            expected_call=ExpectedCall(
                "ec2", "describe_vpn_gateways", [], {"VpnGatewayIds": ["vpn-11111111111111111"]}
            ),
        )
    ]
    multiple_resource_scenarios = [
        MultipleResourceScenario(
            arguments=CloudWandererCalls(regions=["eu-west-2"], service_names=["ec2"], resource_types=["vpn_gateway"]),
            expected_results=[vpn_gateway_payload],
        )
    ]
