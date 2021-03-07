"""A standardised interface for interacting with AWS.

Provides simpler methods for :class:`~.cloud_wanderer.CloudWanderer` to call.
"""

import logging
from typing import Iterator, List

import boto3
import botocore
from boto3.resources.model import ResourceModel

from .boto3_helpers import Boto3CommonAttributesMixin
from .boto3_loaders import ServiceMappingLoader
from .boto3_services import Boto3Services, MergedServiceLoader
from .cloud_wanderer_resource import CloudWandererResource
from .exceptions import BadRequestError, ResourceNotFoundError, UnsupportedServiceError
from .storage_connectors.base_connector import BaseStorageConnector
from .urn import URN

logger = logging.getLogger(__name__)


class CloudWandererAWSInterface(Boto3CommonAttributesMixin):
    """Simplifies lookup of Boto3 services and resources."""

    limit_resources = None

    def __init__(
        self,
        boto3_session: boto3.session.Session = None,
        service_loader: MergedServiceLoader = None,
        service_mapping_loader: ServiceMappingLoader = None,
    ) -> None:
        """Simplifies lookup of Boto3 services and resources.

        Arguments:
            boto3_session (boto3.session.Session):
                A Boto3 session, if not provided the default will be used.
            service_loader:
                An optional loader to allow the injection of additional custom services
            service_mapping_loader:
                An optional loader to allow the injection of additional custom service mappings
        """
        self.boto3_session = boto3_session or boto3.Session()
        self.boto3_services = Boto3Services(
            boto3_session=boto3_session, service_loader=service_loader, service_mapping_loader=service_mapping_loader
        )

    def get_resource(self, urn: URN) -> CloudWandererResource:
        """Return CloudWandererResource picked out by this urn.

        Arguments:
            urn (URN): The urn of the resource to get.
        """
        try:
            resource = self.boto3_services.get_resource_from_urn(urn=urn)
        except ResourceNotFoundError:
            return None
        except BadRequestError:
            logger.debug(
                f"Got BadRequestError while getting {urn}, as AWS services commonly return 4xx errors other than 404 "
                "for resource non-existence we are interpreting this as the resource does not exist."
            )
            return None

        return CloudWandererResource(
            urn=urn,
            resource_data=resource.normalised_raw_data,
            secondary_attributes=list(resource.get_secondary_attributes()),
        )

    def get_resources(
        self,
        regions: List[str] = None,
        service_names: List[str] = None,
        resource_types: List[str] = None,
        exclude_resources: List[str] = None,
        **kwargs,
    ) -> Iterator[CloudWandererResource]:
        """Get resources matching the arguments.

        All arguments are optional.

        Arguments:
            regions(list):
                The name of the region to get resources from (defaults to session default if not specified)
            service_names (str):
                The names of the services to write resources for (e.g. ``['ec2']``)
            resource_types (list):
                A list of resource types to include (e.g. ``['instance']``)
            exclude_resources (list):
                A list of service:resources to exclude (e.g. ``['ec2:instance']``)
            kwargs:
                All additional keyword arguments will be passed down to the Boto3 client calls.
        """
        regions = regions or self.enabled_regions
        for region_name in regions:
            yield from self._get_resources_in_region(
                service_names=service_names,
                resource_types=resource_types,
                exclude_resources=exclude_resources,
                region_name=region_name,
                **kwargs,
            )

    def _get_resources_in_region(
        self,
        service_names: List[str],
        resource_types: List[str] = None,
        exclude_resources: List[str] = None,
        region_name: str = None,
        **kwargs,
    ) -> None:
        """Get resources in region matching the resource types.

        Any additional args will be passed into the Boto3 client methods.

        Arguments:
            service_names (str):
                The names of the services to write resources for (e.g. ``['ec2']``)
            resource_types (list):
                A list of resource types to include (e.g. ``['instance']``)
            exclude_resources (list):
                exclude_resources (list): A list of service:resources to exclude (e.g. ``['ec2:instance']``)
            region_name (str):
                The name of the region to get resources from (defaults to session default if not specified)
            **kwargs: Additional keyword arguments will be passed down to the cloud interface methods.

        Raises:
            UnsupportedServiceError: Occurs if a service is requested that CloudWanderer does not support.
        """
        exclude_resources = exclude_resources or []
        service_names = service_names or self.boto3_services.available_services

        for service_name in service_names:
            if service_name not in self.boto3_services.available_services:
                raise UnsupportedServiceError(f"Service {service_name} is not supported by CloudWanderer.")
            yield from self._get_resources_of_service_in_region(
                service_name=service_name,
                resource_types=resource_types,
                exclude_resources=exclude_resources,
                region_name=region_name,
                **kwargs,
            )

    def _get_resources_of_service_in_region(
        self,
        service_name: str,
        region_name: str,
        exclude_resources: List[str] = None,
        resource_types: List[str] = None,
        **kwargs,
    ) -> None:
        """Write all AWS resources in this region in this service to storage.

        Any additional args will be passed into the Boto3 client methods.

        Arguments:
            service_name (str):
                The name of the service to write resources for (e.g. ``'ec2'``)
            exclude_resources (list):
                A list of service:resources to exclude (e.g. ``['ec2:instance']``)
            resource_types (list):
                A list of resource types to include (e.g. ``['instance']``)
            region_name (str):
                The name of the region to get resources from
            **kwargs: Additional keyword arguments will be passed down to the cloud interface methods.
        """
        logger.info("Writing all %s resources in %s", service_name, region_name)
        exclude_resources = exclude_resources or []
        service = self.boto3_services.get_service(service_name=service_name, region_name=region_name)
        if not service.should_query_resources_in_region:
            logger.info(
                "Skipping %s as it cannot have resources in %s",
                service_name,
                region_name,
            )
            return
        resource_types = resource_types or service.resource_types
        for resource_type in resource_types:
            service_resource = f"{service_name}:{resource_type}"
            if resource_type not in service.resource_types:
                logging.debug("Skipping %s as it is not a valid resource for %s", resource_type, service_name)
                continue
            if service_resource in exclude_resources:
                logger.info("Skipping %s as per exclude_resources", service_resource)
                continue
            if self.limit_resources is not None and service_resource not in self.limit_resources:
                logger.info("Skipping %s as per limit_resources", service_resource)
                continue

            yield from self._get_resources_of_type_in_region(
                service_name=service_name,
                resource_type=resource_type,
                region_name=region_name,
                **kwargs,
            )

    def _get_resources_of_type_in_region(
        self,
        service_name: str,
        region_name: str,
        resource_type: str = None,
        **kwargs,
    ) -> None:
        """Write all AWS resources in this region in this service to storage.

        Any additional args will be passed into the Boto3 client methods.

        Arguments:
            service_name (str):
                The name of the service to write resources for (e.g. ``'ec2'``)
            resource_type (str):
                The name of the type of the resource to write (e.g. ``'instance'``)
            region_name (str):
                The name of the region to get resources from
            **kwargs: Additional keyword arguments will be passed down to the cloud interface methods.
        """
        logger.info("Fetching %s %s from %s", service_name, resource_type, region_name)
        yield from self._get_resources_of_type(
            service_name=service_name,
            resource_type=resource_type,
            region_name=region_name,
            **kwargs,
        )

    def _get_resources_of_type(
        self, service_name: str, resource_type: str, region_name: str = None, **kwargs
    ) -> Iterator[ResourceModel]:
        """Return all resources of resource_type from Boto3.

        Arguments:
            service_name (str): The name of the service to get resource for (e.g. ``'ec2'``)
            resource_type (str): The type of resource to get resources of (e.g. ``'instance'``)
            region_name (str): The region to get resources of (e.g. ``'eu-west-1'``)
            **kwargs: Additional keyword arguments will be passed down to the Boto3 client.

        Raises:
            botocore.exceptions.ClientError: Occurs if the Boto3 Client Errors.
        """
        service = self.boto3_services.get_service(service_name=service_name, region_name=region_name)
        try:
            for resource in service.get_resources(resource_type=resource_type):
                logger.debug("Found %s", resource.urn)
                yield CloudWandererResource(
                    urn=resource.urn,
                    resource_data=resource.normalised_raw_data,
                    secondary_attributes=list(resource.get_secondary_attributes()),
                )
                for subresource in resource.get_subresources():
                    yield CloudWandererResource(
                        urn=subresource.urn,
                        resource_data=subresource.normalised_raw_data,
                        secondary_attributes=list(resource.get_secondary_attributes()),
                    )
        except botocore.exceptions.EndpointConnectionError:
            logger.info("%s %s not supported in %s", service_name, resource_type, region_name)
            return
        except botocore.exceptions.ClientError as ex:
            if ex.response["Error"]["Code"] == "InvalidAction":
                logger.info("%s %s not supported in %s", service_name, resource_type, region_name)
                return
            raise

    def cleanup_resources(
        self,
        storage_connector: BaseStorageConnector,
        urns_to_keep: List[URN] = None,
        regions: List[str] = None,
        service_names: List[str] = None,
        resource_types: List[str] = None,
        exclude_resources: List[str] = None,
    ) -> None:
        """Delete records as appropriate from a storage connector based on the supplied arguments.

        All arguments except ``storage_connector`` are optional.

        Arguments:
            storage_connector (BaseStorageConnector):
                The storage connector to delete the records from.
            urns_to_keep (List[URN]):
                A list of URNs which should not be removed from the storage_connector
            regions(list):
                The name of the region to get resources from (defaults to session default if not specified)
            service_names (str):
                The names of the services to write resources for (e.g. ``['ec2']``)
            resource_types (list):
                A list of resource types to include (e.g. ``['instance']``)
            exclude_resources (list):
                A list of service:resources to exclude (e.g. ``['ec2:instance']``)
        """
        exclude_resources = exclude_resources or []
        regions = regions or self.enabled_regions
        service_names = service_names or self.boto3_services.available_services
        for region_name in regions:
            for service_name in service_names:
                service = self.boto3_services.get_service(service_name, region_name=region_name)
                if not service.should_delete_resources_in_region:
                    logger.info(
                        "Skipping storage cleanup of %s resources as it cannot have resources in %s",
                        service_name,
                        region_name,
                    )
                    continue
                if resource_types:
                    resource_types = list(set(resource_types) & set(service.resource_types))
                else:
                    resource_types = service.resource_types
                for resource_type in resource_types:
                    service_resource = f"{service}:{resource_type}"
                    if service_resource in exclude_resources:
                        logger.info("Skipping %s as per exclude_resources", service_resource)
                    if resource_type not in service.resource_types:
                        logging.debug("Skipping %s as it is not a valid resource for %s", resource_type, service_name)
                    self._clean_resources_in_region(
                        storage_connector=storage_connector,
                        service_name=service.name,
                        resource_type=resource_type,
                        region_name=region_name,
                        current_urns=urns_to_keep,
                    )

    def _clean_resources_in_region(
        self,
        storage_connector: BaseStorageConnector,
        service_name: str,
        resource_type: str,
        region_name: str,
        current_urns: List[URN],
    ) -> None:
        """Remove all resources of this type in this region which no longer exist.

        Arguments:
            storage_connector (BaseStorageConnector):
                The storage connector that resources will be deleted from.
            service_name (str):
                The name of the service to write resources for (e.g. ``'ec2'``)
            resource_type (str):
                The name of the type of the resource to write (e.g. ``'instance'``)
            region_name (str):
                The name of the region to get resources from
                (defaults to session default if not specified)
            current_urns (List[URN]):
                A list of URNs which are still current and should not be deleted.
        """
        logger.info(
            "Cleaning up %s %s in %s from %s",
            service_name,
            resource_type,
            region_name,
            storage_connector,
        )
        storage_connector.delete_resource_of_type_in_account_region(
            service=service_name,
            resource_type=resource_type,
            account_id=self.account_id,
            region=region_name,
            urns_to_keep=current_urns,
        )
