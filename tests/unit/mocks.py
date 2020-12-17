from unittest.mock import MagicMock
import boto3

MOCK_COLLECTION_INSTANCES = MagicMock(**{
    'meta.service_name': 'ec2',
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
