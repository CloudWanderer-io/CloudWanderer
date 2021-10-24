from unittest.mock import ANY

import boto3
from moto import mock_ec2, mock_iam, mock_s3, mock_sts

from cloudwanderer.models import ServiceResourceType
from cloudwanderer.urn import URN

from ...pytest_helpers import compare_list_of_dicts_allow_any, create_ec2_instances, create_iam_role, create_s3_buckets


@mock_ec2
@mock_s3
@mock_sts
def test_write_resources(cloudwanderer_aws):
    create_s3_buckets()
    create_ec2_instances()
    cloudwanderer_aws.write_resources(
        regions=["eu-west-2", "us-east-1"],
        service_resource_types=[
            ServiceResourceType(service_name="ec2", name="instance"),
            ServiceResourceType(service_name="s3", name="bucket"),
        ],
    )

    result = list(cloudwanderer_aws.storage_connectors[0].read_all())

    compare_list_of_dicts_allow_any(
        result,
        [
            {
                "AmiLaunchIndex": 0,
                "Architecture": "x86_64",
                "BlockDeviceMappings": [
                    {
                        "DeviceName": "/dev/sda1",
                        "Ebs": {
                            "AttachTime": ANY,
                            "DeleteOnTermination": True,
                            "Status": "in-use",
                            "VolumeId": ANY,
                        },
                    }
                ],
                "BootMode": None,
                "CapacityReservationId": None,
                "CapacityReservationSpecification": None,
                "ClientToken": "ABCDE1234567890123",
                "CpuOptions": None,
                "EbsOptimized": False,
                "ElasticGpuAssociations": None,
                "ElasticInferenceAcceleratorAssociations": None,
                "EnaSupport": None,
                "EnclaveOptions": None,
                "HibernationOptions": None,
                "Hypervisor": "xen",
                "IamInstanceProfile": None,
                "ImageId": ANY,
                "InstanceId": ANY,
                "InstanceLifecycle": None,
                "InstanceType": "m1.small",
                "KernelId": "None",
                "KeyName": "None",
                "LaunchTime": ANY,
                "Licenses": None,
                "MetadataOptions": None,
                "Monitoring": {"State": "disabled"},
                "NetworkInterfaces": [
                    {
                        "Association": {"IpOwnerId": "123456789012", "PublicIp": ANY},
                        "Attachment": {
                            "AttachTime": "2015-01-01T00:00:00+00:00",
                            "AttachmentId": ANY,
                            "DeleteOnTermination": True,
                            "DeviceIndex": 0,
                            "Status": "attached",
                        },
                        "Description": "Primary network interface",
                        "Groups": [],
                        "MacAddress": "1b:2b:3c:4d:5e:6f",
                        "NetworkInterfaceId": ANY,
                        "OwnerId": "123456789012",
                        "PrivateIpAddress": ANY,
                        "PrivateIpAddresses": [
                            {
                                "Association": {"IpOwnerId": "123456789012", "PublicIp": ANY},
                                "Primary": True,
                                "PrivateIpAddress": ANY,
                            }
                        ],
                        "SourceDestCheck": True,
                        "Status": "in-use",
                        "SubnetId": ANY,
                        "VpcId": ANY,
                    }
                ],
                "OutpostArn": None,
                "Placement": {"AvailabilityZone": "eu-west-2a", "GroupName": None, "Tenancy": "default"},
                "Platform": "windows",
                "PlatformDetails": None,
                "PrivateDnsName": ANY,
                "PrivateIpAddress": ANY,
                "ProductCodes": [],
                "PublicDnsName": ANY,
                "PublicIpAddress": ANY,
                "RamdiskId": None,
                "RootDeviceName": "/dev/sda1",
                "RootDeviceType": "ebs",
                "SecurityGroups": [],
                "SourceDestCheck": True,
                "SpotInstanceRequestId": None,
                "SriovNetSupport": None,
                "State": {"Code": 16, "Name": "running"},
                "StateReason": {"Code": None, "Message": None},
                "StateTransitionReason": None,
                "SubnetId": ANY,
                "Tags": None,
                "UsageOperation": None,
                "UsageOperationUpdateTime": None,
                "VirtualizationType": "hvm",
                "VpcId": ANY,
                "attr": "BaseResource",
                "urn": ANY,
            },
            {
                "attr": "ParentUrn",
                "urn": ANY,
                "value": None,
            },
            {
                "attr": "DependentResourceUrns",
                "urn": ANY,
                "value": [],
            },
            {
                "CreationDate": ANY,
                "Name": "test-eu-west-2",
                "attr": "BaseResource",
                "urn": ANY,
            },
            {
                "attr": "ParentUrn",
                "urn": ANY,
                "value": None,
            },
            {
                "attr": "DependentResourceUrns",
                "urn": "urn:aws:123456789012:eu-west-2:s3:bucket:test-eu-west-2",
                "value": [],
            },
        ],
    )


# TODO: Reinstate exclude resources
# @mock_ec2
# @mock_sts
# def test_write_resources_exclude_resources(cloudwanderer_aws):
#     cloudwanderer_aws.write_resources(exclude_resources=["ec2:instance"])

#     for region_name in ["eu-west-2", "us-east-1"]:
#         assert_no_dictionary_overlap(
#             cloudwanderer_aws.storage_connectors[0].read_all(),
#             [
#                 {
#                     "urn": f"urn:aws:.*:{region_name}:ec2:instance:.*",
#                     "attr": "BaseResource",
#                     "VpcId": "vpc-.*",
#                     "SubnetId": "subnet-.*",
#                     "InstanceId": "i-.*",
#                 }
#             ],
#         )
#     assert_dictionary_overlap(cloudwanderer_aws.storage_connectors[0].read_all(), us_east_1_resources)


@mock_iam
@mock_ec2
@mock_sts
def test_cleanup_resources_of_type_us_east_1(cloudwanderer_aws):
    create_iam_role()

    cloudwanderer_aws.write_resources(
        regions=["us-east-1"],
        service_resource_types=[
            ServiceResourceType(service_name="iam", name="role"),
        ],
    )

    compare_list_of_dicts_allow_any(
        [
            {
                "PolicyDocument": {
                    "Statement": {
                        "Action": "s3:ListBucket",
                        "Effect": "Allow",
                        "Resource": "arn:aws:s3:::example_bucket",
                    },
                    "Version": "2012-10-17",
                },
                "PolicyName": "test-role-policy",
                "RoleName": "test-role",
                "attr": "BaseResource",
                "urn": "urn:aws:123456789012:us-east-1:iam:role_policy:test-role/test-role-policy",
            },
            {
                "attr": "ParentUrn",
                "urn": "urn:aws:123456789012:us-east-1:iam:role_policy:test-role/test-role-policy",
                "value": URN(
                    cloud_name="aws",
                    account_id="123456789012",
                    region="us-east-1",
                    service="iam",
                    resource_type="role",
                    resource_id_parts=["test-role"],
                ),
            },
            {
                "attr": "DependentResourceUrns",
                "urn": "urn:aws:123456789012:us-east-1:iam:role_policy:test-role/test-role-policy",
                "value": [],
            },
            {
                "Arn": "arn:aws:iam::123456789012:role/test-role",
                "AssumeRolePolicyDocument": {},
                "CreateDate": ANY,
                "Description": None,
                "InlinePolicyAttachments": {"IsTruncated": False, "Marker": None, "PolicyNames": ["test-role-policy"]},
                "ManagedPolicyAttachments": {
                    "AttachedPolicies": [
                        {
                            "PolicyArn": "arn:aws:iam::aws:policy/aws-service-role/APIGatewayServiceRolePolicy",
                            "PolicyName": "APIGatewayServiceRolePolicy",
                        }
                    ],
                    "IsTruncated": False,
                    "Marker": None,
                },
                "MaxSessionDuration": 3600,
                "Path": "/",
                "PermissionsBoundary": None,
                "RoleId": ANY,
                "RoleLastUsed": None,
                "RoleName": "test-role",
                "Tags": None,
                "attr": "BaseResource",
                "urn": "urn:aws:123456789012:us-east-1:iam:role:test-role",
            },
            {"attr": "ParentUrn", "urn": "urn:aws:123456789012:us-east-1:iam:role:test-role", "value": None},
            {
                "attr": "DependentResourceUrns",
                "urn": "urn:aws:123456789012:us-east-1:iam:role:test-role",
                "value": [
                    URN(
                        cloud_name="aws",
                        account_id="123456789012",
                        region="us-east-1",
                        service="iam",
                        resource_type="role_policy",
                        resource_id_parts=["test-role", "test-role-policy"],
                    )
                ],
            },
        ],
        list(cloudwanderer_aws.storage_connectors[0].read_all()),
    )

    # Delete the role
    iam_resource = boto3.resource("iam")
    iam_resource.Role("test-role").detach_policy(
        PolicyArn="arn:aws:iam::aws:policy/aws-service-role/APIGatewayServiceRolePolicy"
    )
    iam_resource.Role("test-role").Policy("test-role-policy").delete()
    iam_resource.Role("test-role").delete()

    cloudwanderer_aws.write_resources(
        regions=["us-east-1"],
        service_resource_types=[
            ServiceResourceType(service_name="iam", name="role"),
        ],
    )

    assert list(cloudwanderer_aws.storage_connectors[0].read_all()) == []
