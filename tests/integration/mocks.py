import os
from unittest.mock import MagicMock, Mock
import boto3
from cloudwanderer import AwsUrn

MOCK_COLLECTION_INSTANCES = MagicMock(**{
    'meta.service_name': 'ec2',
    'resource.model.shape': 'instance'
})
MOCK_COLLECTION_INSTANCES.configure_mock(name='instances')
MOCK_COLLECTION_BUCKETS = MagicMock(**{
    'meta.service_name': 's3',
    'resource.model.shape': 'bucket'
})
MOCK_COLLECTION_BUCKETS.configure_mock(name='buckets')
MOCK_COLLECTION_IAM_GROUPS = MagicMock(**{
    'meta.service_name': 'iam',
    'resource.model.shape': 'group'
})
MOCK_COLLECTION_IAM_GROUPS.configure_mock(name='groups')
ENABLED_REGIONS = [
    'af-south-1',
    'ap-northeast-1',
    'ap-northeast-2',
    'ap-south-1',
    'ap-southeast-1',
    'ap-southeast-2',
    'ca-central-1',
    'eu-central-1',
    'eu-north-1',
    'eu-south-1',
    'eu-west-1',
    'eu-west-2',
    'eu-west-3',
    'sa-east-1',
    'us-east-1',
    'us-east-2',
    'us-west-1',
    'us-west-2',
    'us-gov-east-1',
    'us-gov-west-1',
    # Disabled because moto seemed to leak through to real AWS for listbuckets in these regions.
    # 'cn-north-1',
    # 'cn-northwest-1'
]


def generate_mock_session(region='eu-west-2'):
    return boto3.session.Session(
        region_name=region,
        aws_access_key_id='1111',
        aws_secret_access_key='1111'
    )


def add_infra(count=1, regions=ENABLED_REGIONS):
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    for region_name in regions:
        ec2_resource = boto3.resource('ec2', region_name=region_name)
        images = list(ec2_resource.images.all())
        ec2_resource.create_instances(ImageId=images[0].image_id, MinCount=count, MaxCount=count)
        for i in range(count - 1):
            ec2_resource.create_vpc(CidrBlock='10.0.0.0/16')

        if region_name != 'us-east-1':
            bucket_args = {'CreateBucketConfiguration': {'LocationConstraint': region_name}}
        else:
            bucket_args = {}
        boto3.resource('s3', region_name='us-east-1').Bucket(f"test-{region_name}").create(**bucket_args)

    iam_resource = boto3.resource('iam')
    iam_resource.Group('test-group').create()


def generate_urn(service, resource_type, id):
    return AwsUrn(
        account_id='111111111111',
        region='eu-west-2',
        service=service,
        resource_type=resource_type,
        resource_id=id
    )


def generate_mock_resource_attribute(data):
    return Mock(
        **{
            'meta.data': data
        }
    )
