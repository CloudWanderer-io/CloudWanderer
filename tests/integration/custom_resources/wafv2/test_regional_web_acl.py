import unittest

from cloudwanderer import URN

from ..helpers import CloudWandererCalls, ExpectedCall, MultipleResourceScenario, NoMotoMock, SingleResourceScenario


class TestRegionalWebAcl(NoMotoMock, unittest.TestCase):

    list_web_acl_payload = {
        "Name": "test-webacl",
        "Id": "11111111-1111-1111-1111-111111111111",
        "Description": "Test Web ACL",
        "LockToken": "11111111-1111-1111-1111-111111111111",
        "ARN": "arn:aws:wafv2:eu-west-1:123456789012:regional/webacl/test-webacl/11111111-1111-1111-1111-111111111111",
    }
    get_web_acl_payload = {
        "Name": "test-webacl",
        "Id": "11111111-1111-1111-1111-111111111111",
        "ARN": "arn:aws:wafv2:eu-west-1:123456789012:regional/webacl/test-webacl/11111111-1111-1111-1111-111111111111",
        "DefaultAction": {"Allow": {}},
        "Description": "Test Web ACL",
        "Rules": [
            {
                "Name": "AWS-AWSManagedRulesAmazonIpReputationList",
                "Priority": 0,
                "Statement": {
                    "ManagedRuleGroupStatement": {"VendorName": "AWS", "Name": "AWSManagedRulesAmazonIpReputationList"}
                },
                "OverrideAction": {"None": {}},
                "VisibilityConfig": {
                    "SampledRequestsEnabled": True,
                    "CloudWatchMetricsEnabled": True,
                    "MetricName": "AWS-AWSManagedRulesAmazonIpReputationList",
                },
            }
        ],
        "VisibilityConfig": {
            "SampledRequestsEnabled": True,
            "CloudWatchMetricsEnabled": True,
            "MetricName": "test-webacl",
        },
        "Capacity": 25,
        "ManagedByFirewallManager": False,
    }

    mock = {
        "wafv2": {
            "list_web_acls.return_value": {"WebACLs": [list_web_acl_payload]},
            "get_web_acl.return_value": {"WebACL": get_web_acl_payload},
        }
    }

    single_resource_scenarios = [
        SingleResourceScenario(
            urn=URN.from_string(
                "urn:aws:123456789012:eu-west-2:wafv2:regional_web_acl:test-webacl/11111111-1111-1111-1111-111111111111"
            ),
            expected_results=[get_web_acl_payload],
            expected_call=ExpectedCall(
                "wafv2",
                "get_web_acl",
                [],
                {"Id": "11111111-1111-1111-1111-111111111111", "Name": "test-webacl", "Scope": "REGIONAL"},
            ),
        )
    ]
    multiple_resource_scenarios = [
        MultipleResourceScenario(
            arguments=CloudWandererCalls(
                regions=["eu-west-2"], service_names=["wafv2"], resource_types=["regional_web_acl"]
            ),
            expected_results=[get_web_acl_payload],
        )
    ]
