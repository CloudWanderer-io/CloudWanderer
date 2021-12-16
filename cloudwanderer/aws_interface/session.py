"""Subclass of Boto3 Session class to provide additional helper methods."""
import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

import boto3
import botocore
from botocore.loaders import Loader

from ..cache_helpers import memoized_method
from .aws_services import AWS_SERVICES
from .boto3_loaders import MergedServiceLoader
from .resource_factory import CloudWandererResourceFactory

if TYPE_CHECKING:
    from .stubs.resource import CloudWandererServiceResource

logger = logging.getLogger(__name__)


class CloudWandererBoto3ClientConfig:
    """Allows the specification of internal getter client config.

    Example:
        Configure the sts client (used in :attr:`CloudWandererBoto3Session.get_account_id`) to use
        a regional endpoint url.

            >>> from cloudwanderer.aws_interface import (
            ...     CloudWandererBoto3ClientConfig,
            ...     CloudWandererBoto3Session
            ... )
            >>> getter_client_config = CloudWandererBoto3ClientConfig(
            ...     sts={"endpoint_url": "https://sts.eu-west-1.amazonaws.com"}
            ... )
            >>> cloudwanderer_boto3_session = CloudWandererBoto3Session(getter_client_config=getter_client_config)
    """

    def __init__(self, **kwargs: Dict[str, Dict[str, Any]]) -> None:
        self.client_configs: Dict[str, Dict[str, Any]] = kwargs

    def __call__(self, service_name: str) -> Dict[str, Any]:
        return self.client_configs.get(service_name, {})


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
        getter_client_config: Optional[CloudWandererBoto3ClientConfig] = None,
        account_id: Optional[str] = None,
        enabled_regions: Optional[List[str]] = None,
    ) -> None:
        """Subclass of Boto3 Session class to provide additional helper methods.

        You will need to interact with this class to provide any credentials that cannot be found in the
        normal Boto3 credentials locations (env vars, default profile, etc.)

        You can also use it to supply a custom resource factory
        if you want to test or use your own resource definitions.

        Args:
            aws_access_key_id:
                AWS access key ID
            aws_secret_access_key:
                AWS secret access key
            aws_session_token:
                AWS temporary session token
            region_name:
                Default region when creating new connections
            botocore_session:
                Use this Botocore session instead of creating a new default one.
            profile_name:
                 The name of a profile to use. If not given, then the default profile is used.
            resource_factory:
                Supply a custom resource factory, useful if you want to test/use your own resource definitions.
            service_mapping_loader:
                Supply a custom service mapping loader, useful if you want to test/use your own resource definitions.
            getter_client_config:
                Supply boto3 client config for
                :func:`CloudWandererBoto3Session.get_account_id` and
                :func:`CloudWandererBoto3Session.get_enabled_regions` .
            account_id:
                The AWS account ID we're fetching resources from. This will be fetched automatically via API
                call if not supplied.
            enabled_regions:
                The list of regions enabled in this AWS account. This will be fetched automatically via API
                call if not supplied.
        """
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

        self.getter_client_config = getter_client_config or CloudWandererBoto3ClientConfig()
        self._account_id = account_id
        self._enabled_regions = enabled_regions

    @memoized_method()
    def get_account_id(self) -> str:
        """Return the AWS Account ID our Boto3 session is authenticated against."""
        if self._account_id:
            return self._account_id
        sts = self.client("sts", **self.getter_client_config("sts"))
        return sts.get_caller_identity()["Account"]

    def _setup_loader(self) -> None:
        """Create loader paths so that we can load resources."""
        self._loader = self.service_mapping_loader or MergedServiceLoader()

    @memoized_method()
    def get_enabled_regions(self) -> List[str]:
        """Return a list of enabled regions in this account."""
        if self._enabled_regions:
            return self._enabled_regions
        regions = self.client("ec2", **self.getter_client_config("ec2")).describe_regions()["Regions"]
        return [region["RegionName"] for region in regions if region["OptInStatus"] != "not-opted-in"]

    def resource(  # type: ignore[override]
        self,
        service_name: AWS_SERVICES,
        region_name: Optional[str] = None,
        api_version: Optional[str] = None,
        use_ssl: Optional[bool] = True,
        verify: Union[bool, str, None] = None,
        endpoint_url: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        aws_session_token: Optional[str] = None,
        config: Optional[botocore.client.Config] = None,
    ) -> "CloudWandererServiceResource":
        return super().resource(  # type: ignore[call-overload, misc]
            service_name,  # type: ignore[arg-type]
            region_name=region_name,
            api_version=api_version,
            use_ssl=use_ssl,
            verify=verify,
            endpoint_url=endpoint_url,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=aws_session_token,
            config=config,
        )
