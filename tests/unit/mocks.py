from unittest.mock import MagicMock
import boto3

MOCK_COLLECTION = MagicMock(**{
    'meta.service_name': 'ec2',
})
MOCK_COLLECTION.configure_mock(name='instances')


def add_servers(count=1):
    resource = boto3.resource('ec2', region_name='eu-west-2')
    images = list(resource.images.all())
    resource.create_instances(ImageId=images[0].image_id, MinCount=count, MaxCount=count)
