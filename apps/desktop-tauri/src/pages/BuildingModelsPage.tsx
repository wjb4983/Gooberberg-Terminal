import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { createDesktopApiClient } from '../api/client';
import { requestJson } from '../api/requestJson';
import { SUBTASK_TYPES, TASK_TYPES, type SubtaskType, type TaskType } from '../types/api';

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
  task_type: TaskType;
  subtask_type: SubtaskType;
  job_id: string;
  status: string;
  parameters: Record<string, unknown>;
  created_at: string;
}

interface ModelConfigFormState {
  numRegimes: string;
  lookbackWindow: string;
  covarianceType: CovarianceType;
  convergenceTol: string;
  maxIterations: string;
}

interface SharedConfigFields {
  name: string;
  version: string;
  taskType: TaskType;
  subtaskType: SubtaskType;
  dataProfile: string;
}

interface TorchFormState {
  lookbackWindow: string;
  horizonSteps: string;
  preset: 'fast' | 'balanced' | 'accurate';
  mode: 'simple' | 'advanced';
  architecture: 'lstm' | 'gru' | 'tcn' | 'transformer_encoder';
  optionsJson: string;
}

interface KalmanFormState {
  transitionStructure: 'identity' | 'constant_velocity' | 'custom';
  stateDimension: string;
  observationDimension: string;
  processNoise: string;
  measurementNoise: string;
  initialCovarianceScale: string;
}

interface TrainingLaunchFormState {
  modelConfigId: string;
  datasetId: string;
  taskType: TaskType;
  subtaskType: SubtaskType;
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

interface ArtifactSummary {
  id: number;
  artifact_ref: string;
  checksum: string;
  size_bytes: number;
  best_metric: number | null;
  created_at: string;
}

interface ArtifactDetail extends ArtifactSummary {
  last_accessed_at: string;
  retention_class: string;
  metrics: Record<string, unknown>;
  notes: string | null;
}

interface FormErrors {
  [key: string]: string;
}

interface TrainingRunCompatibilityStatus {
  modelConfigId: string;
  compatible: boolean;
  warnings: string[];
  errors: string[];
}

interface TrainingRunValidationResponse {
  normalized_payload: {
    model_config_id: string;
    dataset_id: string;
    task_type: TaskType;
    subtask_type: SubtaskType;
    parameters: Record<string, unknown>;
  };
  warnings: string[];
  errors: string[];
  compatible: boolean;
  valid: boolean;
}

const defaultModelConfigForm: ModelConfigFormState = {
  numRegimes: '3',
  lookbackWindow: '252',
  covarianceType: 'diag',
  convergenceTol: '0.001',
  maxIterations: '200',
};

const defaultSharedConfigFields: SharedConfigFields = {
  name: '',
  version: 'v1',
  taskType: 'time_series_momentum',
  subtaskType: 'ranking',
  dataProfile: 'time_series',
};

const defaultTorchFormState: TorchFormState = {
  lookbackWindow: '96',
  horizonSteps: '24',
  preset: 'balanced',
  mode: 'simple',
  architecture: 'transformer_encoder',
  optionsJson: JSON.stringify({
    hidden_size: 128,
    num_layers: 2,
    num_attention_heads: 8,
    dropout: 0.1,
    learning_rate: 0.001,
    batch_size: 64,
    loss_function: 'mse',
  }, null, 2),
};

const defaultKalmanFormState: KalmanFormState = {
  transitionStructure: 'constant_velocity',
  stateDimension: '6',
  observationDimension: '6',
  processNoise: '0.2',
  measurementNoise: '0.1',
  initialCovarianceScale: '1.0',
};

const defaultTrainingLaunchForm: TrainingLaunchFormState = {
  modelConfigId: '',
  datasetId: 'equities_daily_v1',
  taskType: 'time_series_momentum',
  subtaskType: 'ranking',
  epochs: '20',
  seed: '42',
  learningRate: '0.001',
  batchSize: '64',
};

function buildHmmPayload(form: ModelConfigFormState, shared: SharedConfigFields): Record<string, unknown> {
  return {
    name: shared.name.trim(),
    version: shared.version.trim(),
    task_type: shared.taskType,
    subtask_type: shared.subtaskType,
    data_profile: shared.dataProfile.trim(),
    n_states: Number(form.numRegimes),
    lookback_window: Number(form.lookbackWindow),
    covariance_type: form.covarianceType,
    convergence_tol: Number(form.convergenceTol),
    max_iterations: Number(form.maxIterations),
  };
}

function validateModelConfig(form: ModelConfigFormState, shared: SharedConfigFields): FormErrors {
  const errors: FormErrors = {};
  if (!shared.name.trim()) {
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
  const convergenceTol = Number(form.convergenceTol);
  if (!Number.isFinite(convergenceTol) || convergenceTol <= 0 || convergenceTol > 1) {
    errors.convergenceTol = 'Convergence tolerance must be > 0 and <= 1.';
  }
  const maxIterations = Number(form.maxIterations);
  if (!Number.isFinite(maxIterations) || maxIterations < 10) {
    errors.maxIterations = 'Max iterations must be a number >= 10.';
  }
  return errors;
}

function buildTorchPayload(form: TorchFormState, shared: SharedConfigFields): Record<string, unknown> {
  const presets: Record<TorchFormState['preset'], Record<string, unknown>> = {
    fast: { architecture: 'gru', hidden_size: 64, num_layers: 1, num_attention_heads: 1, dropout: 0.05, learning_rate: 0.001, batch_size: 128, loss_function: 'mse' },
    balanced: { architecture: 'transformer_encoder', hidden_size: 128, num_layers: 2, num_attention_heads: 8, dropout: 0.1, learning_rate: 0.001, batch_size: 64, loss_function: 'mse' },
    accurate: { architecture: 'transformer_encoder', hidden_size: 256, num_layers: 4, num_attention_heads: 8, dropout: 0.2, learning_rate: 0.0005, batch_size: 32, loss_function: 'huber' },
  };
  const advancedOptions = form.mode === 'advanced'
    ? (JSON.parse(form.optionsJson) as Record<string, unknown>)
    : {};
  return {
    name: shared.name.trim(),
    version: shared.version.trim(),
    task_type: shared.taskType,
    subtask_type: shared.subtaskType,
    data_type: shared.dataProfile.trim() || 'time_series',
    lookback_window: Number(form.lookbackWindow),
    horizon_steps: Number(form.horizonSteps),
    ...(form.mode === 'simple' ? presets[form.preset] : { architecture: form.architecture, ...advancedOptions }),
  };
}

function buildKalmanPayload(form: KalmanFormState, shared: SharedConfigFields): Record<string, unknown> {
  return {
    name: shared.name.trim(),
    version: shared.version.trim(),
    task_type: shared.taskType,
    subtask_type: shared.subtaskType,
    data_type: shared.dataProfile.trim() || 'state_space_timeseries',
    transition_structure: form.transitionStructure,
    state_dimension: Number(form.stateDimension),
    observation_dimension: Number(form.observationDimension),
    process_noise: Number(form.processNoise),
    measurement_noise: Number(form.measurementNoise),
    initial_covariance_scale: Number(form.initialCovarianceScale),
  };
}

function FamilyConfigSection({ children }: { children: ReactNode }): JSX.Element {
  return <div style={{ display: 'grid', gap: '0.5rem' }}>{children}</div>;
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
      task_type: run.task_type,
      subtask_type: run.subtask_type,
      parameters: run.parameters,
    },
    source: 'training-run',
  };
}

export function BuildingModelsPage({ baseUrl }: BuildingModelsPageProps): JSX.Element {
  const client = useMemo(() => createDesktopApiClient({ baseHttpUrl: baseUrl }), [baseUrl]);
  const lastSeqRef = useRef<number | undefined>(undefined);

  const [modelConfigs, setModelConfigs] = useState<ModelConfigItem[]>([]);
  const [modelFamilies, setModelFamilies] = useState<string[]>([]);
  const [selectedFamily, setSelectedFamily] = useState('hmm_regime_switching');
  const [jobs, setJobs] = useState<JobCard[]>([]);

  const [sharedConfig, setSharedConfig] = useState<SharedConfigFields>(defaultSharedConfigFields);
  const [configForm, setConfigForm] = useState<ModelConfigFormState>(defaultModelConfigForm);
  const [torchForm, setTorchForm] = useState<TorchFormState>(defaultTorchFormState);
  const [kalmanForm, setKalmanForm] = useState<KalmanFormState>(defaultKalmanFormState);
  const [launchForm, setLaunchForm] = useState<TrainingLaunchFormState>(defaultTrainingLaunchForm);

  const [configErrors, setConfigErrors] = useState<FormErrors>({});
  const [launchErrors, setLaunchErrors] = useState<FormErrors>({});
  const [compatibilityStatuses, setCompatibilityStatuses] = useState<Record<string, TrainingRunCompatibilityStatus>>({});
  const [compatibilityLoading, setCompatibilityLoading] = useState(false);

  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isCreatingConfig, setIsCreatingConfig] = useState(false);
  const [isLaunchingRun, setIsLaunchingRun] = useState(false);
  const [jobActionPendingId, setJobActionPendingId] = useState<string | null>(null);
  const [artifactSummaries, setArtifactSummaries] = useState<ArtifactSummary[]>([]);
  const [selectedArtifactId, setSelectedArtifactId] = useState<number | null>(null);
  const [artifactDetailsById, setArtifactDetailsById] = useState<Record<number, ArtifactDetail>>({});

  const selectedJob = useMemo(() => jobs.find((item) => item.id === selectedJobId) ?? null, [jobs, selectedJobId]);
  const selectedArtifact = selectedArtifactId ? artifactDetailsById[selectedArtifactId] : undefined;

  const load = useCallback(async (): Promise<void> => {
    setError(null);
    try {
      const [configs, runs, families] = await Promise.all([
        requestJson<ModelConfigItem[]>(baseUrl, '/api/v1/model-configs'),
        requestJson<TrainingRunItem[]>(baseUrl, '/api/v1/training-runs'),
        requestJson<string[]>(baseUrl, '/api/v1/models/deployments/families'),
      ]);
      setModelConfigs(configs);
      setModelFamilies(families);
      setSelectedFamily((previous) => (families.includes(previous) ? previous : (families[0] ?? 'hmm_regime_switching')));
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

  useEffect(() => {
    if (!selectedJob || selectedJob.status !== 'success') {
      setArtifactSummaries([]);
      setSelectedArtifactId(null);
      return;
    }
    void requestJson<ArtifactSummary[]>(baseUrl, `/api/v1/jobs/${encodeURIComponent(selectedJob.id)}/artifacts`)
      .then((items) => {
        setArtifactSummaries(items);
        setSelectedArtifactId((previous) => previous ?? (items[0]?.id ?? null));
      })
      .catch(() => {
        setArtifactSummaries([]);
        setSelectedArtifactId(null);
      });
  }, [baseUrl, selectedJob]);

  const loadArtifactDetail = useCallback(async (artifactId: number): Promise<void> => {
    if (!selectedJob) return;
    if (artifactDetailsById[artifactId]) {
      setSelectedArtifactId(artifactId);
      return;
    }
    const detail = await requestJson<ArtifactDetail>(
      baseUrl,
      `/api/v1/jobs/${encodeURIComponent(selectedJob.id)}/artifacts/${artifactId}`,
    );
    setArtifactDetailsById((previous) => ({ ...previous, [artifactId]: detail }));
    setSelectedArtifactId(artifactId);
  }, [artifactDetailsById, baseUrl, selectedJob]);

  const submitConfig = async (): Promise<void> => {
    const validation = selectedFamily === 'hmm_regime_switching' ? validateModelConfig(configForm, sharedConfig) : {};
    if (!sharedConfig.name.trim()) {
      validation.name = 'Model name is required so it is easy to select for later training jobs.';
    }
    if (selectedFamily === 'torch_nn_timeseries' && torchForm.mode === 'advanced') {
      try {
        JSON.parse(torchForm.optionsJson);
      } catch {
        validation.optionsJson = 'Advanced options must be valid JSON.';
      }
    }
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
          model_family: selectedFamily,
          config: selectedFamily === 'hmm_regime_switching'
            ? buildHmmPayload(configForm, sharedConfig)
            : selectedFamily === 'torch_nn_timeseries'
              ? buildTorchPayload(torchForm, sharedConfig)
              : buildKalmanPayload(kalmanForm, sharedConfig),
        }),
      });
      setModelConfigs((previous) => [created, ...previous]);
      setLaunchForm((previous) => ({ ...previous, modelConfigId: created.id }));
      setConfigForm(defaultModelConfigForm);
      setSharedConfig(defaultSharedConfigFields);
      setTorchForm(defaultTorchFormState);
      setKalmanForm(defaultKalmanFormState);
      setConfigErrors({});
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Failed to create model config.');
    } finally {
      setIsCreatingConfig(false);
    }
  };

  useEffect(() => {
    if (!launchForm.datasetId.trim() || modelConfigs.length === 0) {
      setCompatibilityStatuses({});
      return;
    }

    let cancelled = false;
    const loadCompatibility = async (): Promise<void> => {
      setCompatibilityLoading(true);
      try {
        const responses = await Promise.all(modelConfigs.map(async (modelConfig) => {
          const payload = await requestJson<TrainingRunValidationResponse>(baseUrl, '/api/v1/training-runs/compatibility', {
            method: 'POST',
            body: JSON.stringify({
              model_config_id: modelConfig.id,
              dataset_id: launchForm.datasetId.trim(),
              task_type: launchForm.taskType,
              subtask_type: launchForm.subtaskType,
              parameters: {},
            }),
          });
          return [modelConfig.id, {
            modelConfigId: modelConfig.id,
            compatible: payload.compatible,
            warnings: payload.warnings,
            errors: payload.errors,
          }] as const;
        }));
        if (!cancelled) {
          setCompatibilityStatuses(Object.fromEntries(responses));
        }
      } catch {
        if (!cancelled) {
          setCompatibilityStatuses({});
        }
      } finally {
        if (!cancelled) {
          setCompatibilityLoading(false);
        }
      }
    };

    void loadCompatibility();
    return () => {
      cancelled = true;
    };
  }, [baseUrl, launchForm.datasetId, launchForm.subtaskType, launchForm.taskType, modelConfigs]);

  const launchTrainingRun = async (): Promise<void> => {
    const optimisticId = `optimistic-${crypto.randomUUID()}`;
    const nowIso = new Date().toISOString();
    const draftPayload = {
      model_config_id: launchForm.modelConfigId,
      dataset_id: launchForm.datasetId.trim(),
      task_type: launchForm.taskType,
      subtask_type: launchForm.subtaskType,
      parameters: {
        epochs: Number(launchForm.epochs),
        seed: Number(launchForm.seed),
        learning_rate: Number(launchForm.learningRate),
        batch_size: Number(launchForm.batchSize),
      },
    };

    setError(null);
    setIsLaunchingRun(true);
    setLaunchErrors({});

    try {
      const preflight = await requestJson<TrainingRunValidationResponse>(baseUrl, '/api/v1/training-runs/preflight', {
        method: 'POST',
        body: JSON.stringify(draftPayload),
      });
      if (!preflight.valid) {
        setLaunchErrors({ submit: preflight.errors.join(' ') || 'Preflight failed.' });
        return;
      }
      if (preflight.warnings.length > 0) {
        setError(preflight.warnings.join(' '));
      }
      const payload = preflight.normalized_payload;

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
        <FamilyConfigSection>
          <select value={selectedFamily} onChange={(event) => setSelectedFamily(event.target.value)}>
            {[...new Set(modelFamilies.length > 0 ? modelFamilies : ['hmm_regime_switching', 'torch_nn_timeseries', 'kalman_filter'])].map((family) => (
              <option key={family} value={family}>{family}</option>
            ))}
          </select>
          <input value={sharedConfig.name} onChange={(event) => setSharedConfig((prev) => ({ ...prev, name: event.target.value }))} placeholder="Model name" />
          {configErrors.name ? <small className="muted">{configErrors.name}</small> : null}
          <input value={sharedConfig.version} onChange={(event) => setSharedConfig((prev) => ({ ...prev, version: event.target.value }))} placeholder="Version" />
          <select value={sharedConfig.taskType} onChange={(event) => setSharedConfig((prev) => ({ ...prev, taskType: event.target.value as TaskType }))}>
            {TASK_TYPES.map((taskType) => <option key={taskType} value={taskType}>{taskType}</option>)}
          </select>
          <select value={sharedConfig.subtaskType} onChange={(event) => setSharedConfig((prev) => ({ ...prev, subtaskType: event.target.value as SubtaskType }))}>
            {SUBTASK_TYPES.map((subtaskType) => <option key={subtaskType} value={subtaskType}>{subtaskType}</option>)}
          </select>
          <input value={sharedConfig.dataProfile} onChange={(event) => setSharedConfig((prev) => ({ ...prev, dataProfile: event.target.value }))} placeholder="Data profile" />

          {selectedFamily === 'hmm_regime_switching' ? (
            <>
              <input value={configForm.numRegimes} onChange={(event) => setConfigForm((prev) => ({ ...prev, numRegimes: event.target.value }))} placeholder="Num regimes" />
              {configErrors.numRegimes ? <small className="muted">{configErrors.numRegimes}</small> : null}
              <input value={configForm.lookbackWindow} onChange={(event) => setConfigForm((prev) => ({ ...prev, lookbackWindow: event.target.value }))} placeholder="Lookback window" />
              {configErrors.lookbackWindow ? <small className="muted">{configErrors.lookbackWindow}</small> : null}
              <select value={configForm.covarianceType} onChange={(event) => setConfigForm((prev) => ({ ...prev, covarianceType: event.target.value as CovarianceType }))}>
                <option value="diag">diag</option>
                <option value="full">full</option>
              </select>
              <input value={configForm.convergenceTol} onChange={(event) => setConfigForm((prev) => ({ ...prev, convergenceTol: event.target.value }))} placeholder="Convergence tolerance" />
              {configErrors.convergenceTol ? <small className="muted">{configErrors.convergenceTol}</small> : null}
              <input value={configForm.maxIterations} onChange={(event) => setConfigForm((prev) => ({ ...prev, maxIterations: event.target.value }))} placeholder="Max iterations" />
              {configErrors.maxIterations ? <small className="muted">{configErrors.maxIterations}</small> : null}
            </>
          ) : null}

          {selectedFamily === 'torch_nn_timeseries' ? (
            <>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button type="button" onClick={() => setTorchForm((prev) => ({ ...prev, mode: 'simple' }))} disabled={torchForm.mode === 'simple'}>Simple mode</button>
                <button type="button" onClick={() => setTorchForm((prev) => ({ ...prev, mode: 'advanced' }))} disabled={torchForm.mode === 'advanced'}>Advanced mode</button>
              </div>
              <input value={torchForm.lookbackWindow} onChange={(event) => setTorchForm((prev) => ({ ...prev, lookbackWindow: event.target.value }))} placeholder="Lookback window" />
              <input value={torchForm.horizonSteps} onChange={(event) => setTorchForm((prev) => ({ ...prev, horizonSteps: event.target.value }))} placeholder="Horizon steps" />
              {torchForm.mode === 'simple' ? (
                <select value={torchForm.preset} onChange={(event) => setTorchForm((prev) => ({ ...prev, preset: event.target.value as TorchFormState['preset'] }))}>
                  <option value="fast">fast</option>
                  <option value="balanced">balanced</option>
                  <option value="accurate">accurate</option>
                </select>
              ) : (
                <>
                  <select value={torchForm.architecture} onChange={(event) => setTorchForm((prev) => ({ ...prev, architecture: event.target.value as TorchFormState['architecture'] }))}>
                    <option value="lstm">lstm</option><option value="gru">gru</option><option value="tcn">tcn</option><option value="transformer_encoder">transformer_encoder</option>
                  </select>
                  <textarea value={torchForm.optionsJson} onChange={(event) => setTorchForm((prev) => ({ ...prev, optionsJson: event.target.value }))} rows={8} />
                  {configErrors.optionsJson ? <small className="muted">{configErrors.optionsJson}</small> : null}
                </>
              )}
            </>
          ) : null}

          {selectedFamily === 'kalman_filter' ? (
            <>
              <select value={kalmanForm.transitionStructure} onChange={(event) => setKalmanForm((prev) => ({ ...prev, transitionStructure: event.target.value as KalmanFormState['transitionStructure'] }))}>
                <option value="identity">identity</option><option value="constant_velocity">constant_velocity</option><option value="custom">custom</option>
              </select>
              <input value={kalmanForm.stateDimension} onChange={(event) => setKalmanForm((prev) => ({ ...prev, stateDimension: event.target.value }))} placeholder="State dimension" />
              <input value={kalmanForm.observationDimension} onChange={(event) => setKalmanForm((prev) => ({ ...prev, observationDimension: event.target.value }))} placeholder="Observation dimension" />
              <input value={kalmanForm.processNoise} onChange={(event) => setKalmanForm((prev) => ({ ...prev, processNoise: event.target.value }))} placeholder="Process noise" />
              <input value={kalmanForm.measurementNoise} onChange={(event) => setKalmanForm((prev) => ({ ...prev, measurementNoise: event.target.value }))} placeholder="Measurement noise" />
              <input value={kalmanForm.initialCovarianceScale} onChange={(event) => setKalmanForm((prev) => ({ ...prev, initialCovarianceScale: event.target.value }))} placeholder="Initial covariance scale" />
            </>
          ) : null}
          <button type="button" disabled={isCreatingConfig} onClick={() => void submitConfig()}>{isCreatingConfig ? 'Creating…' : 'Create config'}</button>
        </FamilyConfigSection>
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
          <div style={{ border: '1px solid rgba(255,255,255,0.12)', borderRadius: '0.5rem', padding: '0.75rem' }}>
            <strong>Candidate compatibility</strong>
            <p className="muted" style={{ margin: '0.25rem 0 0.5rem 0' }}>Statuses come from /api/v1/training-runs/compatibility for selected dataset/task.</p>
            {compatibilityLoading ? <p className="muted" style={{ margin: 0 }}>Checking compatibility…</p> : null}
            {!compatibilityLoading && modelConfigs.length > 0 ? (
              <ul style={{ margin: 0, paddingLeft: '1.25rem', display: 'grid', gap: '0.35rem' }}>
                {modelConfigs.map((item) => {
                  const status = compatibilityStatuses[item.id];
                  const label = typeof item.config.name === 'string' ? item.config.name : item.id;
                  const state = !status ? 'unknown' : !status.compatible ? 'incompatible' : status.warnings.length > 0 ? 'warning' : 'compatible';
                  return (
                    <li key={`compat-${item.id}`}>
                      <span><code>{label}</code>: <strong>{state}</strong></span>
                      {status?.errors?.length ? <div className="muted">{status.errors.join(' ')}</div> : null}
                      {!status?.errors?.length && status?.warnings?.length ? <div className="muted">{status.warnings.join(' ')}</div> : null}
                    </li>
                  );
                })}
              </ul>
            ) : null}
          </div>
          <input value={launchForm.datasetId} onChange={(event) => setLaunchForm((prev) => ({ ...prev, datasetId: event.target.value }))} placeholder="Dataset ID" />
          {launchErrors.datasetId ? <small className="muted">{launchErrors.datasetId}</small> : null}
          <div style={{ display: 'grid', gap: '0.5rem', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))' }}>
            <select value={launchForm.taskType} onChange={(event) => setLaunchForm((prev) => ({ ...prev, taskType: event.target.value as TaskType }))}>
              {TASK_TYPES.map((taskType) => <option key={taskType} value={taskType}>{taskType}</option>)}
            </select>
            <select value={launchForm.subtaskType} onChange={(event) => setLaunchForm((prev) => ({ ...prev, subtaskType: event.target.value as SubtaskType }))}>
              {SUBTASK_TYPES.map((subtaskType) => <option key={subtaskType} value={subtaskType}>{subtaskType}</option>)}
            </select>
          </div>
          {launchErrors.subtaskType ? <small className="muted">{launchErrors.subtaskType}</small> : null}
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
          {launchErrors.submit ? <small className="muted">{launchErrors.submit}</small> : null}
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
            {artifactSummaries.length === 0 ? <p className="muted" style={{ margin: 0 }}>No artifact summaries persisted yet.</p> : null}
            {artifactSummaries.length > 0 ? (
              <ul style={{ marginTop: 0 }}>
                {artifactSummaries.map((summary) => (
                  <li key={summary.id}>
                    <button type="button" onClick={() => void loadArtifactDetail(summary.id)}>Load details</button>{' '}
                    <code>{summary.artifact_ref}</code> · {(summary.size_bytes / 1024).toFixed(1)} KB · {new Date(summary.created_at).toLocaleString()} · best metric: {summary.best_metric ?? 'n/a'}
                  </li>
                ))}
              </ul>
            ) : null}
            {selectedArtifact ? (
              <div className="card" style={{ marginTop: '0.25rem' }}>
                <p style={{ margin: 0 }}><strong>Selected artifact checksum:</strong> <code>{selectedArtifact.checksum}</code></p>
                <p style={{ margin: 0 }}><strong>Retention class:</strong> {selectedArtifact.retention_class}</p>
                <p style={{ margin: 0 }}><strong>Last accessed:</strong> {new Date(selectedArtifact.last_accessed_at).toLocaleString()}</p>
              </div>
            ) : null}
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
