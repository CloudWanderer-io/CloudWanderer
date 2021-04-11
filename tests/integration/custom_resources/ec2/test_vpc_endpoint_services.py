import unittest

from cloudwanderer import URN

from ..helpers import CloudWandererCalls, ExpectedCall, MultipleResourceScenario, NoMotoMock, SingleResourceScenario


class TestVPCEndpointServices(NoMotoMock, unittest.TestCase):

    vpc_endpoint_service_payload = {
        "ServiceName": "com.amazonaws.vpce.eu-west-1.vpce-svc-11111111111111111",
        "ServiceId": "vpce-svc-11111111111111111",
        "ServiceType": [{"ServiceType": "Interface"}],
        "AvailabilityZones": ["eu-west-1a"],
        "Owner": "111111111111",
        "BaseEndpointDnsNames": ["vpce-svc-11111111111111111.eu-west-1.vpce.amazonaws.com"],
        "VpcEndpointPolicySupported": False,
        "AcceptanceRequired": True,
        "ManagesVpcEndpoints": False,
        "Tags": [],
    }

    mock = {
        "ec2": {
            "describe_vpc_endpoint_services.return_value": {
                "ServiceDetails": [vpc_endpoint_service_payload],
                "ServiceNames": ["com.amazonaws.vpce.eu-west-1.vpce-svc-11111111111111111"],
            }
        }
    }

    single_resource_scenarios = [
        SingleResourceScenario(
            urn=URN.from_string(
                "urn:aws:123456789012:eu-west-2:ec2:vpc_endpoint_service:com.amazonaws.vpce.eu-west-1.vpce-svc-11111111111111111"  # noqa
            ),
            expected_results=[vpc_endpoint_service_payload],
            expected_call=ExpectedCall(
                "ec2",
                "describe_vpc_endpoint_services",
                [],
                {"ServiceNames": ["com.amazonaws.vpce.eu-west-1.vpce-svc-11111111111111111"]},
            ),
        )
    ]
    multiple_resource_scenarios = [
        MultipleResourceScenario(
            arguments=CloudWandererCalls(
                regions=["eu-west-2"], service_names=["ec2"], resource_types=["vpc_endpoint_service"]
            ),
            expected_results=[vpc_endpoint_service_payload],
        )
    ]
