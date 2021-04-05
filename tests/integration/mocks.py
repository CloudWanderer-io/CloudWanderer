import json
import os
from unittest.mock import MagicMock

import boto3

from cloudwanderer import URN


def generate_mock_collection(service, shape_name, collection_name):
    resource_model = MagicMock(shape=shape_name)
    resource_model.configure_mock(name=shape_name)
    collection = MagicMock(**{"meta.service_name": service, "resource.model": resource_model})
    collection.configure_mock(name=collection_name)
    return collection


MOCK_COLLECTION_INSTANCES = generate_mock_collection("ec2", "Instance", "instances")
MOCK_COLLECTION_BUCKETS = generate_mock_collection("s3", "Bucket", "buckets")
MOCK_COLLECTION_IAM_GROUPS = generate_mock_collection("iam", "Group", "groups")
MOCK_COLLECTION_IAM_ROLES = generate_mock_collection("iam", "Role", "roles")
MOCK_COLLECTION_IAM_ROLE_POLICIES = generate_mock_collection("Role", "RolePolicy", "policies")

ENABLED_REGIONS = [
    "af-south-1",
    "ap-northeast-1",
    "ap-northeast-2",
    "ap-south-1",
    "ap-southeast-1",
    "ap-southeast-2",
    "ca-central-1",
    "eu-central-1",
    "eu-north-1",
    "eu-south-1",
    "eu-west-1",
    "eu-west-2",
    "eu-west-3",
    "sa-east-1",
    "us-east-1",
    "us-east-2",
    "us-west-1",
    "us-west-2",
    "us-gov-east-1",
    "us-gov-west-1",
    # Disabled because moto seemed to leak through to real AWS for listbuckets in these regions.
    # 'cn-north-1',
    # 'cn-northwest-1'
]


def generate_mock_session(region="eu-west-2"):
    return boto3.session.Session(region_name=region, aws_access_key_id="1111", aws_secret_access_key="1111")


def add_infra(count=1, regions=["us-east-1", "eu-west-2", "ap-east-1"]):
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    for region_name in regions:
        ec2_resource = boto3.resource("ec2", region_name=region_name)
        images = list(ec2_resource.images.all())
        ec2_resource.create_instances(ImageId=images[0].image_id, MinCount=count, MaxCount=count)
        for i in range(count - 1):
            ec2_resource.create_vpc(CidrBlock="10.0.0.0/16")

        if region_name != "us-east-1":
            bucket_args = {"CreateBucketConfiguration": {"LocationConstraint": region_name}}
        else:
            bucket_args = {}
        boto3.resource("s3", region_name="us-east-1").Bucket(f"test-{region_name}").create(**bucket_args)

    iam_resource = boto3.resource("iam")
    iam_resource.Group("test-group").create()
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


def generate_urn(service, resource_type, resource_id, parent_id=None):
    return URN(
        account_id="111111111111",
        region="eu-west-2",
        service=service,
        resource_type=resource_type,
        resource_id=resource_id,
        parent_resource_id=parent_id,
    )
