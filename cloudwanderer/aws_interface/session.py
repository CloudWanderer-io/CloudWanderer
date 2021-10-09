from .boto3_loaders import MergedServiceLoader
from .resource_factory import CloudWandererResourceFactory
import boto3
import logging
from ..cache_helpers import memoized_method
from typing import List

logger = logging.getLogger(__name__)


class CloudWandererBoto3Session(boto3.session.Session):
    def __init__(
        self,
        aws_access_key_id=None,
        aws_secret_access_key=None,
        aws_session_token=None,
        region_name=None,
        botocore_session=None,
        profile_name=None,
        resource_factory=None,
        service_mapping_loader=None,
    ) -> None:
        super().__init__(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=aws_session_token,
            region_name=region_name,
            botocore_session=botocore_session,
            profile_name=profile_name,
        )
        self.service_mapping_loader = service_mapping_loader
        self.resource_factory = resource_factory or CloudWandererResourceFactory(
            self._session.get_component("event_emitter"),
            service_mapping_loader=self.service_mapping_loader,
            cloudwanderer_boto3_session=self,
        )

    @memoized_method()
    def get_account_id(self) -> str:
        """Return the AWS Account ID our Boto3 session is authenticated against."""
        sts = self.client("sts")
        return sts.get_caller_identity()["Account"]

    def _setup_loader(self):
        """
        Setup loader paths so that we can load resources.
        """
        self._loader = MergedServiceLoader()
        # self._loader = self._session.get_component("data_loader")
        # self._loader.search_paths.append(os.path.join(os.path.dirname(__file__), "data"))

    @memoized_method()  # type: ignore
    def get_enabled_regions(self) -> List[str]:
        """Return a list of enabled regions in this account."""
        regions = self.client("ec2").describe_regions()["Regions"]
        return [region["RegionName"] for region in regions if region["OptInStatus"] != "not-opted-in"]
