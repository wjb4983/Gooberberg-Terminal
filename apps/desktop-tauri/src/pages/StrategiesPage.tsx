import type { StrategyInstance, StrategyMode, WebSocketEventEnvelope } from '@gb/schemas';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createDesktopApiClient } from '../api/client';

interface StrategiesPageProps {
  baseUrl: string;
}

export function StrategiesPage({ baseUrl }: StrategiesPageProps): JSX.Element {
  const client = useMemo(() => createDesktopApiClient({ baseHttpUrl: baseUrl }), [baseUrl]);
  const [instances, setInstances] = useState<StrategyInstance[]>([]);
  const [strategyKey, setStrategyKey] = useState('');
  const [mode, setMode] = useState<StrategyMode>('paper');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [connectionState, setConnectionState] = useState('connecting');
  const [events, setEvents] = useState<WebSocketEventEnvelope[]>([]);
  const lastSeqRef = useRef<number | undefined>(undefined);

  const loadInstances = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = await client.listStrategyInstances();
      setInstances(payload);
    } catch (fetchError) {
      setError(fetchError instanceof Error ? fetchError.message : 'Failed to load strategy instances.');
    } finally {
      setLoading(false);
    }
  }, [client]);

  useEffect(() => {
    void loadInstances();
  }, [loadInstances]);

  useEffect(() => {
    const connection = client.connectTopicWebSocket({
      topics: ['strategy'],
      getResumeSeq: () => lastSeqRef.current,
      onStatus: setConnectionState,
      onEvent: (event) => {
        if (event.topic !== 'strategy') {
          return;
        }

        lastSeqRef.current = event.seq;
        setEvents((previous) => [event, ...previous].slice(0, 25));
      },
    });

    return () => {
      connection.close();
    };
  }, [client]);

  const handleCreate = async (): Promise<void> => {
    const trimmedKey = strategyKey.trim();
    if (!trimmedKey) {
      setError('Strategy key is required.');
      return;
    }

    setError(null);
    try {
      const created = await client.createStrategyInstance({
        strategyKey: trimmedKey,
        mode,
        intent: { params: {} },
      });
      setInstances((previous) => [created, ...previous]);
      setStrategyKey('');
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : 'Failed to create strategy instance.');
    }
  };

  const handleTransition = async (instanceId: string, action: 'start' | 'stop'): Promise<void> => {
    setError(null);
    try {
      const response =
        action === 'start'
          ? await client.startStrategyInstance(instanceId)
          : await client.stopStrategyInstance(instanceId);
      setInstances((previous) =>
        previous.map((instance) => (instance.id === instanceId ? response.instance : instance)),
      );
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : `Failed to ${action} strategy instance.`);
    }
  };

  return (
    <section>
      <h2>Strategies</h2>
      <p>Manage strategy instances with mocked lifecycle transitions.</p>
      <p className="muted">Connection: {connectionState}</p>

      <div className="card" style={{ marginBottom: '1rem' }}>
        <h3>Create strategy instance</h3>
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          <input value={strategyKey} onChange={(event) => setStrategyKey(event.target.value)} placeholder="Strategy key" />
          <select value={mode} onChange={(event) => setMode(event.target.value as StrategyMode)}>
            <option value="paper">paper</option>
            <option value="live">live</option>
          </select>
          <button type="button" onClick={() => void handleCreate()}>
            Create
          </button>
        </div>
      </div>

      {error ? <p className="muted">Error: {error}</p> : null}

      <div className="card jobs-card">
        <table className="jobs-table">
          <thead>
            <tr>
              <th>Strategy</th>
              <th>Mode</th>
              <th>Status</th>
              <th>Updated</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {!loading && instances.length === 0 ? (
              <tr>
                <td colSpan={5}>No strategy instances yet.</td>
              </tr>
            ) : (
              instances.map((instance) => (
                <tr key={instance.id}>
                  <td>{instance.strategyKey}</td>
                  <td>{instance.mode}</td>
                  <td>{instance.status}</td>
                  <td>{new Date(instance.updatedAtIso).toLocaleString()}</td>
                  <td>
                    <button
                      type="button"
                      onClick={() => void handleTransition(instance.id, 'start')}
                      disabled={instance.status === 'running'}
                    >
                      Start
                    </button>{' '}
                    <button
                      type="button"
                      onClick={() => void handleTransition(instance.id, 'stop')}
                      disabled={instance.status !== 'running'}
                    >
                      Stop
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="card" style={{ marginTop: '1rem' }}>
        <h3>Recent strategy events</h3>
        <ul>
          {events.length === 0 ? <li>No strategy events received yet.</li> : null}
          {events.map((event) => (
            <li key={event.event_id}>
              {new Date(event.timestamp).toLocaleTimeString()} · seq {event.seq} · {JSON.stringify(event.payload)}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
