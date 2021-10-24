from cloudwanderer.aws_interface.boto3_helpers import _clean_boto3_metadata


def test__clean_boto3_metadata():
    result = _clean_boto3_metadata(
        boto3_metadata={
            "ShouldIBeHere": "Yes",
            "ResponseMetadata": {"ShouldIBeHere": "No"},
        }
    )

    assert result == {"ShouldIBeHere": "Yes"}
