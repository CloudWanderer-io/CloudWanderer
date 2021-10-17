import logging
from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional

from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection
from gremlin_python.process.anonymous_traversal import traversal
from gremlin_python.process.graph_traversal import __
from gremlin_python.process.traversal import Cardinality, T, P, Traversal

from cloudwanderer.models import RelationshipDirection

from ..cloud_wanderer_resource import CloudWandererResource
from ..exceptions import ResourceNotFoundError
from ..urn import URN, PartialUrn
from .base_connector import BaseStorageConnector

logger = logging.getLogger(__name__)

# TODO: figure out how to get previously unknown resources to migrate edges to known resource once discovered.
# eg: get vpc to associate its subnet with itself once discovered (if they were previously associated with unknown vpc vertex.)


def generate_primary_label(urn: PartialUrn) -> str:
    return "_".join([urn.cloud_name, urn.service, urn.resource_type])


def generate_edge_id(source_urn, destination_urn):
    return f"{source_urn}#{destination_urn}"


class GremlinStorageConnector(BaseStorageConnector):
    def __init__(self, endpoint_url: str, supports_multiple_labels=False, **kwargs):
        """
        Arguments:
            supports_multiple_labels: Some GraphDBs (Neptune/Neo4J) support multiple labels on a single vertex.
        """
        self.endpoint_url = endpoint_url
        self.supports_multiple_labels = supports_multiple_labels
        self.connection_args = kwargs

    def init(self):
        ...

    def open(self):
        self.connection = DriverRemoteConnection(f"{self.endpoint_url}/gremlin", "g", **self.connection_args)
        self.g = traversal().withRemote(self.connection)

    def close(self):
        self.connection.close()

    def write_resource(self, resource: CloudWandererResource) -> None:
        """Persist a single resource to storage.

        Arguments:
            resource (CloudWandererResource): The CloudWandererResource to write.
        """
        self._write_resource(resource)
        self._write_dependent_resource_edges(resource)

    def _write_resource(self, resource: CloudWandererResource) -> None:
        primary_label = generate_primary_label(resource.urn)

        traversal = self._write_vertex(vertex_id=str(resource.urn), vertex_labels=[primary_label])
        traversal = (
            traversal.property(Cardinality.single, "_cloud_name", resource.urn.cloud_name)
            .property(Cardinality.single, "_account_id", resource.urn.account_id)
            .property(Cardinality.single, "_region", resource.urn.region)
            .property(Cardinality.single, "_service", resource.urn.service)
            .property(Cardinality.single, "_resource_type", resource.urn.resource_type)
            .property(Cardinality.single, "_discovery_time", resource.discovery_time.isoformat())
        )
        for id_part in resource.urn.resource_id_parts:
            traversal.property(Cardinality.set_, "_resource_id_parts", id_part)
        traversal = self._write_properties(
            traversal=traversal, properties=resource.cloudwanderer_metadata.resource_data
        )
        traversal.next()

        self._write_relationships(resource)
        if not resource.urn.is_partial:
            self._repoint_vertex_edges(vertex_label=primary_label, new_resource_urn=resource.urn)

    def _write_dependent_resource_edges(self, resource: CloudWandererResource) -> None:
        for dependent_urn in resource.dependent_resource_urns:
            edge_id = generate_edge_id(resource.urn, dependent_urn)
            logger.debug("writing edge id %s", edge_id)
            self._write_edge(
                edge_id=edge_id,
                edge_label="has",
                source_vertex_id=str(resource.urn),
                destination_vertex_id=str(dependent_urn),
            ).next()

    def _write_relationships(self, resource: CloudWandererResource) -> None:

        for relationship in resource.relationships:
            inferred_partner_urn = str(relationship.partial_urn)
            try:
                pre_existing_resource_id = self._lookup_resource(relationship.partial_urn).next().id
            except StopIteration:
                pre_existing_resource_id = None

            if pre_existing_resource_id:
                self._write_relationship_edge(
                    resource_id=str(resource.urn),
                    relationship_resource_id=pre_existing_resource_id,
                    direction=relationship.direction,
                )
                if pre_existing_resource_id != inferred_partner_urn:

                    self._delete_relationship_edge(
                        resource_id=str(resource.urn),
                        relationship_resource_id=inferred_partner_urn,
                        direction=relationship.direction,
                    )
                continue
            logger.debug("Writing inferred resource %s", inferred_partner_urn)
            self._write_resource(CloudWandererResource(urn=relationship.partial_urn, resource_data={}))
            self._write_relationship_edge(
                resource_id=str(resource.urn),
                relationship_resource_id=inferred_partner_urn,
                direction=relationship.direction,
            )

    def _repoint_vertex_edges(self, vertex_label: str, new_resource_urn: URN) -> None:
        # https://tinkerpop.apache.org/docs/current/recipes/#edge-move

        resources_of_the_same_type = self.g.V().as_("old_vertex").hasLabel(vertex_label)
        for id_part in new_resource_urn.resource_id_parts:
            resources_of_the_same_type.has("_resource_id_parts", id_part)
        resources_with_same_id_but_unknown = (
            resources_of_the_same_type.properties()
            .hasValue("unknown")
            .or_(__.hasKey("_account_id"), __.hasKey("_region"))
            .select("old_vertex")
        )
        # Outbound
        old_vertices_outbound_edges = resources_with_same_id_but_unknown.outE().as_("e1")
        old_outbound_edges_partner_vertex = old_vertices_outbound_edges.inV().as_("b")

        new_vertex = old_outbound_edges_partner_vertex.V(str(new_resource_urn)).as_("new_vertex")
        add_old_outbound_edges_to_new_vertex = (
            new_vertex.addE("has")
            .to("b")
            .as_("e2")
            .sideEffect(
                __.select("e1")
                .properties()
                .unfold()
                .as_("p")
                .select("e2")
                .property(__.select("p").key(), __.select("p").value())
            )
        )
        drop_old_edges = add_old_outbound_edges_to_new_vertex.select("e1").drop()

        # Inbound
        old_vertices_inbound_edges = drop_old_edges.select("old_vertex").inE().as_("e3")
        old_inbound_edges_partner_vertex = old_vertices_inbound_edges.inV().as_("c")

        new_vertex = old_inbound_edges_partner_vertex.select("new_vertex")
        add_old_inbound_edges_to_new_vertex = (
            new_vertex.addE("has")
            .from_("c")
            .as_("e4")
            .sideEffect(
                __.select("e3")
                .properties()
                .unfold()
                .as_("p")
                .select("e4")
                .property(__.select("p").key(), __.select("p").value())
            )
        )
        drop_old_edges = add_old_inbound_edges_to_new_vertex.select("e3").drop()

        # Delete old vertex
        delete_old_vertex = drop_old_edges.select("old_vertex").drop()

        # Execute
        delete_old_vertex.iterate()

    def _delete_relationship_edge(
        self, resource_id: str, relationship_resource_id: str, direction: RelationshipDirection
    ) -> None:
        if direction == RelationshipDirection.INBOUND:
            self._delete_edge(generate_edge_id(relationship_resource_id, resource_id))
        else:
            self._delete_edge(generate_edge_id(resource_id, relationship_resource_id))

    def _write_relationship_edge(
        self, resource_id: str, relationship_resource_id: str, direction: RelationshipDirection
    ) -> None:
        if direction == RelationshipDirection.INBOUND:
            self._write_edge(
                edge_id=generate_edge_id(relationship_resource_id, resource_id),
                edge_label="has",
                source_vertex_id=relationship_resource_id,
                destination_vertex_id=resource_id,
            ).next()
        else:
            self._write_edge(
                edge_id=generate_edge_id(resource_id, relationship_resource_id),
                edge_label="has",
                source_vertex_id=resource_id,
                destination_vertex_id=relationship_resource_id,
            ).next()

    def _lookup_resource(self, partial_urn: PartialUrn) -> Traversal:
        vertex_label = generate_primary_label(partial_urn)
        traversal = (
            self.g.V()
            .hasLabel(vertex_label)
            .has("_cloud_name", partial_urn.cloud_name)
            .has("_service", partial_urn.service)
            .has("_resource_type", partial_urn.resource_type)
        )
        for id_part in partial_urn.resource_id_parts:
            traversal.has("_resource_id_parts", id_part)
        if partial_urn.account_id != "unknown":
            traversal.has("_account_id", partial_urn.account_id)
        if partial_urn.region != "unknown":
            traversal.has("_region", partial_urn.region)
        return traversal

    def _write_vertex(self, vertex_id: str, vertex_labels: List[str]) -> Traversal:
        logger.debug("Writing vertex %s", vertex_id)
        if self.supports_multiple_labels:
            vertex_label = "::".join(vertex_labels)
        else:
            vertex_label = vertex_labels[0]
        return self.g.V(vertex_id).fold().coalesce(__.unfold(), __.addV(vertex_label).property(T.id, vertex_id))

    def _write_properties(self, traversal: Traversal, properties: Dict[str, Any]) -> Traversal:
        logger.debug("Writing properties: %s", properties)
        for property_name, property_value in properties.items():
            traversal = traversal.property(Cardinality.single, str(property_name), str(property_value))
        return traversal

    def _write_edge(
        self, edge_id: str, edge_label: str, source_vertex_id: str, destination_vertex_id: str
    ) -> Traversal:
        logger.debug("Writing edge between %s and %s", source_vertex_id, destination_vertex_id)
        return (
            self.g.V(source_vertex_id)
            .as_("source")
            .V(destination_vertex_id)
            .coalesce(
                __.inE().where(__.outV().as_("source")),
                __.addE(edge_label).from_("source").property(T.id, edge_id),
            )
        )

    def _delete_edge(self, edge_id: str) -> Traversal:
        logger.debug("Deleting edge %s", edge_id)
        deleted_edges = self.g.E(edge_id).drop().toList()
        if deleted_edges:
            logger.debug("Deleted edges %s", deleted_edges)

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
        logger.info("Deleting resource %s", urn)
        deleted_resources = self.g.V(str(urn)).sideEffect(__.drop()).toList()
        if deleted_resources:
            logger.debug("Deleted %s", deleted_resources)

    def delete_resource_of_type_in_account_region(
        self,
        cloud_name: str,
        service: str,
        resource_type: str,
        account_id: str,
        region: str,
        cutoff: Optional[datetime],
    ) -> None:
        """Delete resources of type in account and region unless in list of URNs.

        This is used primarily to clean up old resources.

        Arguments:
            cloud_name: The name of the cloud in question
            account_id: Cloud Account ID
            region: Cloud region (e.g. ``'eu-west-2'``)
            service: Service name (e.g. ``'ec2'``)
            resource_type: Resource Type (e.g. ``'instance'``)
            cutoff: Delete any resource discovered before this time
        """
        partial_urn = PartialUrn(
            cloud_name=cloud_name,
            service=service,
            account_id=account_id,
            region=region,
            resource_type=resource_type,
        )
        logger.debug("Deleting resources that match %s that were discovered before %s", partial_urn, cutoff)
        traversal = self._lookup_resource(partial_urn=partial_urn)
        if cutoff:
            traversal.where(__.values("_discovery_time").is_(P.lt(cutoff.isoformat())))
        deleted_vertices = traversal.sideEffect(__.drop()).toList()
        if deleted_vertices:
            logger.debug("Deleted %s", deleted_vertices)
