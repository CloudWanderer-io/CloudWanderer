from cloudwanderer.models import ActionSet, TemplateActionSet, TemplateActionSetRegionValues
from cloudwanderer.urn import PartialUrn


def test_template_action_set_inflate():
    template = TemplateActionSet(
        get_urns=[
            PartialUrn(
                cloud_name="aws",
                account_id="ALL",
                region="eu-west-1",
                service="ec2",
                resource_type="vpc",
                resource_id_parts=[],
            ),
            PartialUrn(
                cloud_name="aws",
                account_id="ALL",
                region="us-east-1",
                service="ec2",
                resource_type="vpc",
                resource_id_parts=[],
            ),
        ],
        delete_urns=[
            PartialUrn(
                cloud_name="aws",
                account_id="ALL",
                region="eu-west-1",
                service="ec2",
                resource_type="vpc",
                resource_id_parts=[],
            ),
            PartialUrn(
                cloud_name="aws",
                account_id="ALL",
                region="us-east-1",
                service="ec2",
                resource_type="vpc",
                resource_id_parts=[],
            ),
        ],
    )

    assert template.inflate(regions=["eu-west-1"], account_id="111111") == ActionSet(
        get_urns=[
            PartialUrn(
                cloud_name="aws",
                account_id="111111",
                region="eu-west-1",
                service="ec2",
                resource_type="vpc",
                resource_id_parts=[],
            ),
            PartialUrn(
                cloud_name="aws",
                account_id="111111",
                region="us-east-1",
                service="ec2",
                resource_type="vpc",
                resource_id_parts=[],
            ),
        ],
        delete_urns=[
            PartialUrn(
                cloud_name="aws",
                account_id="111111",
                region="eu-west-1",
                service="ec2",
                resource_type="vpc",
                resource_id_parts=[],
            ),
            PartialUrn(
                cloud_name="aws",
                account_id="111111",
                region="us-east-1",
                service="ec2",
                resource_type="vpc",
                resource_id_parts=[],
            ),
        ],
    )


def test_template_action_set_inflate_regions():
    template = TemplateActionSet(
        get_urns=[
            PartialUrn(
                cloud_name="aws",
                account_id="ALL",
                region="us-east-1",
                service="s3",
                resource_type="bucket",
                resource_id_parts=[],
            )
        ],
        delete_urns=[
            PartialUrn(
                cloud_name="aws",
                account_id="ALL",
                region=TemplateActionSetRegionValues.ALL_REGIONS.name,
                service="s3",
                resource_type="bucket",
                resource_id_parts=[],
            )
        ],
    )

    assert template.inflate(regions=["us-east-1", "eu-west-1"], account_id="111111") == ActionSet(
        get_urns=[
            PartialUrn(
                cloud_name="aws",
                account_id="111111",
                region="us-east-1",
                service="s3",
                resource_type="bucket",
                resource_id_parts=[],
            ),
        ],
        delete_urns=[
            PartialUrn(
                cloud_name="aws",
                account_id="111111",
                region="us-east-1",
                service="s3",
                resource_type="bucket",
                resource_id_parts=[],
            ),
            PartialUrn(
                cloud_name="aws",
                account_id="111111",
                region="eu-west-1",
                service="s3",
                resource_type="bucket",
                resource_id_parts=[],
            ),
        ],
    )
