import graphviz
from botocore import xform_name

from cloudwanderer import CloudWanderer, CloudWandererAWSInterface
from cloudwanderer.exceptions import UnsupportedResourceTypeError
from cloudwanderer.models import RelationshipDirection

interface = CloudWandererAWSInterface()
aws = graphviz.Digraph(comment="Cloud Wanderer AWS Resources", format="png")

# aws.node("AWS", "AWS")
# aws.edge_attr["style"] = "invisible"
# aws.edge_attr.update(arrowhead="none")
with aws.subgraph(name="services") as services_graph:

    services_graph.graph_attr.update(rank="same")
    for service_name in interface.cloudwanderer_boto3_session.get_available_resources():

        service = interface.cloudwanderer_boto3_session.resource(service_name)

        # services_graph.node(service_name, service_name)
        # services_graph.edge("AWS", service_name)

        with aws.subgraph(name=f"cluster resource types {service_name}") as resource_types_graph:
            resource_types_graph.graph_attr.update(rank="same", newrank="true", label=service_name)
            resource_types_graph.edge_attr.update(arrowhead="vee", style="")
            for resource_type_boto3 in service.get_available_subresources():
                resource_type = xform_name(resource_type_boto3)
                service_resource_name = f"{service_name} {resource_type}"
                print(f"creating node {service_resource_name}")
                resource_types_graph.node(service_resource_name, service_resource_name)
                # services_graph.edge(service_name, service_resource_name)
                try:
                    resource = service.resource(resource_type, empty_resource=True)
                except UnsupportedResourceTypeError:
                    continue
                for relationship in resource.resource_map.relationships:
                    partner_service_resource_name = f"{relationship.service} {relationship.resource_type}"
                    if relationship.direction == RelationshipDirection.INBOUND:
                        print(f"creating edge {partner_service_resource_name} > {service_resource_name}")
                        services_graph.edge(partner_service_resource_name, service_resource_name)
                    else:
                        print(f"creating edge {service_resource_name} > {partner_service_resource_name}")
                        services_graph.edge(service_resource_name, partner_service_resource_name)

aws.render("resources", view=True)
