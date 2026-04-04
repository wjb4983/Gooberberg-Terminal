import { useCallback, useEffect, useMemo, useState } from 'react';

interface ModelsPageProps {
  baseUrl: string;
}

type CovarianceType = 'full' | 'diag';

interface HmmConfigFormState {
  name: string;
  numRegimes: string;
  lookbackWindow: string;
  covarianceType: CovarianceType;
  transitionRegularization: string;
  featureColumns: string;
  targetColumn: string;
}

interface ModelConfigItem {
  id: string;
  model_family: string;
  config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

interface HmmConfigValidationErrors {
  name?: string;
  numRegimes?: string;
  lookbackWindow?: string;
  transitionRegularization?: string;
  featureColumns?: string;
  targetColumn?: string;
}

const defaultFormState: HmmConfigFormState = {
  name: '',
  numRegimes: '2',
  lookbackWindow: '252',
  covarianceType: 'diag',
  transitionRegularization: '0.01',
  featureColumns: 'returns_1d,returns_5d,volatility_20d',
  targetColumn: 'returns_1d',
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

function buildHmmConfig(state: HmmConfigFormState): Record<string, unknown> {
  return {
    name: state.name.trim(),
    num_regimes: Number(state.numRegimes),
    lookback_window: Number(state.lookbackWindow),
    covariance_type: state.covarianceType,
    transition_regularization: Number(state.transitionRegularization),
    feature_columns: state.featureColumns.split(',').map((item) => item.trim()).filter(Boolean),
    target_column: state.targetColumn.trim(),
  };
}

function validateForm(state: HmmConfigFormState): HmmConfigValidationErrors {
  const errors: HmmConfigValidationErrors = {};
  if (!state.name.trim()) {
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
  const regularization = Number(state.transitionRegularization);
  if (!Number.isFinite(regularization) || regularization < 0 || regularization > 1) {
    errors.transitionRegularization = 'Transition regularization must be between 0 and 1.';
  }
  if (state.featureColumns.split(',').map((item) => item.trim()).filter(Boolean).length === 0) {
    errors.featureColumns = 'Provide at least one feature column.';
  }
  if (!state.targetColumn.trim()) {
    errors.targetColumn = 'Target column is required.';
  }
  return errors;
}

function formFromConfig(config: Record<string, unknown>): HmmConfigFormState {
  const featureColumns = Array.isArray(config.feature_columns)
    ? config.feature_columns.map((item) => String(item)).join(',')
    : '';

  return {
    name: typeof config.name === 'string' ? config.name : '',
    numRegimes: String(config.num_regimes ?? '2'),
    lookbackWindow: String(config.lookback_window ?? '252'),
    covarianceType: config.covariance_type === 'full' ? 'full' : 'diag',
    transitionRegularization: String(config.transition_regularization ?? '0.01'),
    featureColumns,
    targetColumn: typeof config.target_column === 'string' ? config.target_column : '',
  };
}

export function ModelsPage({ baseUrl }: ModelsPageProps): JSX.Element {
  const [models, setModels] = useState<ModelConfigItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [formState, setFormState] = useState<HmmConfigFormState>(defaultFormState);
  const [fieldErrors, setFieldErrors] = useState<HmmConfigValidationErrors>({});

  const selectedModel = useMemo(
    () => models.find((item) => item.id === selectedId) ?? null,
    [models, selectedId],
  );

  const loadModels = useCallback(async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const payload = await requestJson<ModelConfigItem[]>(baseUrl, '/api/v1/model-configs');
      setModels(payload);
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
    setFormState(defaultFormState);
    setFieldErrors({});
  };

  const startEdit = (item: ModelConfigItem): void => {
    setSelectedId(item.id);
    setIsEditing(true);
    setFormState(formFromConfig(item.config));
    setFieldErrors({});
  };

  const handleSubmit = async (): Promise<void> => {
    const validation = validateForm(formState);
    setFieldErrors(validation);
    if (Object.keys(validation).length > 0) {
      return;
    }

    const path = isEditing && selectedModel ? `/api/v1/model-configs/${encodeURIComponent(selectedModel.id)}` : '/api/v1/model-configs';
    const method = isEditing ? 'PUT' : 'POST';
    const payload = isEditing
      ? { config: buildHmmConfig(formState) }
      : { model_family: 'hmm_regime_switching', config: buildHmmConfig(formState) };

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
        <div style={{ display: 'grid', gap: '0.5rem' }}>
          <input value={formState.name} onChange={(event) => setFormState((prev) => ({ ...prev, name: event.target.value }))} placeholder="Config name" />
          {fieldErrors.name ? <small className="muted">{fieldErrors.name}</small> : null}
          <input value={formState.numRegimes} onChange={(event) => setFormState((prev) => ({ ...prev, numRegimes: event.target.value }))} placeholder="Num regimes" />
          {fieldErrors.numRegimes ? <small className="muted">{fieldErrors.numRegimes}</small> : null}
          <input value={formState.lookbackWindow} onChange={(event) => setFormState((prev) => ({ ...prev, lookbackWindow: event.target.value }))} placeholder="Lookback window" />
          {fieldErrors.lookbackWindow ? <small className="muted">{fieldErrors.lookbackWindow}</small> : null}
          <select value={formState.covarianceType} onChange={(event) => setFormState((prev) => ({ ...prev, covarianceType: event.target.value as CovarianceType }))}>
            <option value="diag">diag</option>
            <option value="full">full</option>
          </select>
          <input
            value={formState.transitionRegularization}
            onChange={(event) => setFormState((prev) => ({ ...prev, transitionRegularization: event.target.value }))}
            placeholder="Transition regularization"
          />
          {fieldErrors.transitionRegularization ? <small className="muted">{fieldErrors.transitionRegularization}</small> : null}
          <input value={formState.featureColumns} onChange={(event) => setFormState((prev) => ({ ...prev, featureColumns: event.target.value }))} placeholder="Feature columns (comma separated)" />
          {fieldErrors.featureColumns ? <small className="muted">{fieldErrors.featureColumns}</small> : null}
          <input value={formState.targetColumn} onChange={(event) => setFormState((prev) => ({ ...prev, targetColumn: event.target.value }))} placeholder="Target column" />
          {fieldErrors.targetColumn ? <small className="muted">{fieldErrors.targetColumn}</small> : null}
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button type="button" onClick={() => void handleSubmit()}>{isEditing ? 'Update config' : 'Create config'}</button>
            <button type="button" onClick={resetToCreate}>New config</button>
          </div>
        </div>
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
                <td>{String(model.config.num_regimes ?? 'n/a')}</td>
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
