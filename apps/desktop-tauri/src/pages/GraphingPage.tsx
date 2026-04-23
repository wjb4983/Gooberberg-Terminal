import { GbApiClient } from '@gb/api-client';
import type { GraphEdge, GraphNode } from '@gb/schemas';
import { useEffect, useMemo, useState } from 'react';
import CytoscapeComponent from 'react-cytoscapejs';
import Plot from 'react-plotly.js';

interface GraphingPageProps {
  baseUrl: string;
}

type GraphTab = 'relationship' | 'plots';

interface ViewportState {
  x: number;
  y: number;
  width: number;
  height: number;
  zoom: number;
}

const DEFAULT_VIEWPORT: ViewportState = {
  x: 0,
  y: 0,
  width: 1200,
  height: 800,
  zoom: 0.7,
};

export function GraphingPage({ baseUrl }: GraphingPageProps): JSX.Element {
  const client = useMemo(() => new GbApiClient({ baseHttpUrl: baseUrl }), [baseUrl]);
  const [activeTab, setActiveTab] = useState<GraphTab>('relationship');
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [viewport, setViewport] = useState<ViewportState>(DEFAULT_VIEWPORT);
  const [graphDataLabel, setGraphDataLabel] = useState<'summary/downsampled' | 'detailed window'>('summary/downsampled');
  const [plotDataLabel, setPlotDataLabel] = useState<'summary/downsampled' | 'detailed window'>('summary/downsampled');
  const [timeseries, setTimeseries] = useState<Array<{ seriesKey: string; points: Array<{ timestamp: string; value: number }> }>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const loadCoarse = async (): Promise<void> => {
      setLoading(true);
      setError(null);
      try {
        const [topology, layout, tiles] = await Promise.all([
          client.getGraphTopology(),
          client.getGraphLayoutProducts({
            zoom: DEFAULT_VIEWPORT.zoom,
            viewportX: DEFAULT_VIEWPORT.x,
            viewportY: DEFAULT_VIEWPORT.y,
            viewportWidth: DEFAULT_VIEWPORT.width,
            viewportHeight: DEFAULT_VIEWPORT.height,
          }),
          client.getGraphTimeSeriesTiles({ zoom: DEFAULT_VIEWPORT.zoom }),
        ]);
        if (cancelled) return;

        const positions = new Map(layout.nodes.map((node) => [node.nodeId, { x: node.x, y: node.y }]));
        setNodes(
          topology.nodes
            .filter((node) => positions.has(node.id))
            .map((node) => ({ ...node, metadata: { ...node.metadata, position: positions.get(node.id) } }))
        );
        setEdges(topology.edges);
        setGraphDataLabel(layout.dataLabel);
        setPlotDataLabel(tiles.dataLabel);
        setTimeseries(tiles.tiles);
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : 'Failed to load graphing data.');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    void loadCoarse();
    return () => {
      cancelled = true;
    };
  }, [client]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void (async () => {
        try {
          const [layout, tiles] = await Promise.all([
            client.getGraphLayoutProducts({
              zoom: viewport.zoom,
              viewportX: viewport.x,
              viewportY: viewport.y,
              viewportWidth: viewport.width,
              viewportHeight: viewport.height,
            }),
            client.getGraphTimeSeriesTiles({ zoom: viewport.zoom }),
          ]);

          const positions = new Map(layout.nodes.map((node) => [node.nodeId, { x: node.x, y: node.y }]));
          setNodes((previous) =>
            previous
              .filter((node) => positions.has(node.id))
              .map((node) => ({ ...node, metadata: { ...node.metadata, position: positions.get(node.id) } }))
          );
          setGraphDataLabel(layout.dataLabel);
          setPlotDataLabel(tiles.dataLabel);
          setTimeseries(tiles.tiles);
        } catch {
          // Keep prior coarse data on incremental fetch errors.
        }
      })();
    }, 280);

    return () => window.clearTimeout(timer);
  }, [client, viewport]);

  const cytoscapeElements = useMemo(
    () => [
      ...nodes.map((node) => {
        const position = node.metadata.position as { x: number; y: number } | undefined;
        return {
          data: { id: node.id, label: node.label, nodeType: node.type },
          position: position ?? { x: 0, y: 0 },
        };
      }),
      ...edges
        .filter((edge) => nodes.some((node) => node.id === edge.source) && nodes.some((node) => node.id === edge.target))
        .map((edge) => ({ data: { id: edge.id, source: edge.source, target: edge.target, label: edge.label ?? '' } })),
    ],
    [edges, nodes]
  );

  return (
    <section>
      <header>
        <h2>Graphing</h2>
        <p className="muted">Server-driven graph layout + tiled heavy plots with progressive refinement.</p>
      </header>

      <div className="card" style={{ marginBottom: 12 }}>
        <div style={{ display: 'flex', gap: 8 }}>
          <button type="button" onClick={() => setActiveTab('relationship')} disabled={activeTab === 'relationship'}>Relationship graph</button>
          <button type="button" onClick={() => setActiveTab('plots')} disabled={activeTab === 'plots'}>Heavy plots</button>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 12 }}>
        <h3>Viewport / zoom</h3>
        <label>
          Zoom: {viewport.zoom.toFixed(2)}
          <input
            type="range"
            min={0.2}
            max={3.5}
            step={0.05}
            value={viewport.zoom}
            onChange={(event) => setViewport((previous) => ({ ...previous, zoom: Number(event.target.value) }))}
          />
        </label>
        <p className="muted">Coarse data is requested first; detailed window data replaces it as zoom increases.</p>
      </div>

      {loading ? <p>Loading graphing data…</p> : null}
      {error ? <p className="error">{error}</p> : null}

      {activeTab === 'relationship' ? (
        <div className="card">
          <p><strong>Data detail:</strong> {graphDataLabel}</p>
          <CytoscapeComponent
            elements={cytoscapeElements}
            style={{ width: '100%', height: '520px' }}
            layout={{ name: 'preset', fit: true, padding: 30 }}
            stylesheet={[
              {
                selector: 'node',
                style: {
                  label: 'data(label)',
                  'font-size': 10,
                  'text-wrap': 'wrap',
                  'background-color': '#1f6feb',
                  color: '#fff',
                },
              },
              {
                selector: 'edge',
                style: {
                  width: 1,
                  'line-color': '#8b949e',
                  'target-arrow-color': '#8b949e',
                  'target-arrow-shape': 'triangle',
                  'curve-style': 'bezier',
                },
              },
            ]}
            wheelSensitivity={0.2}
          />
        </div>
      ) : (
        <div className="card">
          <p><strong>Data detail:</strong> {plotDataLabel}</p>
          <Plot
            data={timeseries.map((tile) => ({
              x: tile.points.map((point) => point.timestamp),
              y: tile.points.map((point) => point.value),
              type: 'scattergl',
              mode: 'lines',
              name: tile.seriesKey,
            }))}
            layout={{
              autosize: true,
              title: { text: 'Graph telemetry tiles (server-downsampled by zoom/window)' },
              paper_bgcolor: '#0d1117',
              plot_bgcolor: '#0d1117',
              font: { color: '#c9d1d9' },
              xaxis: { title: { text: 'Time' } },
              yaxis: { title: { text: 'Value' } },
            }}
            config={{ responsive: true, displaylogo: false }}
            style={{ width: '100%', height: '520px' }}
            useResizeHandler
          />
        </div>
      )}
    </section>
  );
}
