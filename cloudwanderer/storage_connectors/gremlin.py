from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional

from gremlin_python.process.traversal import Cardinality, Traversal
from ..urn import URN
from ..cloud_wanderer_resource import CloudWandererResource
from .base_connector import BaseStorageConnector
from gremlin_python.process.graph_traversal import __
from gremlin_python.process.traversal import T
from gremlin_python.process.anonymous_traversal import traversal
from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection
import logging

logger = logging.getLogger(__name__)


class GremlinStorageConnector(BaseStorageConnector):
    def __init__(self, endpoint_url: str, supports_multiple_labels=False):
        """
        Arguments:
            supports_multiple_labels: Some GraphDBs (Neptune/Neo4J) support mutiple labels on a single vertex.
        """
        self.endpoint_url = endpoint_url
        self.supports_multiple_labels = supports_multiple_labels
        self.g = traversal().withRemote(DriverRemoteConnection(f"{self.endpoint_url}/gremlin", "g"))

    def init(self):
        ...

    def write_resource(self, resource: CloudWandererResource) -> None:
        """Persist a single resource to storage.

        Arguments:
            resource (CloudWandererResource): The CloudWandererResource to write.
        """
        primary_label = "_".join([resource.urn.cloud_name, resource.urn.service, resource.urn.resource_type])

        traversal = self._write_vertex(vertex_id=str(resource.urn), vertex_labels=[primary_label])
        traversal = self._write_properties(
            traversal=traversal, properties=resource.cloudwanderer_metadata.resource_data
        )
        traversal.next()

        for dependent_urn in resource.subresource_urns:
            edge_id = f"{resource.urn}#{dependent_urn}"
            self._write_edge(
                edge_id=edge_id,
                edge_label="has",
                source_vertex_id=str(resource.urn),
                destination_vertex_id=str(dependent_urn),
            ).next()

    def _write_vertex(self, vertex_id: str, vertex_labels: List[str]) -> Traversal:
        if self.supports_multiple_labels:
            vertex_label = "::".join(vertex_labels)
        else:
            vertex_label = vertex_labels[0]
        return self.g.V(vertex_id).fold().coalesce(__.unfold(), __.addV(vertex_label).property(T.id, vertex_id))

    def _write_properties(self, traversal: Traversal, properties: Dict[str, Any]) -> Traversal:
        for property_name, property_value in properties.items():
            traversal = traversal.property(Cardinality.single, str(property_name), str(property_value))
        return traversal

    def _write_edge(
        self, edge_id: str, edge_label: str, source_vertex_id: str, destination_vertex_id: str
    ) -> Traversal:

        return (
            self.g.V(source_vertex_id)
            .as_("source")
            .V(destination_vertex_id)
            .coalesce(
                __.inE().where(__.outV().as_("source")),
                __.addE(edge_label).from_("source").property(T.id, edge_id),
            )
        )

    def read_all(self) -> Iterator[dict]:
        """Return all records from storage."""

    def read_resource(self, urn: URN) -> Optional[CloudWandererResource]:
        """Return a resource matching the supplied urn from storage.

        Arguments:
            urn (URN): The AWS URN of the resource to return
        """

    def read_resources(
        self,
        account_id: str = None,
        region: str = None,
        service: str = None,
        resource_type: str = None,
        urn: URN = None,
    ) -> Iterator["CloudWandererResource"]:
        """Yield a resource matching the supplied urn from storage.

        All arguments are optional.

        Arguments:
            urn: The AWS URN of the resource to return
            account_id: AWS Account ID
            region: AWS region (e.g. ``'eu-west-2'``)
            service: Service name (e.g. ``'ec2'``)
            resource_type: Resource Type (e.g. ``'instance'``)
        """

    def delete_resource(self, urn: URN) -> None:
        """Delete this resource and all its resource attributes.

        Arguments:
            urn (URN): The URN of the resource to delete
        """

    def delete_resource_of_type_in_account_region(
        self, service: str, resource_type: str, account_id: str, region: str, cutoff: Optional[datetime]
    ) -> None:
        """Delete resources of type in account and region unless in list of URNs.

        This is used primarily to clean up old resources.

        Arguments:
            account_id (str): AWS Account ID
            region (str): AWS region (e.g. ``'eu-west-2'``)
            service (str): Service name (e.g. ``'ec2'``)
            resource_type (str): Resource Type (e.g. ``'instance'``)
            urns_to_keep (List[cloudwanderer.urn.URN]): A list of resources not to delete
        """
