import { GbApiClient } from '@gb/api-client';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { JobLifecyclePanel } from '../components/JobLifecyclePanel';

interface TestingPageProps {
  baseUrl: string;
}

type TestingMode = 'smoke' | 'acceptance' | 'regression';

interface TestingTargetReference {
  target_type: string;
  target_id: string;
  label?: string;
}

interface TestingArtifactReference {
  artifact_type: string;
  artifact_ref: string;
  label?: string;
}

interface TestingResultSummary {
  passed_checks: string[];
  failed_checks: string[];
  log_artifacts: TestingArtifactReference[];
}

interface TestingRunItem {
  id: string;
  job_id: string;
  mode: TestingMode;
  target_refs: TestingTargetReference[];
  status: string;
  parameters: Record<string, unknown>;
  result_summary: TestingResultSummary | null;
  created_at: string;
}

interface RunEvent {
  timestamp: string;
  status: string;
  detail: string;
}

const MODE_PRESETS: Record<TestingMode, { parameters: Record<string, unknown>; targetRefs: TestingTargetReference[] }> = {
  smoke: {
    parameters: { timeout_sec: 120, parallelism: 1, strict: false },
    targetRefs: [{ target_type: 'strategy', target_id: 'mean_revert.v1', label: 'Mean Revert v1' }],
  },
  acceptance: {
    parameters: { timeout_sec: 900, parallelism: 2, strict: true },
    targetRefs: [{ target_type: 'model', target_id: 'hmm_regime_switching', label: 'HMM model deployment gate' }],
  },
  regression: {
    parameters: { timeout_sec: 1800, parallelism: 4, strict: true },
    targetRefs: [{ target_type: 'suite', target_id: 'nightly_regression', label: 'Nightly regression suite' }],
  },
};

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

export function TestingPage({ baseUrl }: TestingPageProps): JSX.Element {
  const client = useMemo(() => new GbApiClient({ baseHttpUrl: baseUrl }), [baseUrl]);
  const [searchParams, setSearchParams] = useSearchParams();
  const [runs, setRuns] = useState<TestingRunItem[]>([]);
  const [mode, setMode] = useState<TestingMode>('smoke');
  const [parametersJson, setParametersJson] = useState(JSON.stringify(MODE_PRESETS.smoke.parameters, null, 2));
  const [targetRefsJson, setTargetRefsJson] = useState(JSON.stringify(MODE_PRESETS.smoke.targetRefs, null, 2));
  const [summary, setSummary] = useState('No testing run selected.');
  const [eventsByJob, setEventsByJob] = useState<Record<string, RunEvent[]>>({});
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
    setError(null);
    try {
      const runPayload = await requestJson<TestingRunItem[]>(baseUrl, '/api/v1/testing-runs');
      setRuns(runPayload);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Failed loading testing runs.');
    }
  }, [baseUrl]);

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
        if (selectedRun?.job_id === jobId) {
          setSummary(`${nextEvent.status}: ${nextEvent.detail}`);
        }
      },
    });

    return () => connection.close();
  }, [client, selectedRun]);

  const applyPreset = (nextMode: TestingMode): void => {
    setMode(nextMode);
    setParametersJson(JSON.stringify(MODE_PRESETS[nextMode].parameters, null, 2));
    setTargetRefsJson(JSON.stringify(MODE_PRESETS[nextMode].targetRefs, null, 2));
  };

  const launchRun = async (): Promise<void> => {
    setError(null);
    let parsedParameters: Record<string, unknown>;
    let parsedTargetRefs: TestingTargetReference[];

    try {
      parsedParameters = JSON.parse(parametersJson) as Record<string, unknown>;
    } catch {
      setError('Parameters must be valid JSON.');
      return;
    }

    try {
      parsedTargetRefs = JSON.parse(targetRefsJson) as TestingTargetReference[];
      if (!Array.isArray(parsedTargetRefs)) {
        throw new Error('Target refs must be an array.');
      }
    } catch {
      setError('Target refs must be valid JSON array.');
      return;
    }

    try {
      const created = await requestJson<TestingRunItem>(baseUrl, '/api/v1/testing-runs', {
        method: 'POST',
        body: JSON.stringify({
          mode,
          target_refs: parsedTargetRefs,
          parameters: parsedParameters,
        }),
      });
      setRuns((previous) => [created, ...previous]);
      setSelectedJobId(created.job_id);
      setSummary('queued: testing run accepted by api-control-plane');
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : 'Failed launching testing run.');
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
      <h2>Testing</h2>
      <p className="muted"><strong>Warning:</strong> test execution is server-side only. This page only submits requests and renders server outputs.</p>
      {error ? <p className="muted">Error: {error}</p> : null}

      <div className="card" style={{ marginBottom: '1rem', maxWidth: '680px' }}>
        <h3>Launch testing run</h3>
        <div style={{ display: 'grid', gap: '0.5rem' }}>
          <label>
            Mode
            <select value={mode} onChange={(event) => applyPreset(event.target.value as TestingMode)}>
              <option value="smoke">smoke</option>
              <option value="acceptance">acceptance</option>
              <option value="regression">regression</option>
            </select>
          </label>
          <label>
            Targets (JSON array)
            <textarea value={targetRefsJson} onChange={(event) => setTargetRefsJson(event.target.value)} rows={4} />
          </label>
          <label>
            Parameters (JSON)
            <textarea value={parametersJson} onChange={(event) => setParametersJson(event.target.value)} rows={5} />
          </label>
          <button type="button" onClick={() => void launchRun()}>Launch testing run</button>
        </div>
      </div>

      <div className="card jobs-card">
        <table className="jobs-table">
          <thead><tr><th>ID</th><th>Job ID</th><th>Mode</th><th>Status</th><th>Created</th></tr></thead>
          <tbody>
            {runs.length === 0 ? <tr><td colSpan={5}>No testing runs yet.</td></tr> : null}
            {runs.map((run) => (
              <tr key={run.id} onClick={() => setSelectedJobId(run.job_id)} style={{ cursor: 'pointer', background: selectedJobId === run.job_id ? 'rgba(127,127,127,0.12)' : undefined }}>
                <td>{run.id.slice(0, 8)}</td>
                <td>{run.job_id.slice(0, 8)}</td>
                <td>{run.mode}</td>
                <td>{run.status}</td>
                <td>{new Date(run.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <JobLifecyclePanel
        submitContent={<p>Mode presets are editable; selected run remains addressable via <code>?job_id=...</code>.</p>}
        runningContent={!selectedRun ? <p className="muted">Select a run to inspect progress and terminal status.</p> : (
          <>
            <p><strong>Run:</strong> {selectedRun.id}</p>
            <p><strong>Persisted summary:</strong> {summary}</p>
            <ul>
              {(eventsByJob[selectedRun.job_id] ?? []).map((event, index) => (
                <li key={`${event.timestamp}-${index}`}>{new Date(event.timestamp).toLocaleTimeString()} · {event.status} · {event.detail}</li>
              ))}
              {(eventsByJob[selectedRun.job_id] ?? []).length === 0 ? <li>No live server events yet.</li> : null}
            </ul>
          </>
        )}
        artifactContent={!selectedRun ? <p className="muted">Select a run to inspect result summaries.</p> : (
          <div style={{ display: 'grid', gap: '0.75rem' }}>
            <div className="card" style={{ maxWidth: '100%' }}>
              <h4>Passed checks</h4>
              <ul>
                {(selectedRun.result_summary?.passed_checks ?? []).map((check) => <li key={check}>{check}</li>)}
                {(selectedRun.result_summary?.passed_checks ?? []).length === 0 ? <li className="muted">No passed checks published by server.</li> : null}
              </ul>
            </div>
            <div className="card" style={{ maxWidth: '100%' }}>
              <h4>Failed checks</h4>
              <ul>
                {(selectedRun.result_summary?.failed_checks ?? []).map((check) => <li key={check}>{check}</li>)}
                {(selectedRun.result_summary?.failed_checks ?? []).length === 0 ? <li className="muted">No failed checks published by server.</li> : null}
              </ul>
            </div>
            <div className="card" style={{ maxWidth: '100%' }}>
              <h4>Linked logs / artifacts</h4>
              <ul>
                {(selectedRun.result_summary?.log_artifacts ?? []).map((artifact) => (
                  <li key={`${artifact.artifact_type}-${artifact.artifact_ref}`}>
                    <strong>{artifact.artifact_type}:</strong> {artifact.label ? `${artifact.label} · ` : ''}<a href={artifact.artifact_ref} target="_blank" rel="noreferrer">{artifact.artifact_ref}</a>
                  </li>
                ))}
                {(selectedRun.result_summary?.log_artifacts ?? []).length === 0 ? <li className="muted">No artifact references published by server.</li> : null}
              </ul>
            </div>
            <p><Link to={`/jobs/${encodeURIComponent(selectedRun.job_id)}`}>Open job detail view for job {selectedRun.job_id}</Link></p>
          </div>
        )}
      />
    </section>
  );
}
