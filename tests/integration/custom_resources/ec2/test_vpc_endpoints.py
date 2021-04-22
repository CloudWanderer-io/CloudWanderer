import unittest

from cloudwanderer import URN

from ..helpers import CloudWandererCalls, ExpectedCall, MultipleResourceScenario, NoMotoMock, SingleResourceScenario


class TestVPCEndpoints(NoMotoMock, unittest.TestCase):

    vpc_endpoint_payload = {
        "VpcEndpointId": "vpce-11111111111111111",
        "VpcEndpointType": "Interface",
        "VpcId": "vpc-11111111",
        "ServiceName": "com.amazonaws.eu-west-1.s3",
        "State": "pending",
        "PolicyDocument": '{\n    "Statement": [\n        {\n            "Action": "*",\n            "Effect": "Allow",\n            "Resource": "*",\n            "Principal": "*"\n        }\n    ]\n}',  # noqa
        "RouteTableIds": [],
        "SubnetIds": ["subnet-11111111", "subnet-22222222", "subnet-33333333"],
        "Groups": [{"GroupId": "sg-11111111", "GroupName": "default"}],
        "PrivateDnsEnabled": False,
        "RequesterManaged": False,
        "NetworkInterfaceIds": [
            "eni-11111111111111111",
            "eni-22222222222222222",
            "eni-33333333333333333",
        ],
        "DnsEntries": [
            {
                "DnsName": "*.vpce-11111111111111111-11111111.s3.eu-west-1.vpce.amazonaws.com",
                "HostedZoneId": "11111111111111",
            },
            {
                "DnsName": "*.vpce-11111111111111111-11111111-eu-west-1b.s3.eu-west-1.vpce.amazonaws.com",
                "HostedZoneId": "11111111111111",
            },
            {
                "DnsName": "*.vpce-11111111111111111-11111111-eu-west-1c.s3.eu-west-1.vpce.amazonaws.com",
                "HostedZoneId": "11111111111111",
            },
            {
                "DnsName": "*.vpce-11111111111111111-11111111-eu-west-1a.s3.eu-west-1.vpce.amazonaws.com",
                "HostedZoneId": "11111111111111",
            },
        ],
        "CreationTimestamp": "2021-04-11T09:46:00.672Z",
        "Tags": [],
        "OwnerId": "111111111111",
    }

    mock = {
        "ec2": {
            "describe_vpc_endpoints.return_value": {"VpcEndpoints": [vpc_endpoint_payload]},
        }
    }

    single_resource_scenarios = [
        SingleResourceScenario(
            urn=URN.from_string("urn:aws:123456789012:eu-west-2:ec2:vpc_endpoint:vpce-11111111111111111"),
            expected_results=[vpc_endpoint_payload],
            expected_call=ExpectedCall(
                "ec2", "describe_vpc_endpoints", [], {"VpcEndpointIds": ["vpce-11111111111111111"]}
            ),
        )
    ]
    multiple_resource_scenarios = [
        MultipleResourceScenario(
            arguments=CloudWandererCalls(regions=["eu-west-2"], service_names=["ec2"], resource_types=["vpc_endpoint"]),
            expected_results=[vpc_endpoint_payload],
        )
    ]
