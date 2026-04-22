import { GbApiClient } from '@gb/api-client';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

interface BuildingModelsPageProps {
  baseUrl: string;
}

type CovarianceType = 'full' | 'diag';
type JobLifecycleStatus = 'queued' | 'running' | 'success' | 'failed' | 'cancelled' | 'unknown';

interface ModelConfigItem {
  id: string;
  model_family: string;
  config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
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

interface ModelConfigFormState {
  name: string;
  numRegimes: string;
  lookbackWindow: string;
  covarianceType: CovarianceType;
  transitionRegularization: string;
  featureColumns: string;
  targetColumn: string;
}

interface TrainingLaunchFormState {
  modelConfigId: string;
  datasetId: string;
  epochs: string;
  seed: string;
  learningRate: string;
  batchSize: string;
}

interface JobCard {
  id: string;
  runId?: string;
  runType?: string;
  datasetId: string;
  modelConfigId: string;
  status: JobLifecycleStatus;
  detail: string;
  message: string;
  progressPct: number;
  createdAtIso: string;
  updatedAtIso: string;
  resultRef?: string;
  payload: Record<string, unknown>;
  isOptimistic?: boolean;
  source: 'training-run' | 'retry';
  provenance?: { parentJobId: string };
}

interface FormErrors {
  [key: string]: string;
}

const defaultModelConfigForm: ModelConfigFormState = {
  name: '',
  numRegimes: '3',
  lookbackWindow: '252',
  covarianceType: 'diag',
  transitionRegularization: '0.01',
  featureColumns: 'returns_1d,returns_5d,volatility_20d',
  targetColumn: 'returns_1d',
};

const defaultTrainingLaunchForm: TrainingLaunchFormState = {
  modelConfigId: '',
  datasetId: 'equities_daily_v1',
  epochs: '20',
  seed: '42',
  learningRate: '0.001',
  batchSize: '64',
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
  if (!response.ok) {
    throw new Error(`Request failed (${response.status}) for ${path}`);
  }
  return (await response.json()) as T;
}

function buildModelConfigPayload(form: ModelConfigFormState): Record<string, unknown> {
  return {
    name: form.name.trim(),
    num_regimes: Number(form.numRegimes),
    lookback_window: Number(form.lookbackWindow),
    covariance_type: form.covarianceType,
    transition_regularization: Number(form.transitionRegularization),
    feature_columns: form.featureColumns.split(',').map((item) => item.trim()).filter(Boolean),
    target_column: form.targetColumn.trim(),
  };
}

function validateModelConfig(form: ModelConfigFormState): FormErrors {
  const errors: FormErrors = {};
  if (!form.name.trim()) {
    errors.name = 'Model name is required so it is easy to select for later training jobs.';
  }
  const regimes = Number(form.numRegimes);
  if (!Number.isFinite(regimes) || regimes < 2) {
    errors.numRegimes = 'Number of regimes must be a number >= 2.';
  }
  const lookback = Number(form.lookbackWindow);
  if (!Number.isFinite(lookback) || lookback < 10) {
    errors.lookbackWindow = 'Lookback window must be a number >= 10.';
  }
  const regularization = Number(form.transitionRegularization);
  if (!Number.isFinite(regularization) || regularization < 0 || regularization > 1) {
    errors.transitionRegularization = 'Transition regularization must be between 0 and 1.';
  }
  if (form.featureColumns.split(',').map((item) => item.trim()).filter(Boolean).length === 0) {
    errors.featureColumns = 'Provide at least one feature column (comma-separated).';
  }
  if (!form.targetColumn.trim()) {
    errors.targetColumn = 'Target column is required.';
  }
  return errors;
}

function validateLaunchForm(form: TrainingLaunchFormState): FormErrors {
  const errors: FormErrors = {};
  if (!form.modelConfigId) {
    errors.modelConfigId = 'Choose a saved model config before launching training.';
  }
  if (!form.datasetId.trim()) {
    errors.datasetId = 'Dataset ID is required, e.g. equities_daily_v1.';
  }
  const epochs = Number(form.epochs);
  if (!Number.isFinite(epochs) || epochs < 1) {
    errors.epochs = 'Epochs must be a positive integer.';
  }
  const seed = Number(form.seed);
  if (!Number.isFinite(seed) || seed < 0) {
    errors.seed = 'Seed must be a non-negative integer.';
  }
  const learningRate = Number(form.learningRate);
  if (!Number.isFinite(learningRate) || learningRate <= 0 || learningRate > 1) {
    errors.learningRate = 'Learning rate must be > 0 and <= 1.';
  }
  const batchSize = Number(form.batchSize);
  if (!Number.isFinite(batchSize) || batchSize < 1) {
    errors.batchSize = 'Batch size must be a positive integer.';
  }
  return errors;
}

function mapRunToCard(run: TrainingRunItem): JobCard {
  return {
    id: run.job_id,
    runId: run.id,
    runType: 'training',
    datasetId: run.dataset_id,
    modelConfigId: run.model_config_id,
    status: (run.status as JobLifecycleStatus) ?? 'queued',
    detail: 'training run accepted by api-control-plane',
    message: run.status,
    progressPct: run.status === 'queued' ? 0 : 100,
    createdAtIso: run.created_at,
    updatedAtIso: run.created_at,
    payload: {
      model_config_id: run.model_config_id,
      dataset_id: run.dataset_id,
      parameters: run.parameters,
    },
    source: 'training-run',
  };
}

export function BuildingModelsPage({ baseUrl }: BuildingModelsPageProps): JSX.Element {
  const client = useMemo(() => new GbApiClient({ baseHttpUrl: baseUrl }), [baseUrl]);
  const lastSeqRef = useRef<number | undefined>(undefined);

  const [modelConfigs, setModelConfigs] = useState<ModelConfigItem[]>([]);
  const [jobs, setJobs] = useState<JobCard[]>([]);

  const [configForm, setConfigForm] = useState<ModelConfigFormState>(defaultModelConfigForm);
  const [launchForm, setLaunchForm] = useState<TrainingLaunchFormState>(defaultTrainingLaunchForm);

  const [configErrors, setConfigErrors] = useState<FormErrors>({});
  const [launchErrors, setLaunchErrors] = useState<FormErrors>({});

  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isCreatingConfig, setIsCreatingConfig] = useState(false);
  const [isLaunchingRun, setIsLaunchingRun] = useState(false);
  const [jobActionPendingId, setJobActionPendingId] = useState<string | null>(null);

  const selectedJob = useMemo(() => jobs.find((item) => item.id === selectedJobId) ?? null, [jobs, selectedJobId]);

  const load = useCallback(async (): Promise<void> => {
    setError(null);
    try {
      const [configs, runs] = await Promise.all([
        requestJson<ModelConfigItem[]>(baseUrl, '/api/v1/model-configs'),
        requestJson<TrainingRunItem[]>(baseUrl, '/api/v1/training-runs'),
      ]);
      setModelConfigs(configs);
      setJobs((previous) => {
        const hydrated = runs.map(mapRunToCard);
        const optimistic = previous.filter((item) => item.isOptimistic);
        return [...optimistic, ...hydrated];
      });
      setLaunchForm((previous) => ({
        ...previous,
        modelConfigId: previous.modelConfigId || configs[0]?.id || '',
      }));
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Failed loading model build workspace.');
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
        const status = typeof payload.status === 'string' ? (payload.status as JobLifecycleStatus) : 'unknown';
        const detail = typeof payload.detail === 'string' ? payload.detail : 'job update received';
        const message = typeof payload.message === 'string' ? payload.message : '';
        const progressPct = typeof payload.progress_pct === 'number' ? payload.progress_pct : 0;
        const updatedAtIso = typeof payload.updated_at === 'string' ? payload.updated_at : event.timestamp;

        setJobs((previous) => {
          const existing = previous.find((item) => item.id === jobId);
          if (!existing) return previous;
          return previous.map((item) => (
            item.id !== jobId
              ? item
              : {
                ...item,
                status,
                detail,
                message,
                progressPct,
                updatedAtIso,
                isOptimistic: false,
              }
          ));
        });
      },
    });
    return () => connection.close();
  }, [client]);

  useEffect(() => {
    if (!selectedJobId) return;
    void client.getJob(selectedJobId)
      .then((serverJob) => {
        setJobs((previous) => previous.map((item) => (
          item.id !== selectedJobId
            ? item
            : {
              ...item,
              status: serverJob.status as JobLifecycleStatus,
              detail: serverJob.detail,
              message: serverJob.message,
              progressPct: serverJob.progressPct,
              updatedAtIso: serverJob.updatedAtIso,
              resultRef: serverJob.resultRef,
              runId: serverJob.runId ?? item.runId,
              runType: serverJob.runType ?? item.runType,
            }
        )));
      })
      .catch(() => {
        // intentionally ignore intermittent fetch errors for selected card hydration
      });
  }, [client, selectedJobId]);

  const submitConfig = async (): Promise<void> => {
    const validation = validateModelConfig(configForm);
    setConfigErrors(validation);
    if (Object.keys(validation).length > 0) {
      return;
    }

    setError(null);
    setIsCreatingConfig(true);
    try {
      const created = await requestJson<ModelConfigItem>(baseUrl, '/api/v1/model-configs', {
        method: 'POST',
        body: JSON.stringify({
          model_family: 'hmm_regime_switching',
          config: buildModelConfigPayload(configForm),
        }),
      });
      setModelConfigs((previous) => [created, ...previous]);
      setLaunchForm((previous) => ({ ...previous, modelConfigId: created.id }));
      setConfigForm(defaultModelConfigForm);
      setConfigErrors({});
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Failed to create model config.');
    } finally {
      setIsCreatingConfig(false);
    }
  };

  const launchTrainingRun = async (): Promise<void> => {
    const validation = validateLaunchForm(launchForm);
    setLaunchErrors(validation);
    if (Object.keys(validation).length > 0) {
      return;
    }

    const optimisticId = `optimistic-${crypto.randomUUID()}`;
    const nowIso = new Date().toISOString();
    const payload = {
      model_config_id: launchForm.modelConfigId,
      dataset_id: launchForm.datasetId.trim(),
      parameters: {
        epochs: Number(launchForm.epochs),
        seed: Number(launchForm.seed),
        learning_rate: Number(launchForm.learningRate),
        batch_size: Number(launchForm.batchSize),
      },
    };

    setError(null);
    setIsLaunchingRun(true);

    setJobs((previous) => [{
      id: optimisticId,
      datasetId: payload.dataset_id,
      modelConfigId: payload.model_config_id,
      status: 'queued',
      detail: 'Submitting training run…',
      message: 'queued',
      progressPct: 0,
      createdAtIso: nowIso,
      updatedAtIso: nowIso,
      payload,
      isOptimistic: true,
      source: 'training-run',
    }, ...previous]);
    setSelectedJobId(optimisticId);

    try {
      const created = await requestJson<TrainingRunItem>(baseUrl, '/api/v1/training-runs', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      setJobs((previous) => previous.map((item) => (
        item.id !== optimisticId
          ? item
          : {
            ...item,
            id: created.job_id,
            runId: created.id,
            runType: 'training',
            status: (created.status as JobLifecycleStatus) ?? 'queued',
            detail: 'training run accepted by api-control-plane',
            message: created.status,
            createdAtIso: created.created_at,
            updatedAtIso: created.created_at,
            isOptimistic: false,
          }
      )));
      setSelectedJobId(created.job_id);
    } catch (submitError) {
      setJobs((previous) => previous.filter((item) => item.id !== optimisticId));
      setSelectedJobId(null);
      setError(submitError instanceof Error ? submitError.message : 'Failed launching training run.');
    } finally {
      setIsLaunchingRun(false);
    }
  };

  const cancelJob = async (jobId: string): Promise<void> => {
    setJobActionPendingId(jobId);
    setError(null);
    try {
      const cancelled = await client.cancelJob(jobId);
      setJobs((previous) => previous.map((item) => (
        item.id !== jobId
          ? item
          : {
            ...item,
            status: cancelled.status as JobLifecycleStatus,
            detail: cancelled.detail,
            message: cancelled.message,
            progressPct: cancelled.progressPct,
            updatedAtIso: cancelled.updatedAtIso,
            resultRef: cancelled.resultRef,
          }
      )));
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : 'Cancel request failed.');
    } finally {
      setJobActionPendingId(null);
    }
  };

  const retryJob = async (jobId: string): Promise<void> => {
    setJobActionPendingId(jobId);
    setError(null);
    try {
      const retried = await client.retryJob(jobId);
      const parent = jobs.find((item) => item.id === jobId);
      setJobs((previous) => [{
        id: retried.id,
        runId: retried.runId,
        runType: retried.runType,
        datasetId: parent?.datasetId ?? 'unknown',
        modelConfigId: parent?.modelConfigId ?? 'unknown',
        status: retried.status as JobLifecycleStatus,
        detail: retried.detail,
        message: retried.message,
        progressPct: retried.progressPct,
        createdAtIso: retried.updatedAtIso,
        updatedAtIso: retried.updatedAtIso,
        payload: parent?.payload ?? {},
        source: 'retry',
        provenance: { parentJobId: jobId },
      }, ...previous]);
      setSelectedJobId(retried.id);
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : 'Retry request failed.');
    } finally {
      setJobActionPendingId(null);
    }
  };

  return (
    <section>
      <h2>Building Models</h2>
      <p>Create model configs, launch training, and manage queue lifecycle in one workspace.</p>
      {error ? <p className="muted">Error: {error}</p> : null}

      <div className="card" style={{ marginBottom: '1rem' }}>
        <h3>1) Create model config</h3>
        <div style={{ display: 'grid', gap: '0.5rem' }}>
          <input value={configForm.name} onChange={(event) => setConfigForm((prev) => ({ ...prev, name: event.target.value }))} placeholder="Config name" />
          {configErrors.name ? <small className="muted">{configErrors.name}</small> : null}
          <input value={configForm.numRegimes} onChange={(event) => setConfigForm((prev) => ({ ...prev, numRegimes: event.target.value }))} placeholder="Num regimes" />
          {configErrors.numRegimes ? <small className="muted">{configErrors.numRegimes}</small> : null}
          <input value={configForm.lookbackWindow} onChange={(event) => setConfigForm((prev) => ({ ...prev, lookbackWindow: event.target.value }))} placeholder="Lookback window" />
          {configErrors.lookbackWindow ? <small className="muted">{configErrors.lookbackWindow}</small> : null}
          <select value={configForm.covarianceType} onChange={(event) => setConfigForm((prev) => ({ ...prev, covarianceType: event.target.value as CovarianceType }))}>
            <option value="diag">diag</option>
            <option value="full">full</option>
          </select>
          <input
            value={configForm.transitionRegularization}
            onChange={(event) => setConfigForm((prev) => ({ ...prev, transitionRegularization: event.target.value }))}
            placeholder="Transition regularization"
          />
          {configErrors.transitionRegularization ? <small className="muted">{configErrors.transitionRegularization}</small> : null}
          <input value={configForm.featureColumns} onChange={(event) => setConfigForm((prev) => ({ ...prev, featureColumns: event.target.value }))} placeholder="Feature columns (comma-separated)" />
          {configErrors.featureColumns ? <small className="muted">{configErrors.featureColumns}</small> : null}
          <input value={configForm.targetColumn} onChange={(event) => setConfigForm((prev) => ({ ...prev, targetColumn: event.target.value }))} placeholder="Target column" />
          {configErrors.targetColumn ? <small className="muted">{configErrors.targetColumn}</small> : null}
          <button type="button" disabled={isCreatingConfig} onClick={() => void submitConfig()}>{isCreatingConfig ? 'Creating…' : 'Create config'}</button>
        </div>
      </div>

      <div className="card" style={{ marginBottom: '1rem' }}>
        <h3>2) Launch training job</h3>
        <div style={{ display: 'grid', gap: '0.5rem' }}>
          <select value={launchForm.modelConfigId} onChange={(event) => setLaunchForm((prev) => ({ ...prev, modelConfigId: event.target.value }))}>
            <option value="">Select model config</option>
            {modelConfigs.map((item) => (
              <option key={item.id} value={item.id}>{typeof item.config.name === 'string' ? item.config.name : item.id}</option>
            ))}
          </select>
          {launchErrors.modelConfigId ? <small className="muted">{launchErrors.modelConfigId}</small> : null}
          <input value={launchForm.datasetId} onChange={(event) => setLaunchForm((prev) => ({ ...prev, datasetId: event.target.value }))} placeholder="Dataset ID" />
          {launchErrors.datasetId ? <small className="muted">{launchErrors.datasetId}</small> : null}
          <div style={{ display: 'grid', gap: '0.5rem', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))' }}>
            <div>
              <input value={launchForm.epochs} onChange={(event) => setLaunchForm((prev) => ({ ...prev, epochs: event.target.value }))} placeholder="Epochs" />
              {launchErrors.epochs ? <small className="muted">{launchErrors.epochs}</small> : null}
            </div>
            <div>
              <input value={launchForm.seed} onChange={(event) => setLaunchForm((prev) => ({ ...prev, seed: event.target.value }))} placeholder="Seed" />
              {launchErrors.seed ? <small className="muted">{launchErrors.seed}</small> : null}
            </div>
            <div>
              <input value={launchForm.learningRate} onChange={(event) => setLaunchForm((prev) => ({ ...prev, learningRate: event.target.value }))} placeholder="Learning rate" />
              {launchErrors.learningRate ? <small className="muted">{launchErrors.learningRate}</small> : null}
            </div>
            <div>
              <input value={launchForm.batchSize} onChange={(event) => setLaunchForm((prev) => ({ ...prev, batchSize: event.target.value }))} placeholder="Batch size" />
              {launchErrors.batchSize ? <small className="muted">{launchErrors.batchSize}</small> : null}
            </div>
          </div>
          <button type="button" disabled={isLaunchingRun} onClick={() => void launchTrainingRun()}>{isLaunchingRun ? 'Submitting…' : 'Launch training job'}</button>
        </div>
      </div>

      <div className="card" style={{ marginBottom: '1rem' }}>
        <h3>3) Queue & run controls</h3>
        {jobs.length === 0 ? <p className="muted">No jobs yet.</p> : null}
        <div style={{ display: 'grid', gap: '0.75rem' }}>
          {jobs.map((job) => {
            const canCancel = job.status === 'queued' || job.status === 'running';
            const pending = jobActionPendingId === job.id;
            return (
              <article
                key={job.id}
                className="card"
                style={{ border: selectedJobId === job.id ? '1px solid #6c8cff' : undefined, cursor: 'pointer' }}
                onClick={() => setSelectedJobId(job.id)}
              >
                <p style={{ margin: 0 }}>
                  <strong>{job.status.toUpperCase()}</strong> · job <code>{job.id}</code>
                  {job.isOptimistic ? ' (optimistic)' : ''}
                </p>
                <p className="muted" style={{ margin: 0 }}>{job.detail}</p>
                <p className="muted" style={{ margin: 0 }}>
                  model_config: <code>{job.modelConfigId}</code> · dataset: <code>{job.datasetId}</code> · progress: {job.progressPct.toFixed(0)}%
                </p>
                {job.provenance ? <p className="muted" style={{ margin: 0 }}>retry provenance: prior job <code>{job.provenance.parentJobId}</code></p> : null}
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button type="button" disabled={pending || !canCancel} onClick={(event) => { event.stopPropagation(); void cancelJob(job.id); }}>
                    {pending && canCancel ? 'Cancelling…' : 'Cancel'}
                  </button>
                  <button type="button" disabled={pending} onClick={(event) => { event.stopPropagation(); void retryJob(job.id); }}>
                    {pending && !canCancel ? 'Retrying…' : 'Retry'}
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      </div>

      <div className="card">
        <h3>4) Artifacts</h3>
        {!selectedJob ? <p className="muted">Select a job to inspect artifact references.</p> : null}
        {selectedJob && selectedJob.status !== 'success' ? (
          <p className="muted">Artifacts are published when the selected job reaches <code>success</code>.</p>
        ) : null}
        {selectedJob && selectedJob.status === 'success' ? (
          <div style={{ display: 'grid', gap: '0.4rem' }}>
            <p style={{ margin: 0 }}><strong>result_ref:</strong> {selectedJob.resultRef ? <code>{selectedJob.resultRef}</code> : 'not yet provided'}</p>
            <p style={{ margin: 0 }}><strong>Metadata links:</strong></p>
            <ul>
              <li><a href={`${baseUrl}/api/v1/jobs/${encodeURIComponent(selectedJob.id)}`} target="_blank" rel="noreferrer">Job status payload</a></li>
              <li><a href={`${baseUrl}/api/v1/jobs/${encodeURIComponent(selectedJob.id)}/events`} target="_blank" rel="noreferrer">Job lifecycle events</a></li>
              {selectedJob.runId ? (
                <li>
                  <a href={`${baseUrl}/api/v1/training-runs/${encodeURIComponent(selectedJob.runId)}`} target="_blank" rel="noreferrer">Training run metadata</a>
                </li>
              ) : null}
            </ul>
          </div>
        ) : null}
      </div>
    </section>
  );
}
