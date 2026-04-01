import { GbApiClient } from '@gb/api-client';
import type { GraphNodeType } from '@gb/schemas';
import { useEffect, useMemo, useState } from 'react';
import ReactFlow, { Background, Controls, MiniMap, type Edge, type Node } from 'reactflow';
import 'reactflow/dist/style.css';

interface GraphPageProps {
  baseUrl: string;
}

interface GraphFlowNodeData {
  label: string;
  nodeType: GraphNodeType;
  group?: string;
  metadata: Record<string, unknown>;
}

const NODE_TYPES: GraphNodeType[] = ['strategy', 'model', 'data_source', 'risk_rule', 'execution_adapter', 'job'];

export function GraphPage({ baseUrl }: GraphPageProps): JSX.Element {
  const client = useMemo(() => new GbApiClient({ baseHttpUrl: baseUrl }), [baseUrl]);
  const [nodes, setNodes] = useState<Array<Node<GraphFlowNodeData>>>([]);
  const [edges, setEdges] = useState<Array<Edge>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTypes, setSelectedTypes] = useState<Set<GraphNodeType>>(() => new Set(NODE_TYPES));
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async (): Promise<void> => {
      setLoading(true);
      setError(null);
      try {
        const topology = await client.getGraphTopology();
        if (cancelled) return;

        setNodes(
          topology.nodes.map((node, index) => ({
            id: node.id,
            data: {
              label: `${node.label} (${node.type})`,
              nodeType: node.type,
              group: node.group,
              metadata: node.metadata,
            },
            position: {
              x: (index % 14) * 200,
              y: Math.floor(index / 14) * 90,
            },
          }))
        );

        setEdges(
          topology.edges.map((edge) => ({
            id: edge.id,
            source: edge.source,
            target: edge.target,
            label: edge.label,
            animated: false,
          }))
        );
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : 'Failed to load graph topology.');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void load();
    return () => {
      cancelled = true;
    };
  }, [client]);

  const visibleNodes = useMemo(
    () => nodes.filter((node) => selectedTypes.has(node.data.nodeType)),
    [nodes, selectedTypes]
  );

  const visibleNodeIds = useMemo(() => new Set(visibleNodes.map((node) => node.id)), [visibleNodes]);

  const visibleEdges = useMemo(
    () => edges.filter((edge) => visibleNodeIds.has(edge.source) && visibleNodeIds.has(edge.target)),
    [edges, visibleNodeIds]
  );

  const selectedNode = useMemo(() => visibleNodes.find((node) => node.id === selectedNodeId), [visibleNodes, selectedNodeId]);

  const toggleType = (type: GraphNodeType): void => {
    setSelectedTypes((previous) => {
      const next = new Set(previous);
      if (next.has(type)) {
        next.delete(type);
      } else {
        next.add(type);
      }
      return next;
    });
  };

  return (
    <section className="graph-page">
      <header>
        <h2>Graph</h2>
        <p className="muted">Topology explorer scaffold powered by React Flow.</p>
      </header>

      <div className="graph-controls card">
        <h3>Filters</h3>
        <div className="graph-filter-grid">
          {NODE_TYPES.map((type) => (
            <label key={type}>
              <input type="checkbox" checked={selectedTypes.has(type)} onChange={() => toggleType(type)} /> {type}
            </label>
          ))}
        </div>
        <p className="muted">
          Showing {visibleNodes.length} / {nodes.length} nodes and {visibleEdges.length} / {edges.length} edges
        </p>
      </div>

      {loading ? <p>Loading topology…</p> : null}
      {error ? <p className="error">{error}</p> : null}

      <div className="graph-layout">
        <div className="graph-canvas card">
          <ReactFlow
            nodes={visibleNodes}
            edges={visibleEdges}
            fitView
            onNodeClick={(_, node) => setSelectedNodeId(node.id)}
            minZoom={0.2}
            maxZoom={1.8}
            proOptions={{ hideAttribution: true }}
          >
            <MiniMap zoomable pannable />
            <Background />
            <Controls />
          </ReactFlow>
        </div>

        <aside className="graph-detail card">
          <h3>Node details</h3>
          {!selectedNode ? (
            <p className="muted">Select a node to inspect metadata.</p>
          ) : (
            <>
              <p>
                <strong>ID:</strong> {selectedNode.id}
              </p>
              <p>
                <strong>Type:</strong> {String(selectedNode.data.nodeType)}
              </p>
              <p>
                <strong>Group:</strong> {String(selectedNode.data.group ?? 'n/a')}
              </p>
              <pre>{JSON.stringify(selectedNode.data.metadata, null, 2)}</pre>
            </>
          )}
        </aside>
      </div>
    </section>
  );
}
