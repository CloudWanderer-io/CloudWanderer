"""Helper classes and methods for interacting with boto3."""


def _clean_boto3_metadata(boto3_metadata: dict) -> dict:
    """Remove unwanted keys from boto3 metadata dictionaries.

    Arguments:
        boto3_metadata (dict): The raw dictionary of metadata typically found in resource.meta.data
    """
    boto3_metadata = boto3_metadata or {}
    unwanted_keys = ["ResponseMetadata"]
    for key in unwanted_keys:
        if key in boto3_metadata:
            del boto3_metadata[key]
    return boto3_metadata
