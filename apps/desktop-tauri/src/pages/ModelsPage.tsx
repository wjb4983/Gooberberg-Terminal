import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { requestJson } from '../api/requestJson';

interface ModelsPageProps {
  baseUrl: string;
}

type CovarianceType = 'full' | 'diag';

interface SharedConfigFields {
  name: string;
  version: string;
  taskType: string;
  dataProfile: string;
}

interface HmmConfigFormState {
  numRegimes: string;
  lookbackWindow: string;
  covarianceType: CovarianceType;
  convergenceTol: string;
  maxIterations: string;
}

interface TorchFormState {
  mode: 'simple' | 'advanced';
  preset: 'fast' | 'balanced' | 'accurate';
  architecture: 'lstm' | 'gru' | 'tcn' | 'transformer_encoder';
  lookbackWindow: string;
  horizonSteps: string;
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

interface ModelConfigItem {
  id: string;
  model_family: string;
  config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

interface FormErrors { [key: string]: string; }

const defaultShared: SharedConfigFields = { name: '', version: 'v1', taskType: 'forecasting', dataProfile: 'time_series' };
const defaultTorch: TorchFormState = {
  mode: 'simple',
  preset: 'balanced',
  architecture: 'transformer_encoder',
  lookbackWindow: '96',
  horizonSteps: '24',
  optionsJson: JSON.stringify({ hidden_size: 128, num_layers: 2, num_attention_heads: 8, dropout: 0.1, learning_rate: 0.001, batch_size: 64, loss_function: 'mse' }, null, 2),
};
const defaultKalman: KalmanFormState = {
  transitionStructure: 'constant_velocity',
  stateDimension: '6',
  observationDimension: '6',
  processNoise: '0.2',
  measurementNoise: '0.1',
  initialCovarianceScale: '1.0',
};

const defaultFormState: HmmConfigFormState = {
  numRegimes: '2',
  lookbackWindow: '252',
  covarianceType: 'diag',
  convergenceTol: '0.001',
  maxIterations: '200',
};

function buildHmmConfig(state: HmmConfigFormState, shared: SharedConfigFields): Record<string, unknown> {
  return {
    name: shared.name.trim(),
    version: shared.version.trim(),
    task_type: shared.taskType.trim(),
    data_profile: shared.dataProfile.trim(),
    n_states: Number(state.numRegimes),
    lookback_window: Number(state.lookbackWindow),
    covariance_type: state.covarianceType,
    convergence_tol: Number(state.convergenceTol),
    max_iterations: Number(state.maxIterations),
  };
}

function validateForm(state: HmmConfigFormState, shared: SharedConfigFields): FormErrors {
  const errors: FormErrors = {};
  if (!shared.name.trim()) {
    errors.name = 'Name is required.';
  }
  const regimes = Number(state.numRegimes);
  if (!Number.isFinite(regimes) || regimes < 2) {
    errors.numRegimes = 'Number of regimes must be >= 2.';
  }
  const lookback = Number(state.lookbackWindow);
  if (!Number.isFinite(lookback) || lookback < 10) {
    errors.lookbackWindow = 'Lookback window must be >= 10.';
  }
  const convergenceTol = Number(state.convergenceTol);
  if (!Number.isFinite(convergenceTol) || convergenceTol <= 0 || convergenceTol > 1) {
    errors.convergenceTol = 'Convergence tolerance must be > 0 and <= 1.';
  }
  const maxIterations = Number(state.maxIterations);
  if (!Number.isFinite(maxIterations) || maxIterations < 10) {
    errors.maxIterations = 'Max iterations must be >= 10.';
  }
  return errors;
}

function formFromConfig(config: Record<string, unknown>): HmmConfigFormState {
  return {
    numRegimes: String(config.n_states ?? '2'),
    lookbackWindow: String(config.lookback_window ?? '252'),
    covarianceType: config.covariance_type === 'full' ? 'full' : 'diag',
    convergenceTol: String(config.convergence_tol ?? '0.001'),
    maxIterations: String(config.max_iterations ?? '200'),
  };
}

function FamilyConfigSection({ children }: { children: ReactNode }): JSX.Element {
  return <div style={{ display: 'grid', gap: '0.5rem' }}>{children}</div>;
}

export function ModelsPage({ baseUrl }: ModelsPageProps): JSX.Element {
  const [models, setModels] = useState<ModelConfigItem[]>([]);
  const [families, setFamilies] = useState<string[]>([]);
  const [selectedFamily, setSelectedFamily] = useState('hmm_regime_switching');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [shared, setShared] = useState<SharedConfigFields>(defaultShared);
  const [formState, setFormState] = useState<HmmConfigFormState>(defaultFormState);
  const [torchForm, setTorchForm] = useState<TorchFormState>(defaultTorch);
  const [kalmanForm, setKalmanForm] = useState<KalmanFormState>(defaultKalman);
  const [fieldErrors, setFieldErrors] = useState<FormErrors>({});

  const selectedModel = useMemo(
    () => models.find((item) => item.id === selectedId) ?? null,
    [models, selectedId],
  );

  const loadModels = useCallback(async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const [payload, familyPayload] = await Promise.all([
        requestJson<ModelConfigItem[]>(baseUrl, '/api/v1/model-configs'),
        requestJson<string[]>(baseUrl, '/api/v1/models/deployments/families'),
      ]);
      setModels(payload);
      setFamilies(familyPayload);
      setSelectedFamily((previous) => (familyPayload.includes(previous) ? previous : (familyPayload[0] ?? 'hmm_regime_switching')));
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Failed to load model configs.');
    } finally {
      setLoading(false);
    }
  }, [baseUrl]);

  useEffect(() => {
    void loadModels();
  }, [loadModels]);

  const resetToCreate = (): void => {
    setSelectedId(null);
    setIsEditing(false);
    setSelectedFamily('hmm_regime_switching');
    setShared(defaultShared);
    setFormState(defaultFormState);
    setTorchForm(defaultTorch);
    setKalmanForm(defaultKalman);
    setFieldErrors({});
  };

  const startEdit = (item: ModelConfigItem): void => {
    setSelectedId(item.id);
    setIsEditing(true);
    setSelectedFamily(item.model_family);
    setShared({
      name: typeof item.config.name === 'string' ? item.config.name : '',
      version: typeof item.config.version === 'string' ? item.config.version : 'v1',
      taskType: typeof item.config.task_type === 'string' ? item.config.task_type : 'forecasting',
      dataProfile: typeof item.config.data_profile === 'string' ? item.config.data_profile : 'time_series',
    });
    setFormState(formFromConfig(item.config));
    setFieldErrors({});
  };

  const handleSubmit = async (): Promise<void> => {
    const validation = selectedFamily === 'hmm_regime_switching' ? validateForm(formState, shared) : {};
    if (!shared.name.trim()) {
      validation.name = 'Name is required.';
    }
    if (selectedFamily === 'torch_nn_timeseries' && torchForm.mode === 'advanced') {
      try { JSON.parse(torchForm.optionsJson); } catch { validation.optionsJson = 'Advanced options must be valid JSON.'; }
    }
    setFieldErrors(validation);
    if (Object.keys(validation).length > 0) {
      return;
    }

    const path = isEditing && selectedModel ? `/api/v1/model-configs/${encodeURIComponent(selectedModel.id)}` : '/api/v1/model-configs';
    const method = isEditing ? 'PUT' : 'POST';
    const torchPresets: Record<TorchFormState['preset'], Record<string, unknown>> = {
      fast: { architecture: 'gru', hidden_size: 64, num_layers: 1, num_attention_heads: 1, dropout: 0.05, learning_rate: 0.001, batch_size: 128, loss_function: 'mse' },
      balanced: { architecture: 'transformer_encoder', hidden_size: 128, num_layers: 2, num_attention_heads: 8, dropout: 0.1, learning_rate: 0.001, batch_size: 64, loss_function: 'mse' },
      accurate: { architecture: 'transformer_encoder', hidden_size: 256, num_layers: 4, num_attention_heads: 8, dropout: 0.2, learning_rate: 0.0005, batch_size: 32, loss_function: 'huber' },
    };
    const config = selectedFamily === 'hmm_regime_switching'
      ? buildHmmConfig(formState, shared)
      : selectedFamily === 'torch_nn_timeseries'
        ? {
          name: shared.name.trim(),
          version: shared.version.trim(),
          task_type: shared.taskType.trim() || 'forecasting',
          data_type: shared.dataProfile.trim() || 'time_series',
          lookback_window: Number(torchForm.lookbackWindow),
          horizon_steps: Number(torchForm.horizonSteps),
          ...(torchForm.mode === 'simple'
            ? torchPresets[torchForm.preset]
            : { architecture: torchForm.architecture, ...(JSON.parse(torchForm.optionsJson) as Record<string, unknown>) }),
        }
        : {
          name: shared.name.trim(),
          version: shared.version.trim(),
          task_type: shared.taskType.trim() || 'filtering',
          data_type: shared.dataProfile.trim() || 'state_space_timeseries',
          transition_structure: kalmanForm.transitionStructure,
          state_dimension: Number(kalmanForm.stateDimension),
          observation_dimension: Number(kalmanForm.observationDimension),
          process_noise: Number(kalmanForm.processNoise),
          measurement_noise: Number(kalmanForm.measurementNoise),
          initial_covariance_scale: Number(kalmanForm.initialCovarianceScale),
        };
    const payload = isEditing ? { config } : { model_family: selectedFamily, config };

    setError(null);
    try {
      const saved = await requestJson<ModelConfigItem>(baseUrl, path, {
        method,
        body: JSON.stringify(payload),
      });
      setModels((previous) => {
        const existingIndex = previous.findIndex((item) => item.id === saved.id);
        if (existingIndex >= 0) {
          return previous.map((item) => (item.id === saved.id ? saved : item));
        }
        return [saved, ...previous];
      });
      setSelectedId(saved.id);
      setIsEditing(true);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Failed to save model config.');
    }
  };

  return (
    <section>
      <h2>Models</h2>
      <p>HMM regime-switching model configuration registry. Save once, reuse for async training/sweeps/backtests.</p>
      {error ? <p className="muted">Error: {error}</p> : null}
      <div className="card" style={{ marginBottom: '1rem' }}>
        <h3>{isEditing ? 'Edit model config' : 'Create model config'}</h3>
        <FamilyConfigSection>
          <select value={selectedFamily} onChange={(event) => setSelectedFamily(event.target.value)} disabled={isEditing}>
            {[...new Set(families.length > 0 ? families : ['hmm_regime_switching', 'torch_nn_timeseries', 'kalman_filter'])].map((family) => (
              <option key={family} value={family}>{family}</option>
            ))}
          </select>
          <input value={shared.name} onChange={(event) => setShared((prev) => ({ ...prev, name: event.target.value }))} placeholder="Model name" />
          {fieldErrors.name ? <small className="muted">{fieldErrors.name}</small> : null}
          <input value={shared.version} onChange={(event) => setShared((prev) => ({ ...prev, version: event.target.value }))} placeholder="Version" />
          <input value={shared.taskType} onChange={(event) => setShared((prev) => ({ ...prev, taskType: event.target.value }))} placeholder="Task type" />
          <input value={shared.dataProfile} onChange={(event) => setShared((prev) => ({ ...prev, dataProfile: event.target.value }))} placeholder="Data profile" />
          {selectedFamily === 'hmm_regime_switching' ? (
            <>
              <input value={formState.numRegimes} onChange={(event) => setFormState((prev) => ({ ...prev, numRegimes: event.target.value }))} placeholder="Num regimes" />
              {fieldErrors.numRegimes ? <small className="muted">{fieldErrors.numRegimes}</small> : null}
              <input value={formState.lookbackWindow} onChange={(event) => setFormState((prev) => ({ ...prev, lookbackWindow: event.target.value }))} placeholder="Lookback window" />
              {fieldErrors.lookbackWindow ? <small className="muted">{fieldErrors.lookbackWindow}</small> : null}
              <select value={formState.covarianceType} onChange={(event) => setFormState((prev) => ({ ...prev, covarianceType: event.target.value as CovarianceType }))}>
                <option value="diag">diag</option><option value="full">full</option>
              </select>
              <input value={formState.convergenceTol} onChange={(event) => setFormState((prev) => ({ ...prev, convergenceTol: event.target.value }))} placeholder="Convergence tolerance" />
              {fieldErrors.convergenceTol ? <small className="muted">{fieldErrors.convergenceTol}</small> : null}
              <input value={formState.maxIterations} onChange={(event) => setFormState((prev) => ({ ...prev, maxIterations: event.target.value }))} placeholder="Max iterations" />
              {fieldErrors.maxIterations ? <small className="muted">{fieldErrors.maxIterations}</small> : null}
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
                  <option value="fast">fast</option><option value="balanced">balanced</option><option value="accurate">accurate</option>
                </select>
              ) : (
                <>
                  <select value={torchForm.architecture} onChange={(event) => setTorchForm((prev) => ({ ...prev, architecture: event.target.value as TorchFormState['architecture'] }))}>
                    <option value="lstm">lstm</option><option value="gru">gru</option><option value="tcn">tcn</option><option value="transformer_encoder">transformer_encoder</option>
                  </select>
                  <textarea value={torchForm.optionsJson} onChange={(event) => setTorchForm((prev) => ({ ...prev, optionsJson: event.target.value }))} rows={8} />
                  {fieldErrors.optionsJson ? <small className="muted">{fieldErrors.optionsJson}</small> : null}
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
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button type="button" onClick={() => void handleSubmit()}>{isEditing ? 'Update config' : 'Create config'}</button>
            <button type="button" onClick={resetToCreate}>New config</button>
          </div>
        </FamilyConfigSection>
      </div>

      <div className="card jobs-card">
        <table className="jobs-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Family</th>
              <th>Regimes</th>
              <th>Updated</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {!loading && models.length === 0 ? <tr><td colSpan={5}>No model configs yet.</td></tr> : null}
            {models.map((model) => (
              <tr key={model.id}>
                <td>{typeof model.config.name === 'string' ? model.config.name : model.id.slice(0, 8)}</td>
                <td>{model.model_family}</td>
                <td>{String(model.config.n_states ?? model.config.state_dimension ?? 'n/a')}</td>
                <td>{new Date(model.updated_at).toLocaleString()}</td>
                <td>
                  <button type="button" onClick={() => startEdit(model)}>Edit</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
