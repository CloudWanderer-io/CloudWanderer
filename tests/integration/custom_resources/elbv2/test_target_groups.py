import unittest

from cloudwanderer import URN

from ..helpers import CloudWandererCalls, ExpectedCall, MultipleResourceScenario, NoMotoMock, SingleResourceScenario


class TestTargetGroups(NoMotoMock, unittest.TestCase):

    target_groups_payload = {
        "TargetGroupArn": "arn:aws:elasticloadbalancing:eu-west-1:111111111111:targetgroup/test-targetgroup/1111111111111111",  # noqa
        "TargetGroupName": "test-targetgroup",
        "Protocol": "TCP",
        "Port": 80,
        "VpcId": "vpc-11111111",
        "HealthCheckProtocol": "TCP",
        "HealthCheckPort": "traffic-port",
        "HealthCheckEnabled": True,
        "HealthCheckIntervalSeconds": 30,
        "HealthCheckTimeoutSeconds": 10,
        "HealthyThresholdCount": 3,
        "UnhealthyThresholdCount": 3,
        "LoadBalancerArns": [],
        "TargetType": "ip",
    }

    mock = {
        "elbv2": {
            "describe_target_groups.return_value": {"TargetGroups": [target_groups_payload]},
        }
    }

    single_resource_scenarios = [
        SingleResourceScenario(
            urn=URN.from_string("urn:aws:123456789012:eu-west-2:elbv2:target_group:test-targetgroup"),
            expected_results=[target_groups_payload],
            expected_call=ExpectedCall("elbv2", "describe_target_groups", [], {"Names": ["test-targetgroup"]}),
        )
    ]
    multiple_resource_scenarios = [
        MultipleResourceScenario(
            arguments=CloudWandererCalls(
                regions=["eu-west-2"], service_names=["elbv2"], resource_types=["target_group"]
            ),
            expected_results=[target_groups_payload],
        )
    ]
