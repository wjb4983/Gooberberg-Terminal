import { HealthWidget } from '../components/HealthWidget';

type Severity = 'healthy' | 'warning' | 'critical';

interface StatusPanelItem {
  label: string;
  detail: string;
  severity: Severity;
  staleAt: string;
}

interface DashboardPageProps {
  baseUrl: string;
}

const severityLabel: Record<Severity, string> = {
  healthy: 'Healthy',
  warning: 'Warning',
  critical: 'Critical'
};

const panelData: Array<{ title: string; items: StatusPanelItem[] }> = [
  {
    title: 'System Health / Liveness',
    items: [
      { label: 'API Control Plane', detail: 'HTTP and websocket checks passing.', severity: 'healthy', staleAt: 'Updated 17s ago' },
      { label: 'Market Data Ingest', detail: '1 transient timeout in last 5 minutes.', severity: 'warning', staleAt: 'Updated 43s ago' },
      { label: 'Execution Engine', detail: 'Heartbeat missed on primary worker.', severity: 'critical', staleAt: 'Updated 2m ago' }
    ]
  },
  {
    title: 'Data Freshness',
    items: [
      { label: 'Price Cache (1m bars)', detail: 'Latest bar aligned with feed latency budget.', severity: 'healthy', staleAt: 'Updated 9s ago' },
      { label: 'Feature Store Snapshot', detail: 'Behind SLA by 3 minutes.', severity: 'warning', staleAt: 'Updated 3m ago' },
      { label: 'Corporate Actions', detail: 'No sync completed in 34 minutes.', severity: 'critical', staleAt: 'Updated 34m ago' }
    ]
  },
  {
    title: 'Open Positions',
    items: [
      { label: 'Net Exposure', detail: '+$1.42M gross, within limits.', severity: 'healthy', staleAt: 'Updated 26s ago' },
      { label: 'Concentration Risk', detail: 'Semiconductor sleeve at 88% soft cap.', severity: 'warning', staleAt: 'Updated 26s ago' },
      { label: 'Leverage Utilization', detail: 'Hard cap exceeded on strategy breakout-07.', severity: 'critical', staleAt: 'Updated 1m ago' }
    ]
  },
  {
    title: 'Top Alerts',
    items: [
      { label: 'Risk Monitor', detail: 'Drawdown guardrail recovered.', severity: 'healthy', staleAt: 'Updated 58s ago' },
      { label: 'Order Gateway', detail: 'Elevated rejects from venue XNAS.', severity: 'warning', staleAt: 'Updated 1m ago' },
      { label: 'Model Drift', detail: 'Prediction error exceeded max tolerance.', severity: 'critical', staleAt: 'Updated 4m ago' }
    ]
  },
  {
    title: 'Recent Decisions / Orders / Fills',
    items: [
      { label: 'Decision #98214', detail: 'Long add approved by risk gate and sent.', severity: 'healthy', staleAt: 'Updated 12s ago' },
      { label: 'Order #A19F-7', detail: 'Partial fill; waiting for 34% remainder.', severity: 'warning', staleAt: 'Updated 35s ago' },
      { label: 'Fill Reconciliation', detail: '1 fill unmatched to internal ledger.', severity: 'critical', staleAt: 'Updated 2m ago' }
    ]
  }
];

export function DashboardPage({ baseUrl }: DashboardPageProps): JSX.Element {
  return (
    <div>
      <h2>Dashboard</h2>
      <p>Overview of system state.</p>
      <HealthWidget baseUrl={baseUrl} />

      <section className="dashboard-panels" aria-label="Operational status panels">
        {panelData.map((panel) => (
          <article className="dashboard-panel" key={panel.title}>
            <h3>{panel.title}</h3>
            <ul className="dashboard-status-list">
              {panel.items.map((item) => (
                <li key={item.label} className="dashboard-status-item">
                  <div className="dashboard-status-title-row">
                    <span className={`status-pill severity-${item.severity}`}>{severityLabel[item.severity]}</span>
                    <strong>{item.label}</strong>
                  </div>
                  <p>{item.detail}</p>
                  <p className="dashboard-staleness">{item.staleAt}</p>
                </li>
              ))}
            </ul>
          </article>
        ))}
      </section>
    </div>
  );
}
