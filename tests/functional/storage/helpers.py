from gremlin_python.process.graph_traversal import __  # type: ignore


def get_vertex_and_edges(gremlin_connector, urn):
    return (
        gremlin_connector.g.V(gremlin_connector.generate_vertex_id(urn))
        .as_("v1")
        .bothE()
        .as_("e")
        .outV()
        .as_("v2")
        .select("v1", "e", "v2")
        .by(__.valueMap(True))
        .toList()
    )
