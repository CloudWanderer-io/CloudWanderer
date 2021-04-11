"""Helper classes and methods for interacting with boto3."""
import logging
from typing import List

import boto3
import botocore  # type: ignore

from .cache_helpers import cached_property

logger = logging.getLogger(__name__)


class Boto3CommonAttributesMixin:
    """Mixin that provides common informational attributes unique to boto3."""

    def __init__(self) -> None:
        self.boto3_session = boto3.session.Session()

    @cached_property
    def account_id(self) -> str:
        """Return the AWS Account ID our Boto3 session is authenticated against."""
        sts = self.boto3_session.client("sts")
        return sts.get_caller_identity()["Account"]

    @cached_property
    def region_name(self) -> str:
        """Return the default AWS region."""
        return self.boto3_session.region_name

    @cached_property  # type: ignore
    def enabled_regions(self) -> List[str]:
        """Return a list of enabled regions in this account."""
        regions = self.boto3_session.client("ec2").describe_regions()["Regions"]
        return [region["RegionName"] for region in regions if region["OptInStatus"] != "not-opted-in"]


def get_shape(boto3_resource: boto3.resources.base.ServiceResource) -> botocore.model.Shape:
    """Return the Botocore shape of a boto3 Resource.

    Parameters:
        boto3_resource (boto3.resources.base.ServiceResource):
            The resource to get the shape of.
    """
    service_model = boto3_resource.meta.client.meta.service_model
    shape = service_model.shape_for(boto3_resource.meta.resource_model.shape)
    return shape


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
