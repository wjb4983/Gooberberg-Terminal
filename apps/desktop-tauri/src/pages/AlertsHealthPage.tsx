import { parseAlertPayload, parseLogPayload } from '@gb/api-client';
import type { AlertEvent, AlertSeverity, LogEvent } from '@gb/schemas';
import { useEffect, useMemo, useRef, useState } from 'react';
import { createDesktopApiClient } from '../api/client';
import { DataTable } from '../components/DataTable';
import { ApiErrorCallout } from '../components/ApiErrorCallout';
import { useOperatorConsole } from '../context/OperatorConsoleContext';

interface AlertsHealthPageProps {
  baseUrl: string;
  defaultSeverity: 'all' | AlertSeverity;
}

export function AlertsHealthPage({ baseUrl, defaultSeverity }: AlertsHealthPageProps): JSX.Element {
  const client = useMemo(() => createDesktopApiClient({ baseHttpUrl: baseUrl }), [baseUrl]);
  const [alerts, setAlerts] = useState<AlertEvent[]>([]);
  const [logs, setLogs] = useState<LogEvent[]>([]);
  const [severityFilter, setSeverityFilter] = useState<'all' | AlertSeverity>(defaultSeverity);
  const [serviceFilter, setServiceFilter] = useState('all');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [connectionState, setConnectionState] = useState('connecting');
  const [error, setError] = useState<string | null>(null);
  const lastSeqRef = useRef<number | undefined>(undefined);
  const { reportWebSocketStatus, reportApiStatus, pushToast } = useOperatorConsole();

  useEffect(() => {
    reportWebSocketStatus(connectionState);
  }, [connectionState, reportWebSocketStatus]);

  useEffect(() => {
    void client
      .getAlerts()
      .then((payload) => {
        setAlerts(payload);
        reportApiStatus('connected');
        setError(null);
      })
      .catch((loadError) => {
        setError(loadError instanceof Error ? loadError.message : 'Failed to load alerts.');
        reportApiStatus('offline');
      });
  }, [client, reportApiStatus]);

  useEffect(() => {
    const connection = client.connectTopicWebSocket({
      topics: ['alerts', 'logs'],
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

  const acknowledgeAlert = async (alert: AlertEvent): Promise<void> => {
    const updated = await client.acknowledgeAlert(alert.id);
    setAlerts((previous) => [updated, ...previous.filter((existing) => existing.id !== updated.id)]);
  };

  return (
    <section>
      <h2>Alerts &amp; Health</h2>

      <div className="graph-filter-grid">
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

      {error ? <ApiErrorCallout message={error} /> : null}

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
          {
            key: 'action',
            header: 'Action',
            render: (alert) => (alert.status === 'active' ? <button onClick={() => void acknowledgeAlert(alert)}>Ack</button> : '—'),
          },
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
    </section>
  );
}
