import { GbApiClient } from '@gb/api-client';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { JobLifecyclePanel } from '../components/JobLifecyclePanel';

interface ParameterSweepsPageProps { baseUrl: string; }
interface ParameterSweepItem {
  id: string;
  model_config_id: string;
  objective: string;
  search_space: Record<string, unknown>;
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

export function ParameterSweepsPage({ baseUrl }: ParameterSweepsPageProps): JSX.Element {
  const client = useMemo(() => new GbApiClient({ baseHttpUrl: baseUrl }), [baseUrl]);
  const [searchParams, setSearchParams] = useSearchParams();
  const [sweeps, setSweeps] = useState<ParameterSweepItem[]>([]);
  const [configs, setConfigs] = useState<ModelConfigItem[]>([]);
  const [selectedConfigId, setSelectedConfigId] = useState('');
  const [objective, setObjective] = useState('maximize_sharpe');
  const [searchSpaceJson, setSearchSpaceJson] = useState('{"learning_rate": [0.001, 0.01], "hidden_size": [16, 32, 64]}');
  const [eventsByJob, setEventsByJob] = useState<Record<string, RunEvent[]>>({});
  const [summary, setSummary] = useState('No run selected.');
  const [error, setError] = useState<string | null>(null);
  const lastSeqRef = useRef<number | undefined>(undefined);

  const selectedJobId = searchParams.get('job_id');
  const selectedSweep = useMemo(() => sweeps.find((item) => item.job_id === selectedJobId) ?? null, [sweeps, selectedJobId]);

  const setSelectedJobId = (jobId: string): void => {
    setSearchParams((previous) => {
      const next = new URLSearchParams(previous);
      next.set('job_id', jobId);
      return next;
    });
  };

  const load = useCallback(async (): Promise<void> => {
    try {
      const [sweepPayload, configPayload] = await Promise.all([
        requestJson<ParameterSweepItem[]>(baseUrl, '/api/v1/parameter-sweeps'),
        requestJson<ModelConfigItem[]>(baseUrl, '/api/v1/model-configs'),
      ]);
      setSweeps(sweepPayload);
      setConfigs(configPayload);
      if (!selectedConfigId && configPayload.length > 0) setSelectedConfigId(configPayload[0].id);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Failed loading parameter sweeps.');
    }
  }, [baseUrl, selectedConfigId]);

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
        const nextEvent: RunEvent = {
          timestamp: typeof payload.updated_at === 'string' ? payload.updated_at : event.timestamp,
          status: typeof payload.status === 'string' ? payload.status : 'unknown',
          detail: typeof payload.detail === 'string' ? payload.detail : JSON.stringify(payload),
        };
        setEventsByJob((previous) => ({ ...previous, [jobId]: [nextEvent, ...(previous[jobId] ?? [])].slice(0, 40) }));
        if (selectedSweep?.job_id === jobId) setSummary(`${nextEvent.status}: ${nextEvent.detail}`);
      },
    });
    return () => connection.close();
  }, [client, selectedSweep]);

  const launchSweep = async (): Promise<void> => {
    setError(null);
    if (!selectedConfigId) { setError('Model config is required.'); return; }
    let parsedSearchSpace: Record<string, unknown>;
    try { parsedSearchSpace = JSON.parse(searchSpaceJson) as Record<string, unknown>; } catch { setError('Search space must be valid JSON.'); return; }

    try {
      const created = await requestJson<ParameterSweepItem>(baseUrl, '/api/v1/parameter-sweeps', {
        method: 'POST',
        body: JSON.stringify({ model_config_id: selectedConfigId, objective, search_space: parsedSearchSpace }),
      });
      setSweeps((previous) => [created, ...previous]);
      setSelectedJobId(created.job_id);
      setSummary('queued: parameter sweep accepted by api-control-plane');
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : 'Failed launching sweep.');
    }
  };

  useEffect(() => {
    if (!selectedSweep) return;
    void requestJson<{ status: string; detail: string }>(baseUrl, `/api/v1/jobs/${encodeURIComponent(selectedSweep.job_id)}`)
      .then((payload) => setSummary(`${payload.status}: ${payload.detail}`))
      .catch(() => setSummary('Unable to load persisted summary.'));
  }, [baseUrl, selectedSweep]);

  return (
    <section>
      <h2>Parameter Sweeps</h2>
      <p>Launch server-side sweep jobs from saved model configs and follow incremental status updates.</p>
      {error ? <p className="muted">Error: {error}</p> : null}
      <div className="card" style={{ marginBottom: '1rem' }}>
        <h3>Launch sweep</h3>
        <div style={{ display: 'grid', gap: '0.5rem' }}>
          <select value={selectedConfigId} onChange={(event) => setSelectedConfigId(event.target.value)}>
            <option value="">Select model config</option>
            {configs.map((config) => <option key={config.id} value={config.id}>{typeof config.config.name === 'string' ? config.config.name : config.id}</option>)}
          </select>
          <input value={objective} onChange={(event) => setObjective(event.target.value)} placeholder="Objective" />
          <textarea value={searchSpaceJson} onChange={(event) => setSearchSpaceJson(event.target.value)} rows={4} />
          <button type="button" onClick={() => void launchSweep()}>Launch parameter sweep</button>
        </div>
      </div>

      <div className="card jobs-card">
        <table className="jobs-table">
          <thead><tr><th>ID</th><th>Job ID</th><th>Objective</th><th>Model Config</th><th>Status</th><th>Created</th></tr></thead>
          <tbody>
            {sweeps.length === 0 ? <tr><td colSpan={6}>No sweeps yet.</td></tr> : null}
            {sweeps.map((sweep) => (
              <tr key={sweep.id} onClick={() => setSelectedJobId(sweep.job_id)} style={{ cursor: 'pointer', background: selectedJobId === sweep.job_id ? 'rgba(127,127,127,0.12)' : undefined }}>
                <td>{sweep.id.slice(0, 8)}</td><td>{sweep.job_id.slice(0, 8)}</td><td>{sweep.objective}</td><td>{sweep.model_config_id.slice(0, 8)}</td><td>{sweep.status}</td><td>{new Date(sweep.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <JobLifecyclePanel
        submitContent={<p>Launch a sweep and persist selection via <code>?job_id=...</code> so deep links reopen the same run.</p>}
        runningContent={!selectedSweep ? <p className="muted">Select a sweep to inspect details.</p> : (
          <>
            <p><strong>Persisted summary:</strong> {summary}</p>
            <ul>
              {(eventsByJob[selectedSweep.job_id] ?? []).map((event, index) => (
                <li key={`${event.timestamp}-${index}`}>{new Date(event.timestamp).toLocaleTimeString()} · {event.status} · {event.detail}</li>
              ))}
              {(eventsByJob[selectedSweep.job_id] ?? []).length === 0 ? <li>No live events yet.</li> : null}
            </ul>
          </>
        )}
        artifactContent={!selectedSweep ? <p className="muted">Select a sweep to open job detail.</p> : <p><Link to={`/jobs/${encodeURIComponent(selectedSweep.job_id)}`}>Open run detail view for job {selectedSweep.job_id}</Link></p>}
      />
    </section>
  );
}
