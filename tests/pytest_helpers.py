import difflib
import json
import logging
import pprint
from typing import Any, Dict, List
from unittest.mock import ANY

import boto3

from cloudwanderer.cloud_wanderer_resource import CloudWandererResource
from cloudwanderer.models import Relationship, RelationshipDirection
from cloudwanderer.urn import URN, PartialUrn

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


def create_iam_policy() -> None:
    iam_resource = boto3.resource("iam")
    iam_resource.create_policy(
        PolicyName="test-policy",
        PolicyDocument='{"Version": "2012-10-17","Statement": [ {"Action": "*","Resource": "*","Effect": "Allow"}]}',
    )


def create_ec2_instances(regions: List[str] = ["eu-west-2"], count=1):
    for region_name in regions:
        logger.info("Creating ec2 instance in %s", region_name)
        ec2_resource = boto3.resource("ec2", region_name=region_name)
        images = list(ec2_resource.images.all())
        ec2_resource.create_instances(ImageId=images[0].image_id, MinCount=count, MaxCount=count)


def create_secretsmanager_secrets(regions=["eu-west-2"]) -> None:
    for region_name in regions:
        secretsmanager = boto3.client("secretsmanager", region_name=region_name)
        secretsmanager.create_secret(Name="TestSecret", SecretString="Ssshhh")


def try_dict(value):
    """Try converting objects first to dict, then to str so we can easily compare them against JSON."""
    try:
        return dict(value)
    except (ValueError, TypeError):
        return str(value)


def prepare_for_comparison(result):
    """Convert results into a JSON compatible dict for comparison"""
    return json.loads(
        json.dumps(
            list(result),
            default=try_dict,
        )
    )


def compare_dict_allow_partial_match_first(first: Dict[str, Any], second: Dict[str, Any]) -> None:
    try:
        second_json = json.dumps(second, default=try_dict)
    except (ValueError, TypeError):
        second_json = ""
    diff = (
        "\nSecond dict as json: "
        + second_json
        + "\nComparison: \n"
        + "\n".join(difflib.ndiff(pprint.pformat(first).splitlines(), pprint.pformat(second).splitlines()))
    )
    for key, value in first.items():
        if isinstance(value, dict) and isinstance(second.get(key), dict):
            compare_dict_allow_partial_match_first(value, second.get(key))
            continue
        if value == second.get(key):
            continue
        raise AssertionError(f"Dictionaries do not match on key {key}, {value} vs {second.get(key)} {diff}")


def compare_dict_allow_any(
    first: Dict[str, Any], second: Dict[str, Any], allow_partial_match_first: bool = False
) -> None:
    """Compare two dictionaries allowing the values of either side to be ANY and match.

    Arguments:
        allow_partial_match_first: Assertion will succeed if the first param only has some of the keys of the second.

    Raises:
        AssertionError: If dictionaries are not equal.
    """
    try:
        second_json = json.dumps(second, default=try_dict)
    except (ValueError, TypeError):
        second_json = ""
    diff = (
        "\nSecond dict as json: "
        + second_json
        + "\nComparison: \n"
        + "\n".join(difflib.ndiff(pprint.pformat(first).splitlines(), pprint.pformat(second).splitlines()))
    )
    if not first or not second:
        raise AssertionError(f"Dictionaries do not match {diff}")
    if not allow_partial_match_first:
        if first.keys() != second.keys():
            raise AssertionError("Dictionaries do not have the same number of keys" + diff)
        for first_item, second_item in zip(sorted(first.items()), sorted(second.items())):
            first_key, first_value = first_item
            second_key, second_value = second_item
            if first_value is ANY or second_value is ANY:
                continue

            if first_key != second_key or first_value != second_value:
                raise AssertionError(
                    f"Dictionaries do not match on {first_key}:{first_value} != {second_key}:{second_value}" + diff
                )
        return

    compare_dict_allow_partial_match_first(first, second)
    return


def compare_list_of_dicts_allow_any(
    first: List[Dict[str, Any]], second: List[Dict[str, Any]], allow_partial_match_first: bool = False
) -> None:
    """
    Arguments:
        allow_partial_match_first: Success if the dictionaries in first only have some of the keys from second.

    Raises:
        AssertionError: If lists are not equal.
    """

    if not len(first) == len(second):
        diff = "\n" + "\n".join(difflib.ndiff(pprint.pformat(first).splitlines(), pprint.pformat(second).splitlines()))
        raise AssertionError(f"The two lists are not of equal length: {diff}")
    for first_item, second_item in zip(first, second):
        compare_dict_allow_any(first_item, second_item, allow_partial_match_first=allow_partial_match_first)


def get_inferred_ec2_instances(cloudwanderer_boto3_session):
    vpcs = list(cloudwanderer_boto3_session.resource("ec2").vpcs.all())
    return [
        CloudWandererResource(
            urn=URN(
                account_id="111111111111",
                region="eu-west-2",
                service="ec2",
                resource_type="instance",
                resource_id_parts=[instance.instance_id],
            ),
            resource_data=instance.meta.data,
            relationships=[
                Relationship(
                    partial_urn=PartialUrn(
                        cloud_name="aws",
                        account_id="unknown",
                        region="eu-west-2",
                        service="ec2",
                        resource_type="vpc",
                        resource_id_parts=[vpcs[0].vpc_id],
                    ),
                    direction=RelationshipDirection.INBOUND,
                )
            ],
        )
        for instance in cloudwanderer_boto3_session.resource("ec2").instances.all()
    ]


def inferred_ec2_vpcs(cloudwanderer_boto3_session):
    return [
        CloudWandererResource(
            urn=URN(
                account_id="111111111111",
                region="eu-west-2",
                service="ec2",
                resource_type="vpc",
                resource_id_parts=[vpc.vpc_id],
            ),
            resource_data=vpc.meta.data,
        )
        for vpc in cloudwanderer_boto3_session.resource("ec2").vpcs.all()
    ]


def get_single_ec2_vpc(ec2_service):
    """Return a single Ec2 Vpc.

    Be warned, you can ONLY access properties on the resultant vpc that do not entail additional API calls.
    See single_iam_role for more details on how to mock additional API calls.
    """
    vpc = list(ec2_service.collection("vpc").all())[0]
    vpc.fetch_secondary_attributes()
    return vpc
