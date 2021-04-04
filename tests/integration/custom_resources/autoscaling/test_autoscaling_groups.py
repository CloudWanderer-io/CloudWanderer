import unittest

from cloudwanderer import URN

from ..helpers import CloudWandererCalls, MultipleResourceScenario, NoMotoMock, SingleResourceScenario


class TestAutoScalingGroups(NoMotoMock, unittest.TestCase):
    auto_scaling_group_payload = {
        "AutoScalingGroupName": "test",
        "AutoScalingGroupARN": "arn:aws:autoscaling:eu-west-1:111111111111:autoScalingGroup:7ccb5b52-f617-417e-95c2-27104e51e1cb:autoScalingGroupName/test-group",  # noqa
        "MixedInstancesPolicy": {
            "LaunchTemplate": {
                "LaunchTemplateSpecification": {
                    "LaunchTemplateId": "lt-0655a3e590d9c5e6c",
                    "LaunchTemplateName": "test",
                    "Version": "$Default",
                },
                "Overrides": [
                    {"InstanceType": "t3a.micro"},
                    {"InstanceType": "t3a.large"},
                    {"InstanceType": "t3a.medium"},
                    {"InstanceType": "t3a.small"},
                    {"InstanceType": "t3.large"},
                    {"InstanceType": "t3.medium"},
                    {"InstanceType": "t3.small"},
                    {"InstanceType": "t3.micro"},
                ],
            },
            "InstancesDistribution": {
                "OnDemandAllocationStrategy": "prioritized",
                "OnDemandBaseCapacity": 0,
                "OnDemandPercentageAboveBaseCapacity": 70,
                "SpotAllocationStrategy": "capacity-optimized",
            },
        },
        "MinSize": 0,
        "MaxSize": 0,
        "DesiredCapacity": 0,
        "DefaultCooldown": 300,
        "AvailabilityZones": ["eu-west-1c"],
        "LoadBalancerNames": [],
        "TargetGroupARNs": [],
        "HealthCheckType": "EC2",
        "HealthCheckGracePeriod": 300,
        "Instances": [],
        "CreatedTime": "2021-04-04T11:18:44.204Z",
        "SuspendedProcesses": [],
        "VPCZoneIdentifier": "subnet-11111111",
        "EnabledMetrics": [],
        "Tags": [],
        "TerminationPolicies": ["Default"],
        "NewInstancesProtectedFromScaleIn": False,
        "ServiceLinkedRoleARN": "arn:aws:iam::111111111111:role/aws-service-role/autoscaling.amazonaws.com/AWSServiceRoleForAutoScaling",  # noqa
        "CapacityRebalance": True,
    }

    mock = {
        "autoscaling": {
            "describe_auto_scaling_groups.return_value": {
                "AutoScalingGroups": [auto_scaling_group_payload],
            }
        }
    }

    single_resource_scenarios = [
        SingleResourceScenario(
            urn=URN.from_string("urn:aws:123456789012:eu-west-1:autoscaling:auto_scaling_group:test-group"),
            expected_results=[auto_scaling_group_payload],
        )
    ]
    multiple_resource_scenarios = [
        MultipleResourceScenario(
            arguments=CloudWandererCalls(
                regions=["eu-west-1"], service_names=["autoscaling"], resource_types=["auto_scaling_group"]
            ),
            expected_results=[auto_scaling_group_payload],
        )
    ]
