import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { createDesktopApiClient } from '../api/client';
import { requestJson } from '../api/requestJson';
import { JobLifecyclePanel } from '../components/JobLifecyclePanel';
import { SUBTASK_TYPES, TASK_TYPES, type SubtaskType, type TaskType } from '../types/api';
import { ModelConfigSelect } from '../components/ModelConfigSelect';

interface TrainingRunsPageProps {
  baseUrl: string;
}

interface TrainingRunItem {
  id: string;
  model_config_id: string;
  dataset_id: string;
  dataset_spec_hash: string;
  dataset_manifest_version: string;
  resolved_symbol_count: number;
  resolved_member_count: number;
  model_config_version_tag: string;
  job_id: string;
  task_type: string;
  subtask_type: string;
  constraint_profile_version: string;
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

interface ArtifactSummaryItem {
  id: number;
  created_at: string;
}

interface ArtifactDetailItem extends ArtifactSummaryItem {
  metrics: Record<string, unknown>;
}

interface MetricDefinition {
  key: string;
  label: string;
  aliases?: string[];
}

interface MetricBundle {
  id: string;
  label: string;
  metrics: MetricDefinition[];
}

interface ResolvedMetric {
  bundleId: string;
  bundleLabel: string;
  definition: MetricDefinition;
  value: unknown;
}

const metricBundles: MetricBundle[] = [
  {
    id: 'ranking_signals',
    label: 'Ranking / Signals',
    metrics: [
      { key: 'precision_at_k', label: 'precision@k', aliases: ['precision@k', 'precision_at_top_k'] },
      { key: 'hit_rate', label: 'hit rate' },
      { key: 'turnover', label: 'turnover' },
      { key: 'net_information_ratio', label: 'net information ratio', aliases: ['information_ratio_net'] },
    ],
  },
  {
    id: 'volatility',
    label: 'Volatility',
    metrics: [
      { key: 'vol_mae', label: 'vol forecast MAE', aliases: ['mae_vol_forecast', 'mae'] },
      { key: 'vol_rmse', label: 'vol forecast RMSE', aliases: ['rmse_vol_forecast', 'rmse'] },
      { key: 'calibration_error', label: 'calibration error', aliases: ['vol_calibration_error'] },
    ],
  },
  {
    id: 'regime',
    label: 'Regime',
    metrics: [
      { key: 'regime_state_accuracy', label: 'regime-state accuracy', aliases: ['regime_accuracy'] },
      { key: 'regime_state_f1', label: 'regime-state F1', aliases: ['regime_f1'] },
      { key: 'transition_precision', label: 'transition precision' },
      { key: 'transition_recall', label: 'transition recall' },
    ],
  },
  {
    id: 'portfolio_realism',
    label: 'Portfolio realism',
    metrics: [
      { key: 'net_sharpe', label: 'net Sharpe', aliases: ['sharpe_net'] },
      { key: 'max_drawdown', label: 'max drawdown', aliases: ['max_drawdown_pct'] },
      { key: 'capacity_proxy', label: 'capacity proxy' },
      { key: 'cost_adjusted_return', label: 'cost-adjusted return', aliases: ['net_return_after_costs'] },
    ],
  },
];

const primaryMetricKeys: string[] = [
  'precision_at_k',
  'hit_rate',
  'vol_rmse',
  'regime_state_f1',
  'net_sharpe',
  'max_drawdown',
  'cost_adjusted_return',
];

function isModelCompatible(config: ModelConfigItem, taskType: TaskType): boolean {
  const configTaskType = typeof config.config.task_type === 'string' ? config.config.task_type : null;
  return configTaskType === null || configTaskType === taskType;
}

function flattenMetrics(metrics: Record<string, unknown>, prefix = ''): Record<string, unknown> {
  return Object.entries(metrics).reduce<Record<string, unknown>>((acc, [key, value]) => {
    const normalizedKey = prefix ? `${prefix}.${key}` : key;
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      return { ...acc, ...flattenMetrics(value as Record<string, unknown>, normalizedKey) };
    }
    acc[normalizedKey] = value;
    return acc;
  }, {});
}

function resolveMetric(metricMap: Record<string, unknown>, definition: MetricDefinition): unknown {
  const candidateKeys = [definition.key, ...(definition.aliases ?? [])];
  for (const candidate of candidateKeys) {
    if (candidate in metricMap) return metricMap[candidate];
  }
  const normalizedMetricMap = new Map<string, unknown>(
    Object.entries(metricMap).map(([key, value]) => [key.replace(/[.\s@_-]/g, '').toLowerCase(), value]),
  );
  for (const candidate of candidateKeys) {
    const normalizedCandidate = candidate.replace(/[.\s@_-]/g, '').toLowerCase();
    if (normalizedMetricMap.has(normalizedCandidate)) return normalizedMetricMap.get(normalizedCandidate);
  }
  return undefined;
}

function formatMetricValue(value: unknown): string {
  if (value === undefined || value === null) return 'n/a';
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) return String(value);
    if (Math.abs(value) >= 1000) return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
    if (Math.abs(value) < 0.01 && value !== 0) return value.toExponential(2);
    return value.toLocaleString(undefined, { maximumFractionDigits: 4 });
  }
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  if (Array.isArray(value)) return value.join(', ');
  return String(value);
}

export function TrainingRunsPage({ baseUrl }: TrainingRunsPageProps): JSX.Element {
  const client = useMemo(() => createDesktopApiClient({ baseHttpUrl: baseUrl }), [baseUrl]);
  const [searchParams, setSearchParams] = useSearchParams();
  const [runs, setRuns] = useState<TrainingRunItem[]>([]);
  const [configs, setConfigs] = useState<ModelConfigItem[]>([]);
  const [taskType, setTaskType] = useState<TaskType>('time_series_momentum');
  const [subtaskType, setSubtaskType] = useState<SubtaskType>('ranking');
  const [datasetId, setDatasetId] = useState('equities_daily_v1');
  const [parametersJson, setParametersJson] = useState('{"epochs": 20, "seed": 42}');
  const [selectedConfigId, setSelectedConfigId] = useState('');
  const [jobDetail, setJobDetail] = useState<string>('No live status yet.');
  const [eventsByJob, setEventsByJob] = useState<Record<string, RunEvent[]>>({});
  const [selectedRunMetrics, setSelectedRunMetrics] = useState<Record<string, unknown>>({});
  const [error, setError] = useState<string | null>(null);
  const lastSeqRef = useRef<number | undefined>(undefined);

  const selectedJobId = searchParams.get('job_id');
  const selectedRun = useMemo(() => runs.find((run) => run.job_id === selectedJobId) ?? null, [runs, selectedJobId]);
  const compatibleConfigs = useMemo(
    () => configs.filter((config) => isModelCompatible(config, taskType)),
    [configs, taskType],
  );

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
      const [runPayload, configPayload] = await Promise.all([
        requestJson<TrainingRunItem[]>(baseUrl, '/api/v1/training-runs'),
        requestJson<ModelConfigItem[]>(baseUrl, '/api/v1/model-configs'),
      ]);
      setRuns(runPayload);
      setConfigs(configPayload);
      const nextCompatibleConfigs = configPayload.filter((config) => isModelCompatible(config, taskType));
      if (!selectedConfigId && nextCompatibleConfigs.length > 0) {
        setSelectedConfigId(nextCompatibleConfigs[0].id);
      }
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Failed loading training runs.');
    }
  }, [baseUrl, selectedConfigId, taskType]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!compatibleConfigs.some((config) => config.id === selectedConfigId)) {
      setSelectedConfigId(compatibleConfigs[0]?.id ?? '');
    }
  }, [compatibleConfigs, selectedConfigId]);

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
      setError('Compatible model config is required.');
      return;
    }
    if (subtaskType === 'regime_state' && taskType !== 'regime_switching') {
      setError('Subtask regime_state can only be used with task regime_switching.');
      return;
    }

    try {
      const created = await requestJson<TrainingRunItem>(baseUrl, '/api/v1/training-runs', {
        method: 'POST',
        body: JSON.stringify({
          model_config_id: selectedConfigId,
          dataset_id: datasetId,
          task_type: taskType,
          subtask_type: subtaskType,
          parameters: parsedParameters,
        }),
      });
      setRuns((previous) => [created, ...previous]);
      setSelectedJobId(created.job_id);
      setJobDetail('queued: training run accepted by api-control-plane');
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : 'Failed launching training run.');
    }
  };

  useEffect(() => {
    const run = selectedRun;
    if (!run) return;
    setSelectedRunMetrics({});
    void requestJson<{ id: string; status: string; detail: string }>(baseUrl, `/api/v1/jobs/${encodeURIComponent(run.job_id)}`)
      .then((payload) => setJobDetail(`${payload.status}: ${payload.detail}`))
      .catch(() => setJobDetail('Unable to load persisted job summary.'));
    void requestJson<ArtifactSummaryItem[]>(baseUrl, `/api/v1/jobs/${encodeURIComponent(run.job_id)}/artifacts`)
      .then((artifacts) => {
        const latest = [...artifacts].sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at))[0];
        if (!latest) return;
        void requestJson<ArtifactDetailItem>(baseUrl, `/api/v1/jobs/${encodeURIComponent(run.job_id)}/artifacts/${latest.id}`)
          .then((detail) => setSelectedRunMetrics(detail.metrics ?? {}))
          .catch(() => setSelectedRunMetrics({}));
      })
      .catch(() => setSelectedRunMetrics({}));
  }, [baseUrl, selectedRun]);

  const resolvedMetrics = useMemo<ResolvedMetric[]>(() => {
    const flattened = flattenMetrics(selectedRunMetrics);
    return metricBundles.flatMap((bundle) => bundle.metrics.map((definition) => ({
      bundleId: bundle.id,
      bundleLabel: bundle.label,
      definition,
      value: resolveMetric(flattened, definition),
    })));
  }, [selectedRunMetrics]);

  const primaryMetrics = useMemo(
    () => resolvedMetrics.filter((metric) => primaryMetricKeys.includes(metric.definition.key)),
    [resolvedMetrics],
  );

  const secondaryMetricsByBundle = useMemo(() => metricBundles.map((bundle) => ({
    bundle,
    metrics: resolvedMetrics.filter((metric) => metric.bundleId === bundle.id && !primaryMetricKeys.includes(metric.definition.key)),
  })), [resolvedMetrics]);

  return (
    <section>
      <h2>Training Runs</h2>
      <p>Guide training launches through tasking, dataset, compatible model config, then run submission.</p>
      {error ? <p className="muted">Error: {error}</p> : null}
      <div className="card" style={{ marginBottom: '1rem' }}>
        <h3>1) Tasking</h3>
        <div style={{ display: 'grid', gap: '0.5rem', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))' }}>
          <label>
            Task
            <select value={taskType} onChange={(event) => setTaskType(event.target.value as TaskType)}>
              {TASK_TYPES.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          </label>
          <label>
            Subtask
            <select value={subtaskType} onChange={(event) => setSubtaskType(event.target.value as SubtaskType)}>
              {SUBTASK_TYPES.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          </label>
        </div>
      </div>
      <div className="card" style={{ marginBottom: '1rem' }}>
        <h3>2) Dataset</h3>
        <input value={datasetId} onChange={(event) => setDatasetId(event.target.value)} placeholder="Dataset ID" />
      </div>
      <div className="card" style={{ marginBottom: '1rem' }}>
        <h3>3) Compatible model config</h3>
        <ModelConfigSelect
          value={selectedConfigId}
          options={compatibleConfigs}
          onChange={setSelectedConfigId}
          emptyLabel="Select compatible model config"
          hint={`Showing configs compatible with ${taskType}.`}
        />
      </div>
      <div className="card" style={{ marginBottom: '1rem' }}>
        <h3>4) Run submission</h3>
        <div style={{ display: 'grid', gap: '0.5rem' }}>
          <textarea value={parametersJson} onChange={(event) => setParametersJson(event.target.value)} rows={4} />
          <button type="button" onClick={() => void launchRun()}>Launch training run</button>
        </div>
      </div>

      <div className="card jobs-card">
        <table className="jobs-table">
          <thead><tr><th>ID</th><th>Job ID</th><th>Model Config</th><th>Dataset</th><th>Status</th><th>Created</th></tr></thead>
          <tbody>
            {runs.length === 0 ? <tr><td colSpan={6}>No training runs yet.</td></tr> : null}
            {runs.map((run) => (
              <tr key={run.id} onClick={() => setSelectedJobId(run.job_id)} style={{ cursor: 'pointer', background: selectedJobId === run.job_id ? 'rgba(127,127,127,0.12)' : undefined }}>
                <td>{run.id.slice(0, 8)}</td><td>{run.job_id.slice(0, 8)}</td><td>{run.model_config_id.slice(0, 8)}</td><td>{run.dataset_id}</td><td>{run.status}</td><td>{new Date(run.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <JobLifecyclePanel
        submitContent={<p>Select config + dataset, then launch a server job. The selected run is restored by <code>?job_id=...</code>.</p>}
        runningContent={!selectedRun ? <p className="muted">Select a run to inspect persisted summary + live logs.</p> : (
          <>
            <p><strong>Run ID:</strong> {selectedRun.id}</p>
            <p><strong>Job:</strong> {selectedRun.job_id}</p>
            <p><strong>Task/Subtask:</strong> {selectedRun.task_type} / {selectedRun.subtask_type}</p>
            <p><strong>Dataset manifest:</strong> {selectedRun.dataset_manifest_version}</p>
            <p><strong>Dataset spec hash:</strong> <code>{selectedRun.dataset_spec_hash.slice(0, 16)}…</code></p>
            <p><strong>Resolved symbols/members:</strong> {selectedRun.resolved_symbol_count} / {selectedRun.resolved_member_count}</p>
            <p><strong>Model config version:</strong> {selectedRun.model_config_version_tag}</p>
            <p><strong>Constraint profile version:</strong> {selectedRun.constraint_profile_version}</p>
            <p><strong>Persisted summary:</strong> {jobDetail}</p>
            <div className="card" style={{ marginTop: '0.75rem', marginBottom: '0.75rem' }}>
              <h4 style={{ marginTop: 0 }}>Primary metrics</h4>
              <p className="muted" style={{ marginTop: 0 }}>Showing 7 key metrics by default. Expand bundles below for secondary metrics.</p>
              <table className="jobs-table" style={{ fontSize: '0.9rem' }}>
                <thead><tr><th>Metric</th><th>Bundle</th><th>Value</th></tr></thead>
                <tbody>
                  {primaryMetrics.map((metric) => (
                    <tr key={metric.definition.key}>
                      <td>{metric.definition.label}</td>
                      <td>{metric.bundleLabel}</td>
                      <td><code>{formatMetricValue(metric.value)}</code></td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {secondaryMetricsByBundle.map(({ bundle, metrics }) => (
                <details key={bundle.id} style={{ marginTop: '0.5rem' }}>
                  <summary>{bundle.label} secondary metrics</summary>
                  <table className="jobs-table" style={{ marginTop: '0.4rem', fontSize: '0.85rem' }}>
                    <thead><tr><th>Metric</th><th>Value</th></tr></thead>
                    <tbody>
                      {metrics.map((metric) => (
                        <tr key={metric.definition.key}>
                          <td>{metric.definition.label}</td>
                          <td><code>{formatMetricValue(metric.value)}</code></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </details>
              ))}
            </div>
            <ul>
              {(eventsByJob[selectedRun.job_id] ?? []).map((event, index) => (
                <li key={`${event.timestamp}-${index}`}>{new Date(event.timestamp).toLocaleTimeString()} · {event.status} · {event.detail}</li>
              ))}
              {(eventsByJob[selectedRun.job_id] ?? []).length === 0 ? <li>No live log events yet.</li> : null}
            </ul>
          </>
        )}
        artifactContent={!selectedRun ? <p className="muted">Select a run to open its detail route.</p> : <p><Link to={`/jobs/${encodeURIComponent(selectedRun.job_id)}`}>Open run detail view for job {selectedRun.job_id}</Link></p>}
      />
    </section>
  );
}
