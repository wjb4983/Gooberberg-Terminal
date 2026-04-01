from app.schemas import GraphEdge, GraphNode, GraphNodeType, GraphTopologyResponse

NODE_TYPES: list[GraphNodeType] = [
    GraphNodeType.STRATEGY,
    GraphNodeType.MODEL,
    GraphNodeType.DATA_SOURCE,
    GraphNodeType.RISK_RULE,
    GraphNodeType.EXECUTION_ADAPTER,
    GraphNodeType.JOB,
]


def get_mock_topology(node_count: int = 120) -> GraphTopologyResponse:
    nodes: list[GraphNode] = []
    for idx in range(node_count):
        node_type = NODE_TYPES[idx % len(NODE_TYPES)]
        nodes.append(
            GraphNode(
                id=f"n-{idx}",
                type=node_type,
                label=f"{node_type.value.replace('_', ' ').title()} {idx + 1}",
                group=f"cluster-{idx % 8}",
                metadata={"mock": True, "index": idx},
            )
        )

    edges: list[GraphEdge] = []
    for idx in range(node_count - 1):
        edges.append(
            GraphEdge(
                id=f"e-{idx}-{idx + 1}",
                source=f"n-{idx}",
                target=f"n-{idx + 1}",
                label="depends_on",
            )
        )

        if idx + 6 < node_count and idx % 3 == 0:
            edges.append(
                GraphEdge(
                    id=f"e-{idx}-{idx + 6}",
                    source=f"n-{idx}",
                    target=f"n-{idx + 6}",
                    label="feeds",
                )
            )

    return GraphTopologyResponse(nodes=nodes, edges=edges)
