import unittest

from cloudwanderer import URN

from ..helpers import CloudWandererCalls, ExpectedCall, MultipleResourceScenario, NoMotoMock, SingleResourceScenario


class TestCustomerGateways(NoMotoMock, unittest.TestCase):

    customer_gateway_payload = {
        "BgpAsn": "65000",
        "CustomerGatewayId": "cgw-11111111111111111",
        "IpAddress": "1.1.1.1",
        "State": "available",
        "Type": "ipsec.1",
        "Tags": [],
    }

    mock = {
        "ec2": {
            "describe_customer_gateways.return_value": {"CustomerGateways": [customer_gateway_payload]},
        }
    }

    single_resource_scenarios = [
        SingleResourceScenario(
            urn=URN.from_string("urn:aws:123456789012:eu-west-2:ec2:customer_gateway:vpn-11111111111111111"),
            expected_results=[customer_gateway_payload],
            expected_call=ExpectedCall(
                "ec2", "describe_customer_gateways", [], {"CustomerGatewayIds": ["vpn-11111111111111111"]}
            ),
        )
    ]
    multiple_resource_scenarios = [
        MultipleResourceScenario(
            arguments=CloudWandererCalls(
                regions=["eu-west-2"], service_names=["ec2"], resource_types=["customer_gateway"]
            ),
            expected_results=[customer_gateway_payload],
        )
    ]
