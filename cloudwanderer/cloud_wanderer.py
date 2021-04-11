"""Main cloudwanderer module."""
import concurrent.futures
import logging
from typing import Callable, Iterator, List, NamedTuple

from .aws_interface import CloudWandererAWSInterface
from .cloud_wanderer_resource import CloudWandererResource
from .storage_connectors import BaseStorageConnector
from .urn import URN
from .utils import exception_logging_wrapper

logger = logging.getLogger("cloudwanderer")


class CloudWanderer:
    """CloudWanderer."""

    def __init__(
        self, storage_connectors: List["BaseStorageConnector"], cloud_interface: CloudWandererAWSInterface = None
    ) -> None:
        """Initialise CloudWanderer.

        Args:
            storage_connectors (List[BaseStorageConnector]):
                CloudWanderer storage connector objects.
            cloud_interface (CloudWandererAWSInterface):
                The cloud interface to get resources from.
                Defaults to :class:`~cloudwanderer.aws_interface.CloudWandererAWSInterface`.
        """
        self.storage_connectors = storage_connectors
        self.cloud_interface = cloud_interface or CloudWandererAWSInterface()

    def write_resource(self, urn: URN, **kwargs) -> None:
        """Fetch data for and persist to storage a single resource and its subresources.

        If the resource does not exist it will be deleted from the storage connectors.

        Arguments:
            urn (URN):
                The URN of the resource to write
            **kwargs:
                All additional keyword arguments will be passed down to the cloud interface client calls.
        """
        resources = list(self.cloud_interface.get_resource(urn=urn, **kwargs))

        for resource in resources:
            list(self._write_resource(resource=resource))
        if not resources:
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
        actions = self.cloud_interface.get_actions(
            regions=regions,
            service_names=service_names,
            resource_types=resource_types,
            exclude_resources=exclude_resources,
        )
        for action_set in actions:
            for get_action in action_set.get_actions:
                resources = self.cloud_interface.get_resources(
                    region=get_action.region,
                    service_name=get_action.service_name,
                    resource_type=get_action.resource_type,
                )
                for resource in resources:
                    urns.extend(list(self._write_resource(resource)))
            for cleanup_action in action_set.cleanup_actions:
                for storage_connector in self.storage_connectors:
                    storage_connector.delete_resource_of_type_in_account_region(
                        account_id=self.cloud_interface.account_id,
                        region=cleanup_action.region,
                        service=cleanup_action.service_name,
                        resource_type=cleanup_action.resource_type,
                        urns_to_keep=urns,
                    )

    def write_resources_concurrently(
        self,
        cloud_interface_generator: Callable,
        storage_connector_generator: Callable,
        exclude_resources: List[str] = None,
        concurrency: int = 10,
        **kwargs,
    ) -> List["CloudWandererConcurrentWriteThreadResult"]:
        """Write all AWS resources in this account from all regions and all services to storage.

        Any additional args will be passed into the cloud interface's ``get_`` methods.
        **WARNING:** Experimental.

        Arguments:
            exclude_resources (list):
                exclude_resources (list): A list of service:resources to exclude (e.g. ``['ec2:instance']``)
            concurrency (int):
                Number of query threads to invoke concurrently.
            cloud_interface_generator (Callable):
                 A method which returns a new cloud interface session when called.
                This helps prevent non-threadsafe cloud interfaces from interfering with each others.
            storage_connector_generator (Callable):
                A method which returns a list of storage connectors when called.
                The returned connectors should be instances of the same connectors each time the method is called.
                These connectors do **not** need to be thread safe and will be returned at the end of execution.
            **kwargs:
                Additional keyword arguments will be passed down to the cloud interface methods.
        """
        logger.info("Writing resources in all regions")
        logger.warning("Using concurrency of: %s - CONCURRENCY IS EXPERIMENTAL", concurrency)
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            threads = []
            for region_name in self.cloud_interface.enabled_regions:
                cw = CloudWanderer(
                    storage_connectors=storage_connector_generator(), cloud_interface=cloud_interface_generator()
                )
                threads.append(
                    executor.submit(
                        exception_logging_wrapper,
                        method=cw.write_resources,
                        exclude_resources=exclude_resources,
                        regions=[region_name],
                        return_value=cw.storage_connectors,
                        **kwargs,
                    )
                )
        thread_results: List[CloudWandererConcurrentWriteThreadResult] = []
        for thread in threads:
            result = thread.result()
            if result:
                thread_results.append(CloudWandererConcurrentWriteThreadResult(storage_connectors=result))
        return thread_results

    def _write_resource(self, resource: CloudWandererResource) -> Iterator[URN]:
        for storage_connector in self.storage_connectors:
            storage_connector.write_resource(resource)
        yield resource.urn


class CloudWandererConcurrentWriteThreadResult(NamedTuple):
    """The result from write_resources_concurrently."""

    storage_connectors: BaseStorageConnector
