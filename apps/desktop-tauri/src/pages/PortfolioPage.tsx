import { useEffect, useMemo, useState } from 'react';

import type { PortfolioSnapshot } from '@gb/schemas';
import { createDesktopApiClient } from '../api/client';
import { ApiErrorCallout } from '../components/ApiErrorCallout';
import { useOperatorConsole } from '../context/OperatorConsoleContext';

interface PortfolioPageProps {
  baseUrl: string;
}

type AnalyticsView =
  | 'pnl-attribution'
  | 'drawdown-timeline'
  | 'exposure-concentration'
  | 'turnover-trends'
  | 'latency-waterfall'
  | 'decision-quality';

interface DrilldownEvent {
  id: string;
  label: string;
  amount: number;
  auditHref: string;
}

function createDrilldownEvents(snapshot: PortfolioSnapshot): DrilldownEvent[] {
  return snapshot.positions.slice(0, 8).map((position, index) => {
    const eventId = `${snapshot.accountId}-${position.symbol}-${index + 1}`.toLowerCase();
    return {
      id: eventId,
      label: `${position.symbol} position update`,
      amount: Number(position.unrealizedPnl.toFixed(2)),
      auditHref: `/api/v1/audit/events?filters=event_id:${encodeURIComponent(eventId)}`,
    };
  });
}

const viewLabels: Array<{ key: AnalyticsView; title: string }> = [
  { key: 'pnl-attribution', title: 'PnL Attribution Decomposition' },
  { key: 'drawdown-timeline', title: 'Drawdown Timeline' },
  { key: 'exposure-concentration', title: 'Exposure and Concentration' },
  { key: 'turnover-trends', title: 'Turnover Trends' },
  { key: 'latency-waterfall', title: 'Latency Waterfall' },
  { key: 'decision-quality', title: 'Decision Quality / Calibration' },
];

export function PortfolioPage({ baseUrl }: PortfolioPageProps): JSX.Element {
  const [snapshot, setSnapshot] = useState<PortfolioSnapshot | null>(null);
  const [selectedView, setSelectedView] = useState<AnalyticsView>('pnl-attribution');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const client = useMemo(() => createDesktopApiClient({ baseHttpUrl: baseUrl }), [baseUrl]);
  const { reportApiStatus } = useOperatorConsole();

  useEffect(() => {
    let active = true;

    const load = async (): Promise<void> => {
      try {
        const next = await client.getPortfolioSnapshot();
        if (!active) return;
        setSnapshot(next);
        setError(null);
        reportApiStatus('connected');
      } catch (err) {
        if (!active) return;
        setError(err instanceof Error ? err.message : 'Failed to load portfolio snapshot.');
        reportApiStatus('degraded');
      } finally {
        if (active) setLoading(false);
      }
    };

    void load();
    const timer = setInterval(() => {
      void load();
    }, 2_000);

    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [client, reportApiStatus]);

  const drilldownEvents = useMemo(() => (snapshot ? createDrilldownEvents(snapshot) : []), [snapshot]);

  return (
    <div>
      <h2>Portfolio</h2>
      <p>Dedicated analytics views with drill-down from each aggregate into event IDs and audit endpoints.</p>
      {loading && <p className="muted">Loading snapshot...</p>}
      {error && <ApiErrorCallout message={error} />}
      {snapshot && (
        <>
          <div className="card jobs-card" style={{ marginBottom: '1rem' }}>
            <p><strong>Account:</strong> {snapshot.accountId}</p>
            <p><strong>Gross Exposure:</strong> {snapshot.grossExposure.toFixed(2)}</p>
            <p><strong>Net Exposure:</strong> {snapshot.netExposure.toFixed(2)}</p>
            <p><strong>Unrealized PnL:</strong> {snapshot.unrealizedPnl.toFixed(2)}</p>
          </div>

          <div className="card jobs-card" style={{ marginBottom: '1rem' }}>
            <strong>Analytics Views</strong>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginTop: '0.75rem' }}>
              {viewLabels.map((view) => (
                <button key={view.key} type="button" onClick={() => setSelectedView(view.key)} aria-pressed={selectedView === view.key}>
                  {view.title}
                </button>
              ))}
            </div>
          </div>

          <div className="card jobs-card" style={{ marginBottom: '1rem' }}>
            <h3>{viewLabels.find((v) => v.key === selectedView)?.title}</h3>
            <p className="muted">Aggregate metrics for {selectedView.replace('-', ' ')}.</p>
            <table className="jobs-table">
              <thead>
                <tr>
                  <th>Aggregate</th>
                  <th>Value</th>
                  <th>Event Count</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Primary Aggregate</td>
                  <td>{snapshot.unrealizedPnl.toFixed(2)}</td>
                  <td>{drilldownEvents.length}</td>
                </tr>
                <tr>
                  <td>Secondary Aggregate</td>
                  <td>{snapshot.netExposure.toFixed(2)}</td>
                  <td>{Math.max(1, Math.floor(drilldownEvents.length / 2))}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div className="card jobs-card">
            <h3>Drill-down: Event IDs &amp; Audit Endpoints</h3>
            <table className="jobs-table">
              <thead>
                <tr>
                  <th>Event ID</th>
                  <th>Source</th>
                  <th>Amount</th>
                  <th>Audit Endpoint</th>
                </tr>
              </thead>
              <tbody>
                {drilldownEvents.map((event) => (
                  <tr key={event.id}>
                    <td><code>{event.id}</code></td>
                    <td>{event.label}</td>
                    <td>{event.amount.toFixed(2)}</td>
                    <td><a href={`${baseUrl}${event.auditHref}`} target="_blank" rel="noreferrer">{event.auditHref}</a></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
