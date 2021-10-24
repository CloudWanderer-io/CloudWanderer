"""Subclass of Boto3 Session class to provide additional helper methods."""
import logging
from typing import List

import boto3
from botocore.loaders import Loader

from ..cache_helpers import memoized_method
from .boto3_loaders import MergedServiceLoader
from .resource_factory import CloudWandererResourceFactory

logger = logging.getLogger(__name__)


class CloudWandererBoto3Session(boto3.session.Session):
    """Subclass of Boto3 Session class to provide additional helper methods."""

    def __init__(
        self,
        aws_access_key_id=None,
        aws_secret_access_key=None,
        aws_session_token=None,
        region_name=None,
        botocore_session=None,
        profile_name=None,
        resource_factory=None,
        service_mapping_loader: Loader = None,
    ) -> None:
        self.service_mapping_loader = service_mapping_loader
        super().__init__(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=aws_session_token,
            region_name=region_name,
            botocore_session=botocore_session,
            profile_name=profile_name,
        )

        self.resource_factory = resource_factory or CloudWandererResourceFactory(
            self._session.get_component("event_emitter"),
            service_mapping_loader=self._loader,
            cloudwanderer_boto3_session=self,
        )

    @memoized_method()
    def get_account_id(self) -> str:
        """Return the AWS Account ID our Boto3 session is authenticated against."""
        sts = self.client("sts")
        return sts.get_caller_identity()["Account"]

    def _setup_loader(self) -> None:
        """Create loader paths so that we can load resources."""
        self._loader = self.service_mapping_loader or MergedServiceLoader()

    @memoized_method()
    def get_enabled_regions(self) -> List[str]:
        """Return a list of enabled regions in this account."""
        regions = self.client("ec2").describe_regions()["Regions"]
        return [region["RegionName"] for region in regions if region["OptInStatus"] != "not-opted-in"]
