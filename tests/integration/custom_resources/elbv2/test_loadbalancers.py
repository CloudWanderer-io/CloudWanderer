import unittest

from cloudwanderer import URN

from ..helpers import CloudWandererCalls, ExpectedCall, MultipleResourceScenario, NoMotoMock, SingleResourceScenario


class TestLoadBalancers(NoMotoMock, unittest.TestCase):

    load_balancers_payload = {
        "LoadBalancerArn": "arn:aws:elasticloadbalancing:eu-west-1:111111111111:loadbalancer/net/test-nlb/1111111111111111",  # noqa
        "DNSName": "test-nlb-1111111111111111.elb.eu-west-1.amazonaws.com",
        "CanonicalHostedZoneId": "11111111111111",
        "CreatedTime": "2021-04-11T14:15:20.004Z",
        "LoadBalancerName": "test-nlb",
        "Scheme": "internet-facing",
        "VpcId": "vpc-11111111",
        "State": {"Code": "provisioning"},
        "Type": "network",
        "AvailabilityZones": [
            {"ZoneName": "eu-west-1a", "SubnetId": "subnet-11111111", "LoadBalancerAddresses": []},
            {"ZoneName": "eu-west-1c", "SubnetId": "subnet-22222222", "LoadBalancerAddresses": []},
            {"ZoneName": "eu-west-1b", "SubnetId": "subnet-33333333", "LoadBalancerAddresses": []},
        ],
        "IpAddressType": "ipv4",
    }

    mock = {
        "elbv2": {
            "describe_load_balancers.return_value": {"LoadBalancers": [load_balancers_payload]},
        }
    }

    single_resource_scenarios = [
        SingleResourceScenario(
            urn=URN.from_string("urn:aws:123456789012:eu-west-2:elbv2:load_balancer:test-nlb"),
            expected_results=[load_balancers_payload],
            expected_call=ExpectedCall("elbv2", "describe_load_balancers", [], {"Names": ["test-nlb"]}),
        )
    ]
    multiple_resource_scenarios = [
        MultipleResourceScenario(
            arguments=CloudWandererCalls(
                regions=["eu-west-2"], service_names=["elbv2"], resource_types=["load_balancer"]
            ),
            expected_results=[load_balancers_payload],
        )
    ]
