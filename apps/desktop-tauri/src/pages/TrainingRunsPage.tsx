import { GbApiClient } from '@gb/api-client';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

interface TrainingRunsPageProps {
  baseUrl: string;
}

interface TrainingRunItem {
  id: string;
  model_config_id: string;
  dataset_id: string;
  job_id: string;
  status: string;
  parameters: Record<string, unknown>;
  created_at: string;
}

interface ModelConfigItem {
  id: string;
  model_family: string;
  config: Record<string, unknown>;
}

interface RunEvent {
  timestamp: string;
  status: string;
  detail: string;
}

async function requestJson<T>(baseUrl: string, path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, {
    ...init,
    headers: {
      Accept: 'application/json',
      ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) throw new Error(`Request failed (${response.status}) for ${path}`);
  return (await response.json()) as T;
}

export function TrainingRunsPage({ baseUrl }: TrainingRunsPageProps): JSX.Element {
  const client = useMemo(() => new GbApiClient({ baseHttpUrl: baseUrl }), [baseUrl]);
  const [runs, setRuns] = useState<TrainingRunItem[]>([]);
  const [configs, setConfigs] = useState<ModelConfigItem[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [datasetId, setDatasetId] = useState('equities_daily_v1');
  const [parametersJson, setParametersJson] = useState('{"epochs": 20, "seed": 42}');
  const [selectedConfigId, setSelectedConfigId] = useState('');
  const [jobDetail, setJobDetail] = useState<string>('No live status yet.');
  const [eventsByJob, setEventsByJob] = useState<Record<string, RunEvent[]>>({});
  const [error, setError] = useState<string | null>(null);
  const lastSeqRef = useRef<number | undefined>(undefined);

  const selectedRun = useMemo(() => runs.find((run) => run.id === selectedRunId) ?? null, [runs, selectedRunId]);

  const load = useCallback(async (): Promise<void> => {
    setError(null);
    try {
      const [runPayload, configPayload] = await Promise.all([
        requestJson<TrainingRunItem[]>(baseUrl, '/api/v1/training-runs'),
        requestJson<ModelConfigItem[]>(baseUrl, '/api/v1/model-configs'),
      ]);
      setRuns(runPayload);
      setConfigs(configPayload);
      if (!selectedConfigId && configPayload.length > 0) {
        setSelectedConfigId(configPayload[0].id);
      }
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Failed loading training runs.');
    }
  }, [baseUrl, selectedConfigId]);

  useEffect(() => {
    void load();
  }, [load]);

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
        setEventsByJob((previous) => ({
          ...previous,
          [jobId]: [nextEvent, ...(previous[jobId] ?? [])].slice(0, 50),
        }));
        if (selectedRun && selectedRun.job_id === jobId) {
          setJobDetail(`${nextEvent.status}: ${nextEvent.detail}`);
        }
      },
    });
    return () => connection.close();
  }, [client, selectedRun]);

  const launchRun = async (): Promise<void> => {
    setError(null);
    let parsedParameters: Record<string, unknown>;
    try {
      parsedParameters = JSON.parse(parametersJson) as Record<string, unknown>;
    } catch {
      setError('Parameters must be valid JSON.');
      return;
    }
    if (!selectedConfigId) {
      setError('Model config is required.');
      return;
    }

    try {
      const created = await requestJson<TrainingRunItem>(baseUrl, '/api/v1/training-runs', {
        method: 'POST',
        body: JSON.stringify({
          model_config_id: selectedConfigId,
          dataset_id: datasetId,
          parameters: parsedParameters,
        }),
      });
      setRuns((previous) => [created, ...previous]);
      setSelectedRunId(created.id);
      setJobDetail('queued: training run accepted by api-control-plane');
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : 'Failed launching training run.');
    }
  };

  useEffect(() => {
    const run = selectedRun;
    if (!run) return;
    void requestJson<{ id: string; status: string; detail: string }>(baseUrl, `/api/v1/jobs/${encodeURIComponent(run.job_id)}`)
      .then((payload) => setJobDetail(`${payload.status}: ${payload.detail}`))
      .catch(() => setJobDetail('Unable to load persisted job summary.'));
  }, [baseUrl, selectedRun]);

  return (
    <section>
      <h2>Training Runs</h2>
      <p>Submit async training jobs; compute stays server-side while UI streams incremental updates only.</p>
      {error ? <p className="muted">Error: {error}</p> : null}
      <div className="card" style={{ marginBottom: '1rem' }}>
        <h3>Launch training run</h3>
        <div style={{ display: 'grid', gap: '0.5rem' }}>
          <select value={selectedConfigId} onChange={(event) => setSelectedConfigId(event.target.value)}>
            <option value="">Select model config</option>
            {configs.map((config) => (
              <option key={config.id} value={config.id}>{typeof config.config.name === 'string' ? config.config.name : config.id}</option>
            ))}
          </select>
          <input value={datasetId} onChange={(event) => setDatasetId(event.target.value)} placeholder="Dataset ID" />
          <textarea value={parametersJson} onChange={(event) => setParametersJson(event.target.value)} rows={4} />
          <button type="button" onClick={() => void launchRun()}>Launch training run</button>
        </div>
      </div>

      <div className="card jobs-card">
        <table className="jobs-table">
          <thead><tr><th>ID</th><th>Model Config</th><th>Dataset</th><th>Status</th><th>Created</th></tr></thead>
          <tbody>
            {runs.length === 0 ? <tr><td colSpan={5}>No training runs yet.</td></tr> : null}
            {runs.map((run) => (
              <tr key={run.id} onClick={() => setSelectedRunId(run.id)} style={{ cursor: 'pointer', background: selectedRunId === run.id ? 'rgba(127,127,127,0.12)' : undefined }}>
                <td>{run.id.slice(0, 8)}</td><td>{run.model_config_id.slice(0, 8)}</td><td>{run.dataset_id}</td><td>{run.status}</td><td>{new Date(run.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card" style={{ marginTop: '1rem' }}>
        <h3>Run detail</h3>
        {!selectedRun ? <p className="muted">Select a run to inspect persisted summary + live logs.</p> : (
          <>
            <p><strong>Run ID:</strong> {selectedRun.id}</p>
            <p><strong>Job:</strong> {selectedRun.job_id}</p>
            <p><strong>Persisted summary:</strong> {jobDetail}</p>
            <ul>
              {(eventsByJob[selectedRun.job_id] ?? []).map((event, index) => (
                <li key={`${event.timestamp}-${index}`}>{new Date(event.timestamp).toLocaleTimeString()} · {event.status} · {event.detail}</li>
              ))}
              {(eventsByJob[selectedRun.job_id] ?? []).length === 0 ? <li>No live log events yet.</li> : null}
            </ul>
          </>
        )}
      </div>
    </section>
  );
}
