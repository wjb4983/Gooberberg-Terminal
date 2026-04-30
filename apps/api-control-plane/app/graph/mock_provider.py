from app.schemas import GraphEdge, GraphNode, GraphNodeType, GraphTopologyResponse


def get_mock_topology() -> GraphTopologyResponse:
    nodes = [
        GraphNode(id="strategy:demo", type=GraphNodeType.STRATEGY, label="Demo Strategy", group="demo", metadata={"mock": True}),
        GraphNode(id="model:demo", type=GraphNodeType.MODEL, label="Demo Model", group="demo", metadata={"mock": True}),
        GraphNode(id="dataset:demo", type=GraphNodeType.DATA_SOURCE, label="Demo Dataset", group="demo", metadata={"mock": True}),
        GraphNode(id="deployment:demo", type=GraphNodeType.EXECUTION_ADAPTER, label="Demo Deployment", group="demo", metadata={"mock": True}),
        GraphNode(id="run:demo", type=GraphNodeType.JOB, label="Demo Run", group="demo", metadata={"mock": True}),
    ]
    edges = [
        GraphEdge(id="e1", source="strategy:demo", target="model:demo", label="uses"),
        GraphEdge(id="e2", source="model:demo", target="dataset:demo", label="trained_on"),
        GraphEdge(id="e3", source="run:demo", target="strategy:demo", label="executes"),
        GraphEdge(id="e4", source="deployment:demo", target="strategy:demo", label="deploys"),
    ]
    return GraphTopologyResponse(nodes=nodes, edges=edges)
