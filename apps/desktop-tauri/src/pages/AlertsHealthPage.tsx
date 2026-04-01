import { GbApiClient, parseAlertPayload, parseLogPayload } from '@gb/api-client';
import type { AlertEvent, AlertSeverity, LogEvent } from '@gb/schemas';
import { useEffect, useMemo, useRef, useState } from 'react';

interface AlertsHealthPageProps {
  baseUrl: string;
}

export function AlertsHealthPage({ baseUrl }: AlertsHealthPageProps): JSX.Element {
  const client = useMemo(() => new GbApiClient({ baseHttpUrl: baseUrl }), [baseUrl]);
  const [alerts, setAlerts] = useState<AlertEvent[]>([]);
  const [logs, setLogs] = useState<LogEvent[]>([]);
  const [severityFilter, setSeverityFilter] = useState<'all' | AlertSeverity>('all');
  const [serviceFilter, setServiceFilter] = useState('all');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [connectionState, setConnectionState] = useState('connecting');
  const lastSeqRef = useRef<number | undefined>(undefined);

  useEffect(() => {
    void client.getAlerts().then(setAlerts);
  }, [client]);

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
          setAlerts((previous) => [alert, ...previous.filter((existing) => existing.id !== alert.id)].slice(0, 100));
        }

        if (event.topic === 'logs') {
          const log = parseLogPayload(event.payload);
          if (!log) return;
          setLogs((previous) => [log, ...previous].slice(0, 200));
        }
      },
    });

    return () => connection.close();
  }, [client]);

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
      <p className="muted">Connection: {connectionState}</p>

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

      <div className="card jobs-card">
        <h3>Alerts</h3>
        <table className="jobs-table">
          <thead><tr><th>Service</th><th>Severity</th><th>Category</th><th>Message</th><th>Status</th><th /></tr></thead>
          <tbody>
            {filteredAlerts.map((alert) => (
              <tr key={alert.id}>
                <td>{alert.service}</td><td>{alert.level}</td><td>{alert.category}</td><td>{alert.message}</td><td>{alert.status}</td>
                <td>{alert.status === 'active' ? <button onClick={() => void acknowledgeAlert(alert)}>Ack</button> : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card jobs-card">
        <h3>Logs</h3>
        <table className="jobs-table">
          <thead><tr><th>Timestamp</th><th>Service</th><th>Level</th><th>Message</th></tr></thead>
          <tbody>
            {logs.length === 0 ? <tr><td colSpan={4}>Waiting for logs…</td></tr> : logs.slice(0, 30).map((log, idx) => (
              <tr key={`${log.timestamp}-${idx}`}><td>{new Date(log.timestamp).toLocaleTimeString()}</td><td>{log.service}</td><td>{log.level}</td><td>{log.message}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
