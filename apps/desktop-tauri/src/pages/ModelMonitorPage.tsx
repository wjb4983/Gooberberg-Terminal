import { parseAlertPayload, parseLogPayload, parseModelDeploymentPayload } from '@gb/api-client';
import type { AlertEvent, AlertSeverity, LogEvent, ModelDeploymentEventPayload } from '@gb/schemas';
import { useEffect, useMemo, useRef, useState } from 'react';

import { createDesktopApiClient } from '../api/client';
import { ApiErrorCallout } from '../components/ApiErrorCallout';
import { DataTable } from '../components/DataTable';
import { HealthWidget } from '../components/HealthWidget';
import { useOperatorConsole } from '../context/OperatorConsoleContext';

interface ModelMonitorPageProps {
  baseUrl: string;
  defaultSeverity: 'all' | AlertSeverity;
}

export function ModelMonitorPage({ baseUrl, defaultSeverity }: ModelMonitorPageProps): JSX.Element {
  const client = useMemo(() => createDesktopApiClient({ baseHttpUrl: baseUrl }), [baseUrl]);
  const [alerts, setAlerts] = useState<AlertEvent[]>([]);
  const [logs, setLogs] = useState<LogEvent[]>([]);
  const [deploymentEvents, setDeploymentEvents] = useState<ModelDeploymentEventPayload[]>([]);
  const [severityFilter, setSeverityFilter] = useState<'all' | AlertSeverity>(defaultSeverity);
  const [serviceFilter, setServiceFilter] = useState('all');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [connectionState, setConnectionState] = useState('connecting');
  const [error, setError] = useState<string | null>(null);
  const lastSeqRef = useRef<number | undefined>(undefined);
  const { reportApiStatus, reportWebSocketStatus, pushToast } = useOperatorConsole();

  useEffect(() => {
    reportWebSocketStatus(connectionState);
  }, [connectionState, reportWebSocketStatus]);

  useEffect(() => {
    void client
      .getAlerts()
      .then((payload) => {
        setAlerts(payload);
        setError(null);
        reportApiStatus('connected');
      })
      .catch((loadError) => {
        setError(loadError instanceof Error ? loadError.message : 'Failed to load alerts.');
        reportApiStatus('offline');
      });
  }, [client, reportApiStatus]);

  useEffect(() => {
    const connection = client.connectTopicWebSocket({
      topics: ['alerts', 'logs', 'models'],
      getResumeSeq: () => lastSeqRef.current,
      onStatus: setConnectionState,
      onEvent: (event) => {
        lastSeqRef.current = event.seq;

        if (event.topic === 'alerts') {
          const alert = parseAlertPayload(event.payload);
          if (!alert) return;
          if (alert.level === 'warning' || alert.level === 'critical') {
            pushToast({ message: `${alert.level.toUpperCase()}: ${alert.service} — ${alert.message}`, tone: alert.level });
          }
          setAlerts((previous) => [alert, ...previous.filter((existing) => existing.id !== alert.id)].slice(0, 200));
        }

        if (event.topic === 'logs') {
          const log = parseLogPayload(event.payload);
          if (!log) return;
          setLogs((previous) => [log, ...previous].slice(0, 200));
        }

        if (event.topic === 'models') {
          const deploymentEvent = parseModelDeploymentPayload(event.payload);
          if (!deploymentEvent) return;
          setDeploymentEvents((previous) => [deploymentEvent, ...previous].slice(0, 30));
        }
      },
    });

    return () => connection.close();
  }, [client, pushToast]);

  const services = useMemo(() => ['all', ...new Set(alerts.map((alert) => alert.service))], [alerts]);
  const categories = useMemo(() => ['all', ...new Set(alerts.map((alert) => alert.category))], [alerts]);

  const filteredAlerts = alerts.filter((alert) => {
    if (severityFilter !== 'all' && alert.level !== severityFilter) return false;
    if (serviceFilter !== 'all' && alert.service !== serviceFilter) return false;
    if (categoryFilter !== 'all' && alert.category !== categoryFilter) return false;
    return true;
  });

  return (
    <section>
      <h2>Model Monitor</h2>
      <p>Live deployment, alert, and log visibility for model operations.</p>
      <p className="muted">Connection: {connectionState}</p>

      <HealthWidget baseUrl={baseUrl} />

      {error ? <ApiErrorCallout message={error} /> : null}

      <div className="card" style={{ marginTop: '1rem' }}>
        <h3>Deployment status stream</h3>
        <ul>
          {deploymentEvents.length === 0 ? <li>No deployment events received yet.</li> : null}
          {deploymentEvents.map((event) => (
            <li key={`${event.deployment_id}-${event.updated_at}`}>
              {new Date(event.updated_at).toLocaleTimeString()} · {event.model_name}:{event.model_version} · {event.status}
            </li>
          ))}
        </ul>
      </div>

      <div className="graph-filter-grid" style={{ marginTop: '1rem' }}>
        <label>
          Severity
          <select value={severityFilter} onChange={(event) => setSeverityFilter(event.target.value as 'all' | AlertSeverity)}>
            <option value="all">All</option>
            <option value="info">Info</option>
            <option value="warning">Warning</option>
            <option value="critical">Critical</option>
          </select>
        </label>
        <label>
          Service
          <select value={serviceFilter} onChange={(event) => setServiceFilter(event.target.value)}>
            {services.map((service) => (
              <option key={service} value={service}>{service}</option>
            ))}
          </select>
        </label>
        <label>
          Category
          <select value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value)}>
            {categories.map((category) => (
              <option key={category} value={category}>{category}</option>
            ))}
          </select>
        </label>
      </div>

      <DataTable
        title="Alerts"
        rows={filteredAlerts}
        emptyLabel="No alerts"
        searchPlaceholder="Search service/category/message"
        searchValue={(alert) => `${alert.service} ${alert.category} ${alert.message}`}
        columns={[
          { key: 'service', header: 'Service', render: (alert) => alert.service },
          { key: 'severity', header: 'Severity', render: (alert) => alert.level },
          { key: 'category', header: 'Category', render: (alert) => alert.category },
          { key: 'message', header: 'Message', render: (alert) => alert.message },
          { key: 'status', header: 'Status', render: (alert) => alert.status },
        ]}
      />

      <DataTable
        title="Logs"
        rows={logs}
        emptyLabel="Waiting for logs…"
        searchPlaceholder="Search logs"
        searchValue={(log) => `${log.service} ${log.level} ${log.message}`}
        columns={[
          { key: 'time', header: 'Timestamp', render: (log) => new Date(log.timestamp).toLocaleTimeString() },
          { key: 'service', header: 'Service', render: (log) => log.service },
          { key: 'level', header: 'Level', render: (log) => log.level },
          { key: 'message', header: 'Message', render: (log) => log.message },
        ]}
      />

      <details className="card" style={{ marginTop: '1rem' }}>
        <summary>Advanced diagnostics (deferred)</summary>
        <p className="muted">Use dedicated graphing workflows for deeper trend analysis to keep this page lightweight.</p>
        <p><a href="/graphing">Open Graphing workspace</a></p>
      </details>
    </section>
  );
}
