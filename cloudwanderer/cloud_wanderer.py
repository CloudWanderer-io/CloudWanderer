"""Main cloudwanderer module."""
from cloudwanderer.cloud_wanderer_resource import CloudWandererResource
from typing import List
import logging
from typing import TYPE_CHECKING, Iterator, Callable
import concurrent.futures
from .utils import exception_logging_wrapper
from .boto3_interface import CloudWandererBoto3Interface
from .aws_urn import AwsUrn

logger = logging.getLogger('cloudwanderer')

if TYPE_CHECKING:
    from .storage_connectors import BaseStorageConnector  # noqa


class CloudWanderer():
    """CloudWanderer."""

    def __init__(
            self, storage_connectors: List['BaseStorageConnector'],
            cloud_interface: CloudWandererBoto3Interface = None) -> None:
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

    def write_resources(
            self, **kwargs) -> None:
        """Write all AWS resources in this account from all regions and all services to storage.

        All arguments are optional.

        Arguments:
            kwargs: Optional arguments narrowing the scope of the resources returned.

        Keyword Arguments:
            urn (~cloudwanderer.aws_urn.AwsUrn): The AWS URN of the resource to return
            account_id (:class:`str`): AWS Account ID
            region (:class:`str`): AWS region (e.g. ``'eu-west-2'``)
            service (:class:`str`): Service name (e.g. ``'ec2'``)
            resource_type (:class:`str`): Resource Type (e.g. ``'instance'``)
        """
        urns = []
        for resource in self.cloud_interface.get_resources(**kwargs):
            urns.extend(list(self._write_resource(resource)))

        for storage_connector in self.storage_connectors:
            self.cloud_interface.cleanup_resources(
                storage_connector=storage_connector, urns_to_keep=urns, **kwargs)

    def write_resources_concurrently(
            self, cloud_interface_generator: Callable, exclude_resources: List[str] = None, concurrency: int = 10,
            **kwargs) -> None:
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
        logger.info('Writing resources in all regions')
        logger.warning('Using concurrency of: %s - CONCURRENCY IS EXPERIMENTAL', concurrency)
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            for region_name in self.cloud_interface.enabled_regions:
                cw = CloudWanderer(
                    storage_connectors=self.storage_connectors,
                    cloud_interface=cloud_interface_generator()
                )
                executor.submit(
                    exception_logging_wrapper,
                    method=cw.write_resources_in_region,
                    exclude_resources=exclude_resources,
                    region_name=region_name,
                    **kwargs
                )

    def _write_resource(self, resource: CloudWandererResource) -> Iterator[AwsUrn]:
        for storage_connector in self.storage_connectors:
            storage_connector.write_resource(resource)
        yield resource.urn
