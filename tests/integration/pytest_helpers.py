import difflib
import json
import logging
import pprint
from typing import Any, Dict, List

import boto3

logger = logging.getLogger(__name__)


def create_s3_buckets(regions: List[str] = ["eu-west-2"]) -> None:
    for region_name in regions:
        if region_name != "us-east-1":
            bucket_args = {"CreateBucketConfiguration": {"LocationConstraint": region_name}}
        else:
            bucket_args = {}
        boto3.resource("s3", region_name="us-east-1").Bucket(f"test-{region_name}").create(**bucket_args)


def create_iam_role() -> None:
    iam_resource = boto3.resource("iam")
    iam_resource.create_role(RoleName="test-role", AssumeRolePolicyDocument="{}")
    policies = list(iam_resource.policies.all())
    iam_resource.Role("test-role").attach_policy(PolicyArn=policies[0].arn)
    iam_resource.Role("test-role").Policy("test-role-policy").put(
        PolicyDocument=json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": {"Effect": "Allow", "Action": "s3:ListBucket", "Resource": "arn:aws:s3:::example_bucket"},
            }
        )
    )


def create_ec2_instances(regions: List[str] = ["eu-west-2"]):
    for region_name in regions:
        ec2_resource = boto3.resource("ec2", region_name=region_name)
        images = list(ec2_resource.images.all())
        ec2_resource.create_instances(ImageId=images[0].image_id, MinCount=1, MaxCount=1)


def create_secretsmanager_secrets(regions=["eu-west-2"]) -> None:
    for region_name in regions:
        secretsmanager = boto3.client("secretsmanager", region_name=region_name)
        secretsmanager.create_secret(Name="TestSecret", SecretString="Ssshhh")


def compare_dict_allow_any(first: Dict[str, Any], second: Dict[str, Any], allow_partial_match_second: bool) -> None:
    """Compare two dictionaries allowing the values of either side to be ANY and match.

    Arguments:
        allow_partial_match_second: Assertion will succeed if the second param only has some of the keys of the first.

    Raises:
        AssertionError: If dictionaries are not equal.
    """
    diff = "\n" + "\n".join(difflib.ndiff(pprint.pformat(first).splitlines(), pprint.pformat(second).splitlines()))
    if not allow_partial_match_second:
        if first.items() == second.items():
            assert True
            return
    else:
        if not second:
            raise AssertionError("Dictionaries do not match" + diff)
        for key, value in second.items():
            if first.get(key) == value:
                continue
            raise AssertionError("Dictionaries do not match" + diff)
        return

    raise AssertionError("Dictionaries do not match" + diff)


def compare_list_of_dicts_allow_any(
    first: List[Dict[str, Any]], second: List[Dict[str, Any]], allow_partial_match_second: bool
) -> None:
    """
    Arguments:
        allow_partial_match_second: Success if the dictionaries in second only have some of the keys from first.

    """
    assert len(first) == len(second), f"Length of first {len(first)} and second {len(second)} is not equal"
    for first_item, second_item in zip(first, second):
        compare_dict_allow_any(first_item, second_item, allow_partial_match_second=allow_partial_match_second)
