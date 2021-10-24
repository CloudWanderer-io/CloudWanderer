from cloudwanderer.models import ActionSet, TemplateActionSet
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
                resource_id_parts=["ALL"],
            ),
            PartialUrn(
                cloud_name="aws",
                account_id="ALL",
                region="us-east-1",
                service="ec2",
                resource_type="vpc",
                resource_id_parts=["ALL"],
            ),
        ],
        delete_urns=[
            PartialUrn(
                cloud_name="aws",
                account_id="ALL",
                region="eu-west-1",
                service="ec2",
                resource_type="vpc",
                resource_id_parts=["ALL"],
            ),
            PartialUrn(
                cloud_name="aws",
                account_id="ALL",
                region="us-east-1",
                service="ec2",
                resource_type="vpc",
                resource_id_parts=["ALL"],
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
                resource_id_parts=["ALL"],
            ),
            PartialUrn(
                cloud_name="aws",
                account_id="111111",
                region="us-east-1",
                service="ec2",
                resource_type="vpc",
                resource_id_parts=["ALL"],
            ),
        ],
        delete_urns=[
            PartialUrn(
                cloud_name="aws",
                account_id="111111",
                region="eu-west-1",
                service="ec2",
                resource_type="vpc",
                resource_id_parts=["ALL"],
            ),
            PartialUrn(
                cloud_name="aws",
                account_id="111111",
                region="us-east-1",
                service="ec2",
                resource_type="vpc",
                resource_id_parts=["ALL"],
            ),
        ],
    )
