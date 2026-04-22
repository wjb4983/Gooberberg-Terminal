import { GbApiClient } from '@gb/api-client';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { JobLifecyclePanel } from '../components/JobLifecyclePanel';

interface BacktestsPageProps { baseUrl: string; }
interface BacktestRunItem {
  id: string;
  strategy_key: string;
  model_config_id: string | null;
  window_start: string;
  window_end: string;
  parameters: Record<string, unknown>;
  job_id: string;
  status: string;
  created_at: string;
}
interface ModelConfigItem { id: string; config: Record<string, unknown>; }
interface RunEvent { timestamp: string; status: string; detail: string; }

async function requestJson<T>(baseUrl: string, path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, { ...init, headers: { Accept: 'application/json', ...(init?.body ? { 'Content-Type': 'application/json' } : {}), ...(init?.headers ?? {}) } });
  if (!response.ok) throw new Error(`Request failed (${response.status}) for ${path}`);
  return (await response.json()) as T;
}

export function BacktestsPage({ baseUrl }: BacktestsPageProps): JSX.Element {
  const client = useMemo(() => new GbApiClient({ baseHttpUrl: baseUrl }), [baseUrl]);
  const [searchParams, setSearchParams] = useSearchParams();
  const [runs, setRuns] = useState<BacktestRunItem[]>([]);
  const [configs, setConfigs] = useState<ModelConfigItem[]>([]);
  const [strategyKey, setStrategyKey] = useState('mean_reversion');
  const [selectedConfigId, setSelectedConfigId] = useState('');
  const [windowStart, setWindowStart] = useState('2024-01-01T00:00:00Z');
  const [windowEnd, setWindowEnd] = useState('2024-12-31T00:00:00Z');
  const [paramsJson, setParamsJson] = useState('{"slippage_bps": 2}');
  const [eventsByJob, setEventsByJob] = useState<Record<string, RunEvent[]>>({});
  const [summary, setSummary] = useState('No run selected.');
  const [error, setError] = useState<string | null>(null);
  const lastSeqRef = useRef<number | undefined>(undefined);

  const selectedJobId = searchParams.get('job_id');
  const selectedRun = useMemo(() => runs.find((item) => item.job_id === selectedJobId) ?? null, [runs, selectedJobId]);

  const setSelectedJobId = (jobId: string): void => {
    setSearchParams((previous) => {
      const next = new URLSearchParams(previous);
      next.set('job_id', jobId);
      return next;
    });
  };

  const load = useCallback(async (): Promise<void> => {
    try {
      const [runPayload, configPayload] = await Promise.all([
        requestJson<BacktestRunItem[]>(baseUrl, '/api/v1/backtest-runs'),
        requestJson<ModelConfigItem[]>(baseUrl, '/api/v1/model-configs'),
      ]);
      setRuns(runPayload);
      setConfigs(configPayload);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Failed loading backtests.');
    }
  }, [baseUrl]);

  useEffect(() => { void load(); }, [load]);

  useEffect(() => {
    const connection = client.connectTopicWebSocket({
      topics: ['jobs'],
      getResumeSeq: () => lastSeqRef.current,
      onEvent: (event) => {
        if (event.topic !== 'jobs') return;
        lastSeqRef.current = event.seq;
        const payload = event.payload as Record<string, unknown>;
        const jobId = typeof payload.job_id === 'string' ? payload.job_id : '';
        if (!jobId) return;
        const next: RunEvent = {
          timestamp: typeof payload.updated_at === 'string' ? payload.updated_at : event.timestamp,
          status: typeof payload.status === 'string' ? payload.status : 'unknown',
          detail: typeof payload.detail === 'string' ? payload.detail : JSON.stringify(payload),
        };
        setEventsByJob((prev) => ({ ...prev, [jobId]: [next, ...(prev[jobId] ?? [])].slice(0, 40) }));
        if (selectedRun?.job_id === jobId) setSummary(`${next.status}: ${next.detail}`);
      },
    });
    return () => connection.close();
  }, [client, selectedRun]);

  const launch = async (): Promise<void> => {
    setError(null);
    let parsedParameters: Record<string, unknown>;
    try { parsedParameters = JSON.parse(paramsJson) as Record<string, unknown>; } catch { setError('Parameters must be valid JSON.'); return; }

    try {
      const created = await requestJson<BacktestRunItem>(baseUrl, '/api/v1/backtest-runs', {
        method: 'POST',
        body: JSON.stringify({
          strategy_key: strategyKey,
          model_config_id: selectedConfigId || null,
          window_start: windowStart,
          window_end: windowEnd,
          parameters: parsedParameters,
        }),
      });
      setRuns((prev) => [created, ...prev]);
      setSelectedJobId(created.job_id);
      setSummary('queued: backtest run accepted by api-control-plane');
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : 'Failed launching backtest.');
    }
  };

  useEffect(() => {
    if (!selectedRun) return;
    void requestJson<{ status: string; detail: string }>(baseUrl, `/api/v1/jobs/${encodeURIComponent(selectedRun.job_id)}`)
      .then((payload) => setSummary(`${payload.status}: ${payload.detail}`))
      .catch(() => setSummary('Unable to load persisted summary.'));
  }, [baseUrl, selectedRun]);

  return (
    <section>
      <h2>Backtests</h2>
      <p>Queue historical backtests as async jobs; this UI only handles submissions and incremental status rendering.</p>
      {error ? <p className="muted">Error: {error}</p> : null}
      <div className="card" style={{ marginBottom: '1rem' }}>
        <h3>Launch backtest</h3>
        <div style={{ display: 'grid', gap: '0.5rem' }}>
          <input value={strategyKey} onChange={(event) => setStrategyKey(event.target.value)} placeholder="Strategy key" />
          <select value={selectedConfigId} onChange={(event) => setSelectedConfigId(event.target.value)}>
            <option value="">No model config</option>
            {configs.map((config) => <option key={config.id} value={config.id}>{typeof config.config.name === 'string' ? config.config.name : config.id}</option>)}
          </select>
          <input value={windowStart} onChange={(event) => setWindowStart(event.target.value)} placeholder="Window start (ISO)" />
          <input value={windowEnd} onChange={(event) => setWindowEnd(event.target.value)} placeholder="Window end (ISO)" />
          <textarea value={paramsJson} onChange={(event) => setParamsJson(event.target.value)} rows={3} />
          <button type="button" onClick={() => void launch()}>Launch backtest</button>
        </div>
      </div>

      <div className="card jobs-card">
        <table className="jobs-table">
          <thead><tr><th>ID</th><th>Job ID</th><th>Strategy</th><th>Model Config</th><th>Status</th><th>Window</th></tr></thead>
          <tbody>
            {runs.length === 0 ? <tr><td colSpan={6}>No backtests yet.</td></tr> : null}
            {runs.map((run) => (
              <tr key={run.id} onClick={() => setSelectedJobId(run.job_id)} style={{ cursor: 'pointer', background: selectedJobId === run.job_id ? 'rgba(127,127,127,0.12)' : undefined }}>
                <td>{run.id.slice(0, 8)}</td><td>{run.job_id.slice(0, 8)}</td><td>{run.strategy_key}</td><td>{run.model_config_id ? run.model_config_id.slice(0, 8) : '-'}</td><td>{run.status}</td><td>{new Date(run.window_start).toLocaleDateString()} → {new Date(run.window_end).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <JobLifecyclePanel
        submitContent={<p>Submit a backtest and revisit it through URL restoration with <code>?job_id=...</code>.</p>}
        runningContent={!selectedRun ? <p className="muted">Select a run to inspect details.</p> : (
          <>
            <p><strong>Persisted summary:</strong> {summary}</p>
            <ul>
              {(eventsByJob[selectedRun.job_id] ?? []).map((event, index) => (
                <li key={`${event.timestamp}-${index}`}>{new Date(event.timestamp).toLocaleTimeString()} · {event.status} · {event.detail}</li>
              ))}
              {(eventsByJob[selectedRun.job_id] ?? []).length === 0 ? <li>No live events yet.</li> : null}
            </ul>
          </>
        )}
        artifactContent={!selectedRun ? <p className="muted">Select a run to open job detail.</p> : <p><Link to={`/jobs/${encodeURIComponent(selectedRun.job_id)}`}>Open run detail view for job {selectedRun.job_id}</Link></p>}
      />
    </section>
  );
}
