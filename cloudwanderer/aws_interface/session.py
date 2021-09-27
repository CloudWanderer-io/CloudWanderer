from .boto3_loaders import ServiceMappingLoader
from .resource_factory import CloudWandererResourceFactory
from ..models import ActionSet
from typing import List, Optional, Tuple
import boto3
import logging

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
        self.service_mapping_loader = service_mapping_loader or ServiceMappingLoader()
        self.resource_factory = resource_factory or CloudWandererResourceFactory(
            self._session.get_component("event_emitter"), service_mapping_loader=self.service_mapping_loader
        )
