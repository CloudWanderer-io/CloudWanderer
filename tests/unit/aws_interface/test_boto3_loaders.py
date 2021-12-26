from unittest.mock import MagicMock

from cloudwanderer.aws_interface.boto3_loaders import CustomServiceLoader, MergedServiceLoader


def test_merged_service_loader_list_available_services():
    mock_custom_service_loader = MagicMock(available_services=["lambda"])
    mock_botocore_session = MagicMock(**{"get_component.return_value.list_available_services.return_value": ["ec2"]})

    subject = MergedServiceLoader(
        custom_service_loader=mock_custom_service_loader, botocore_session=mock_botocore_session
    )

    assert subject.list_available_services() == ["ec2", "lambda"]


def test_custom_service_loader_path_default():
    subject = CustomServiceLoader()

    assert subject.service_definitions_path.endswith("cloudwanderer/aws_interface/resource_definitions")


def test_custom_service_loader_path_custom():
    subject = CustomServiceLoader(definition_path="testpath")

    assert subject.service_definitions_path == "testpath"
