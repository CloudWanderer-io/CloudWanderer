from unittest.mock import MagicMock
import boto3
from cloudwanderer import AwsUrn

MOCK_COLLECTION_INSTANCES = MagicMock(**{
    'meta.service_name': 'ec2',
    'resource.model.shape': 'instance'
})
MOCK_COLLECTION_INSTANCES.configure_mock(name='instances')


def generate_mock_session():
    return boto3.session.Session(
        region_name='eu-west-2',
        aws_access_key_id='1111',
        aws_secret_access_key='1111'
    )


def add_infra(count=1):
    resource = boto3.resource('ec2', region_name='eu-west-2')
    images = list(resource.images.all())
    resource.create_instances(ImageId=images[0].image_id, MinCount=count, MaxCount=count)
    for i in range(count-1):
        resource.create_vpc(CidrBlock='10.0.0.0/16')


def generate_urn(service, resource_type, id):
    return AwsUrn(
        account_id='111111111111',
        region='eu-west-2',
        service=service,
        resource_type=resource_type,
        resource_id=id
    )
