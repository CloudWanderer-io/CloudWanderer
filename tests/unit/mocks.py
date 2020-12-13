from unittest.mock import MagicMock
import boto3

MOCK_COLLECTION_INSTANCES = MagicMock(**{
    'meta.service_name': 'ec2',
})
MOCK_COLLECTION_INSTANCES.configure_mock(name='instances')
MOCK_COLLECTION_VPC_ATTRIBUTE = MagicMock(**{
    'meta.service_name': 'ec2',
})
MOCK_COLLECTION_VPC_ATTRIBUTE.configure_mock(name='VpcEnableDnsSupport')

def add_infra(count=1):
    resource = boto3.resource('ec2', region_name='eu-west-2')
    images = list(resource.images.all())
    resource.create_instances(ImageId=images[0].image_id, MinCount=count, MaxCount=count)
    # resource.create_vpc(CidrBlock='10.0.0.0/24')
    print('vpc', list(resource.vpcs.all())[0].describe_attribute(Attribute='enableDnsSupport'))
