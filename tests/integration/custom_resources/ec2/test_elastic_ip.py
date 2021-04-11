import unittest

from cloudwanderer import URN

from ..helpers import CloudWandererCalls, ExpectedCall, MultipleResourceScenario, NoMotoMock, SingleResourceScenario


class TestElasticIPAddresses(NoMotoMock, unittest.TestCase):

    elastic_ip_payload = {
        "PublicIp": "1.1.1.1",
        "AllocationId": "eipalloc-11111111111111111",
        "Domain": "vpc",
        "PublicIpv4Pool": "amazon",
        "NetworkBorderGroup": "eu-west-1",
    }

    mock = {
        "ec2": {
            "describe_addresses.return_value": {"Addresses": [elastic_ip_payload]},
        }
    }

    single_resource_scenarios = [
        SingleResourceScenario(
            urn=URN.from_string("urn:aws:123456789012:eu-west-2:ec2:elastic_ip:eipalloc-11111111111111111"),
            expected_results=[elastic_ip_payload],
            expected_call=ExpectedCall(
                "ec2", "describe_addresses", [], {"AllocationId": ["eipalloc-11111111111111111"]}
            ),
        )
    ]
    multiple_resource_scenarios = [
        MultipleResourceScenario(
            arguments=CloudWandererCalls(regions=["eu-west-2"], service_names=["ec2"], resource_types=["elastic_ip"]),
            expected_results=[elastic_ip_payload],
        )
    ]
