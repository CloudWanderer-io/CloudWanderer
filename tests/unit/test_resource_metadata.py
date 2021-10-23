from cloudwanderer.cloud_wanderer_resource import ResourceMetadata


def test_dict():
    subject = ResourceMetadata({"VpcId": "vpc-1111"})

    assert dict(subject) == {"VpcId": "vpc-1111"}
