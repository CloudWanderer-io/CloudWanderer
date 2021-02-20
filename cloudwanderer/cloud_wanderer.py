"""Main cloudwanderer module."""
import concurrent.futures
import logging
from typing import TYPE_CHECKING, Callable, Iterator, List

from cloudwanderer.cloud_wanderer_resource import CloudWandererResource

from .aws_urn import AwsUrn
from .boto3_interface import CloudWandererBoto3Interface
from .exceptions import BadRequest, ResourceNotFound
from .utils import exception_logging_wrapper

logger = logging.getLogger("cloudwanderer")

if TYPE_CHECKING:
    from .storage_connectors import BaseStorageConnector  # noqa


class CloudWanderer:
    """CloudWanderer."""

    def __init__(
        self, storage_connectors: List["BaseStorageConnector"], cloud_interface: CloudWandererBoto3Interface = None
    ) -> None:
        """Initialise CloudWanderer.

        Args:
            storage_connectors:
                CloudWanderer storage connector objects.
            cloud_interface (CloudWandererBoto3Interface):
                The cloud interface to get resources from.
                Defaults to :class:`~cloudwanderer.boto3_interface.CloudWandererBoto3Interface`.
        """
        self.storage_connectors = storage_connectors
        self.cloud_interface = cloud_interface or CloudWandererBoto3Interface()

    def write_resource(self, urn: AwsUrn, **kwargs) -> None:
        """Fetch data for and persist to storage a single resource.

        Arguments:
            urn (AwsUrn):
                The URN of the resource to write
            **kwargs:
                All additional keyword arguments will be passed down to the cloud interface client calls.
        """
        try:
            resource = self.cloud_interface.get_resource(urn=urn, **kwargs)
        except (BadRequest, ResourceNotFound):
            # Some Clouds return error 400s other than 404 when a resource is not found
            # Therefore we treat all BadRequest errors as Not Found
            resource = None
        if resource:
            list(self._write_resource(resource=resource))
        else:
            for storage_connector in self.storage_connectors:
                storage_connector.delete_resource(urn)

    def write_resources(
        self,
        regions: List[str] = None,
        service_names: List[str] = None,
        resource_types: List[str] = None,
        exclude_resources: List[str] = None,
        **kwargs,
    ) -> None:
        """Write all AWS resources in this account from all regions and all services to storage.

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
                All additional keyword arguments will be passed down to the cloud interface client calls.

        """
        urns = []
        resources = self.cloud_interface.get_resources(
            regions=regions,
            service_names=service_names,
            resource_types=resource_types,
            exclude_resources=exclude_resources,
            **kwargs,
        )
        for resource in resources:
            urns.extend(list(self._write_resource(resource)))

        for storage_connector in self.storage_connectors:
            self.cloud_interface.cleanup_resources(
                storage_connector=storage_connector,
                regions=regions,
                service_names=service_names,
                resource_types=resource_types,
                urns_to_keep=urns,
                **kwargs,
            )

    def write_resources_concurrently(
        self, cloud_interface_generator: Callable, exclude_resources: List[str] = None, concurrency: int = 10, **kwargs
    ) -> None:
        """Write all AWS resources in this account from all regions and all services to storage.

        Any additional args will be passed into the cloud interface's ``get_`` methods.

        Arguments:
            exclude_resources (list):
                exclude_resources (list): A list of service:resources to exclude (e.g. ``['ec2:instance']``)
            concurrency (int):
                Number of query threads to invoke concurrently.
                If the number of threads exceeds the number of regions by at least two times
                multiple services to be queried concurrently in each region.
                **WARNING:** Experimental. Complete data capture depends heavily on the thread safeness of the
                storage connector and has not been thoroughly tested!
            cloud_interface_generator (Callable): A method which returns a new cloud interface session when called.
                This helps prevent non-threadsafe cloud interfaces from interfering with each others.
            **kwargs: Additional keyword arguments will be passed down to the cloud interface methods.
        """
        logger.info("Writing resources in all regions")
        logger.warning("Using concurrency of: %s - CONCURRENCY IS EXPERIMENTAL", concurrency)
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            for region_name in self.cloud_interface.enabled_regions:
                cw = CloudWanderer(
                    storage_connectors=self.storage_connectors, cloud_interface=cloud_interface_generator()
                )
                executor.submit(
                    exception_logging_wrapper,
                    method=cw.write_resources_in_region,
                    exclude_resources=exclude_resources,
                    region_name=region_name,
                    **kwargs,
                )

    def _write_resource(self, resource: CloudWandererResource) -> Iterator[AwsUrn]:
        print("received: ", resource)
        for storage_connector in self.storage_connectors:
            print(resource)
            storage_connector.write_resource(resource)
        yield resource.urn
