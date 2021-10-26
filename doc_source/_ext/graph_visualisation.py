"""Create a graphviz visualisation of the resource's relationships."""
from pathlib import Path

import graphviz
from botocore import xform_name

from cloudwanderer import CloudWandererAWSInterface
from cloudwanderer.exceptions import UnsupportedResourceTypeError
from cloudwanderer.models import RelationshipDirection

interface = CloudWandererAWSInterface()


class GraphManager:
    def __init__(self, path=".") -> None:
        self.path = Path(path)
        self.graph_dict = {}

    def get_graph(self, graph_name: str) -> "graphviz.DiGraph":
        """Get or create a graph if one does not exist with this name.

        Arguments:
            graph_name: The name of the graph
        """
        if graph_name not in self.graph_dict:
            self.graph_dict[graph_name] = graphviz.Digraph(
                comment="Cloud Wanderer AWS Resources", engine="dot", format="png"
            )
            self.graph_dict[graph_name].graph_attr.update(overlap="false", rankdir="LR")
            self.graph_dict[graph_name].edge_attr.update(arrowhead="vee", style="")

        return self.graph_dict[graph_name]

    def add_edge_to_graph(self, source_node: str, destination_node: str) -> None:
        """Add an edge to both the source node and the destination nodes' graphs.

        Arguments:
            source_node: the name of the node the edge starts at
            destination_node: the nname of the node the edge ends at
        """
        print(f"creating edge {source_node} > {destination_node}")
        source_graph = self.get_graph(source_node)
        destination_graph = self.get_graph(destination_node)

        source_graph.edge(source_node, destination_node)
        destination_graph.edge(source_node, destination_node)

    def render_all(self) -> None:
        """Render the PNGs"""
        for resource_name, graph in self.graph_dict.items():
            file_path = self.path / Path(resource_name + ".gv")
            print(f"Rendering {resource_name} to {file_path}")
            graph.render(file_path, "png", view=False)

    def generate_graphs(self) -> None:
        """Generate the graphs from the service resource relationships"""
        for service_name in interface.cloudwanderer_boto3_session.get_available_resources():

            service = interface.cloudwanderer_boto3_session.resource(service_name)

            for resource_type_boto3 in service.get_available_subresources():
                resource_type = xform_name(resource_type_boto3)
                service_resource_name = f"{service_name}_{resource_type}"

                try:
                    resource = service.resource(resource_type, empty_resource=True)
                except UnsupportedResourceTypeError:
                    continue
                for dependent_resource_type in resource.dependent_resource_types:
                    partner_service_resource_name = f"{service_name}_{dependent_resource_type}"
                    self.add_edge_to_graph(service_resource_name, partner_service_resource_name)
                for relationship in resource.resource_map.relationships:
                    partner_service_resource_name = f"{relationship.service}_{relationship.resource_type}"
                    if relationship.direction == RelationshipDirection.INBOUND:
                        self.add_edge_to_graph(partner_service_resource_name, service_resource_name)
                    else:
                        self.add_edge_to_graph(service_resource_name, partner_service_resource_name)
