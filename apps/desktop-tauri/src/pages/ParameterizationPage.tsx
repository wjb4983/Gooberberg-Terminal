import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { requestJson } from '../api/requestJson';
import { SUBTASK_TYPES, TASK_TYPES, type SubtaskType, type TaskType } from '../types/api';
import { ModelConfigSelect } from '../components/ModelConfigSelect';

interface ParameterizationPageProps {
  baseUrl: string;
}

interface ModelConfigItem {
  id: string;
  model_family: string;
  config: Record<string, unknown>;
}

interface TrainingRunItem {
  id: string;
  model_config_id: string;
  dataset_id: string;
  job_id: string;
  status: string;
  created_at: string;
}

interface IngestionItem {
  request_id?: string;
  dataset_id?: string;
  status?: string;
  symbols?: string[];
  timeframe?: string;
  start_date?: string;
  end_date?: string;
  coverage_pct?: number;
}

interface LaunchErrors {
  taskType?: string;
  subtaskType?: string;
  datasetId?: string;
  modelConfigId?: string;
  parametersJson?: string;
}
type TrainingPreset = 'safe' | 'balanced' | 'aggressive';

interface DatasetCreateForm {
  universeType: 'stocks' | 'options';
  symbolsCsv: string;
  savedUniverseId: string;
  startDate: string;
  endDate: string;
  finestResolution: string;
  featurePackEnabled: boolean;
}

interface DatasetFormErrors {
  symbolsCsv?: string;
  savedUniverseId?: string;
  startDate?: string;
  endDate?: string;
  finestResolution?: string;
}

function isModelCompatible(config: ModelConfigItem, taskType: TaskType): boolean {
  const configTaskType = typeof config.config.task_type === 'string' ? config.config.task_type : null;
  if (!configTaskType) {
    return true;
  }
  return configTaskType === taskType;
}

function normalizeDate(value: string): string {
  return value.trim();
}

export function ParameterizationPage({ baseUrl }: ParameterizationPageProps): JSX.Element {
  const [taskType, setTaskType] = useState<TaskType>('time_series_momentum');
  const [subtaskType, setSubtaskType] = useState<SubtaskType>('ranking');
  const [datasetId, setDatasetId] = useState('');
  const [modelConfigId, setModelConfigId] = useState('');
  const [parametersJson, setParametersJson] = useState('{"epochs": 20, "seed": 42}');
  const [selectedPreset, setSelectedPreset] = useState<TrainingPreset>('balanced');
  const [showAdvancedParameters, setShowAdvancedParameters] = useState(false);
  const [changedFields, setChangedFields] = useState<string[]>([]);

  const [modelConfigs, setModelConfigs] = useState<ModelConfigItem[]>([]);
  const [trainingRuns, setTrainingRuns] = useState<TrainingRunItem[]>([]);
  const [ingestions, setIngestions] = useState<IngestionItem[]>([]);

  const [launchErrors, setLaunchErrors] = useState<LaunchErrors>({});
  const [datasetFormErrors, setDatasetFormErrors] = useState<DatasetFormErrors>({});
  const [pageError, setPageError] = useState<string | null>(null);
  const [launchNotice, setLaunchNotice] = useState<string | null>(null);

  const [showCreateDataset, setShowCreateDataset] = useState(false);
  const [datasetCreateForm, setDatasetCreateForm] = useState<DatasetCreateForm>({
    universeType: 'stocks',
    symbolsCsv: 'AAPL,MSFT,SPY',
    savedUniverseId: '',
    startDate: '2024-01-01',
    endDate: '2024-12-31',
    finestResolution: '1d',
    featurePackEnabled: true,
  });
  const [datasetCreateNotice, setDatasetCreateNotice] = useState<string | null>(null);

  const load = useCallback(async (): Promise<void> => {
    setPageError(null);
    try {
      const [configsPayload, runsPayload] = await Promise.all([
        requestJson<ModelConfigItem[]>(baseUrl, '/api/v1/model-configs'),
        requestJson<TrainingRunItem[]>(baseUrl, '/api/v1/training-runs'),
      ]);
      setModelConfigs(configsPayload);
      setTrainingRuns(runsPayload);
      if (!modelConfigId && configsPayload.length > 0) {
        setModelConfigId(configsPayload[0].id);
      }

      try {
        const ingestionPayload = await requestJson<IngestionItem[]>(baseUrl, '/api/v1/market-data/ingestions');
        setIngestions(ingestionPayload);
      } catch {
        setIngestions([]);
      }
    } catch (loadError) {
      setPageError(loadError instanceof Error ? loadError.message : 'Failed loading parameterization dependencies.');
    }
  }, [baseUrl, modelConfigId]);

  useEffect(() => {
    void load();
  }, [load]);

  const existingDatasetRows = useMemo(() => {
    const byId = new Map<string, { id: string; coveragePct: number | null }>();

    trainingRuns.forEach((run) => {
      if (!run.dataset_id || byId.has(run.dataset_id)) {
        return;
      }
      byId.set(run.dataset_id, { id: run.dataset_id, coveragePct: null });
    });

    ingestions.forEach((ingestion) => {
      const candidateId = (typeof ingestion.dataset_id === 'string' && ingestion.dataset_id) || (typeof ingestion.request_id === 'string' ? `ingestion:${ingestion.request_id}` : '');
      if (!candidateId) {
        return;
      }
      const current = byId.get(candidateId);
      const coveragePct = typeof ingestion.coverage_pct === 'number' ? ingestion.coverage_pct : (current?.coveragePct ?? null);
      byId.set(candidateId, { id: candidateId, coveragePct });
    });

    return Array.from(byId.values()).sort((a, b) => a.id.localeCompare(b.id));
  }, [ingestions, trainingRuns]);

  const compatibleModelConfigs = useMemo(
    () => modelConfigs.filter((item) => isModelCompatible(item, taskType)),
    [modelConfigs, taskType],
  );

  useEffect(() => {
    if (!compatibleModelConfigs.some((item) => item.id === modelConfigId)) {
      setModelConfigId(compatibleModelConfigs[0]?.id ?? '');
    }
  }, [compatibleModelConfigs, modelConfigId]);

  const selectedDatasetCoverage = useMemo(
    () => existingDatasetRows.find((item) => item.id === datasetId)?.coveragePct ?? null,
    [datasetId, existingDatasetRows],
  );

  const selectedModelConfig = useMemo(
    () => modelConfigs.find((item) => item.id === modelConfigId) ?? null,
    [modelConfigId, modelConfigs],
  );

  const parameterDefaults = useMemo(() => {
    const defaults = selectedModelConfig?.config.default_parameters;
    return defaults && typeof defaults === 'object' && !Array.isArray(defaults) ? defaults as Record<string, unknown> : {};
  }, [selectedModelConfig]);

  const advancedParameterDefaults = useMemo(() => {
    const advanced = selectedModelConfig?.config.advanced_parameters;
    return advanced && typeof advanced === 'object' && !Array.isArray(advanced) ? advanced as Record<string, unknown> : {};
  }, [selectedModelConfig]);

  const visibleParameterKeys = useMemo(() => Object.keys(parameterDefaults), [parameterDefaults]);
  const advancedParameterKeys = useMemo(() => Object.keys(advancedParameterDefaults), [advancedParameterDefaults]);

  const presetParameters = useMemo((): Record<TrainingPreset, Record<string, unknown>> => ({
    safe: { ...parameterDefaults, risk_level: 'safe', epochs: 10, learning_rate: 0.0005, seed: 42 },
    balanced: { ...parameterDefaults, risk_level: 'balanced', epochs: 20, learning_rate: 0.001, seed: 42 },
    aggressive: { ...parameterDefaults, risk_level: 'aggressive', epochs: 50, learning_rate: 0.003, seed: 42 },
  }), [parameterDefaults]);

  useEffect(() => {
    const nextParameters = { ...presetParameters[selectedPreset], ...advancedParameterDefaults };
    setParametersJson(JSON.stringify(nextParameters, null, 2));
    setChangedFields([]);
  }, [advancedParameterDefaults, presetParameters, selectedPreset]);

  const parsedParameters = useMemo(() => {
    try {
      const parsed = JSON.parse(parametersJson);
      if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
        return parsed as Record<string, unknown>;
      }
      return {};
    } catch {
      return {};
    }
  }, [parametersJson]);

  const updateParameterField = (field: string, value: string): void => {
    const next = { ...parsedParameters, [field]: value };
    setParametersJson(JSON.stringify(next, null, 2));
    setChangedFields((previous) => Array.from(new Set([...previous, field])));
  };

  const validateLaunchForm = (): LaunchErrors => {
    const errors: LaunchErrors = {};
    if (subtaskType === 'regime_state' && taskType !== 'regime_switching') {
      errors.subtaskType = 'Subtask regime_state can only be used with task regime_switching.';
    }
    if (!datasetId.trim()) {
      errors.datasetId = 'Select an existing dataset or create one first.';
    }
    if (!modelConfigId.trim()) {
      errors.modelConfigId = 'Select a compatible model config.';
    }
    try {
      JSON.parse(parametersJson);
    } catch {
      errors.parametersJson = 'Training parameters must be valid JSON.';
    }
    return errors;
  };

  const launchTrainingRun = async (): Promise<void> => {
    const errors = validateLaunchForm();
    setLaunchErrors(errors);
    setLaunchNotice(null);
    if (Object.keys(errors).length > 0) {
      return;
    }

    try {
      const created = await requestJson<TrainingRunItem>(baseUrl, '/api/v1/training-runs', {
        method: 'POST',
        body: JSON.stringify({
          model_config_id: modelConfigId,
          dataset_id: datasetId.trim(),
          task_type: taskType,
          subtask_type: subtaskType,
          parameters: JSON.parse(parametersJson) as Record<string, unknown>,
        }),
      });
      setLaunchNotice(`Training run queued: ${created.id} (job ${created.job_id}).`);
      setTrainingRuns((previous) => [created, ...previous]);
    } catch (submitError) {
      setPageError(submitError instanceof Error ? submitError.message : 'Failed launching training run.');
    }
  };

  const validateDatasetForm = (): DatasetFormErrors => {
    const errors: DatasetFormErrors = {};
    const symbols = datasetCreateForm.symbolsCsv.split(',').map((item) => item.trim()).filter(Boolean);
    if (!datasetCreateForm.savedUniverseId.trim() && symbols.length === 0) {
      errors.symbolsCsv = 'Provide symbols list or a saved universe ID.';
      errors.savedUniverseId = 'Provide symbols list or a saved universe ID.';
    }
    if (!normalizeDate(datasetCreateForm.startDate)) {
      errors.startDate = 'Start date is required.';
    }
    if (!normalizeDate(datasetCreateForm.endDate)) {
      errors.endDate = 'End date is required.';
    }
    if (normalizeDate(datasetCreateForm.startDate) && normalizeDate(datasetCreateForm.endDate) && datasetCreateForm.startDate > datasetCreateForm.endDate) {
      errors.endDate = 'End date must be on or after start date.';
    }
    if (!datasetCreateForm.finestResolution.trim()) {
      errors.finestResolution = 'Finest resolution target is required.';
    }
    return errors;
  };

  const createDataset = async (): Promise<void> => {
    const errors = validateDatasetForm();
    setDatasetFormErrors(errors);
    setDatasetCreateNotice(null);
    if (Object.keys(errors).length > 0) {
      return;
    }

    try {
      const symbols = datasetCreateForm.symbolsCsv.split(',').map((item) => item.trim()).filter(Boolean);
      const payload = await requestJson<IngestionItem>(baseUrl, '/api/v1/market-data/ingestions', {
        method: 'POST',
        body: JSON.stringify({
          source: 'polygon',
          universe_type: datasetCreateForm.universeType,
          symbols,
          universe_id: datasetCreateForm.savedUniverseId.trim() || undefined,
          timeframe: datasetCreateForm.finestResolution.trim(),
          start_date: datasetCreateForm.startDate,
          end_date: datasetCreateForm.endDate,
          feature_pack_enabled: datasetCreateForm.featurePackEnabled,
        }),
      });

      const createdDatasetId = (typeof payload.dataset_id === 'string' && payload.dataset_id)
        || (typeof payload.request_id === 'string' && payload.request_id ? `ingestion:${payload.request_id}` : '');

      if (createdDatasetId) {
        setDatasetId(createdDatasetId);
      }

      setDatasetCreateNotice(`Dataset creation submitted${createdDatasetId ? `: ${createdDatasetId}` : ''}.`);
      setShowCreateDataset(false);
      await load();
    } catch (submitError) {
      setPageError(submitError instanceof Error ? submitError.message : 'Failed creating dataset ingestion request.');
    }
  };

  return (
    <section>
      <h2>Parameterization</h2>
      <p className="muted">Guide training launches through a 4-step flow: tasking, dataset, compatible model config, then run submission.</p>
      <p style={{ marginTop: 0 }}><Link to="/model-catalog">Browse model catalog</Link> to compare metadata while selecting compatible configs.</p>
      {pageError ? <p className="error">{pageError}</p> : null}

      <div className="card" style={{ marginBottom: '1rem' }}>
        <h3>1) Select task + subtask</h3>
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
        {launchErrors.taskType ? <small className="error">{launchErrors.taskType}</small> : null}
        {launchErrors.subtaskType ? <small className="error">{launchErrors.subtaskType}</small> : null}
      </div>

      <div className="card" style={{ marginBottom: '1rem' }}>
        <h3>2) Select dataset</h3>
        <div style={{ display: 'grid', gap: '0.5rem' }}>
          <label>
            Existing datasets
            <select value={datasetId} onChange={(event) => setDatasetId(event.target.value)}>
              <option value="">Select dataset</option>
              {existingDatasetRows.map((dataset) => (
                <option key={dataset.id} value={dataset.id}>{dataset.id}</option>
              ))}
            </select>
          </label>
          <p className="muted" style={{ margin: 0 }}>
            Coverage badge:{' '}
            <strong style={{ color: selectedDatasetCoverage === null ? 'inherit' : selectedDatasetCoverage >= 99 ? '#34d399' : '#fbbf24' }}>
              {selectedDatasetCoverage === null ? 'Unknown' : `${selectedDatasetCoverage.toFixed(1)}%`}
            </strong>
          </p>
          <div>
            <button type="button" onClick={() => setShowCreateDataset((prev) => !prev)}>
              {showCreateDataset ? 'Close create dataset' : 'Create dataset'}
            </button>
          </div>
          {launchErrors.datasetId ? <small className="error">{launchErrors.datasetId}</small> : null}
        </div>

        {showCreateDataset ? (
          <div style={{ marginTop: '0.75rem', border: '1px solid #2b3558', borderRadius: 8, padding: '0.75rem', display: 'grid', gap: '0.5rem' }}>
            <h4 style={{ margin: 0 }}>Create dataset</h4>
            <label>
              Universe type
              <select value={datasetCreateForm.universeType} onChange={(event) => setDatasetCreateForm((prev) => ({ ...prev, universeType: event.target.value as DatasetCreateForm['universeType'] }))}>
                <option value="stocks">stocks</option>
                <option value="options">options</option>
              </select>
            </label>
            <label>
              Symbols list (comma separated)
              <input value={datasetCreateForm.symbolsCsv} onChange={(event) => setDatasetCreateForm((prev) => ({ ...prev, symbolsCsv: event.target.value }))} placeholder="AAPL,MSFT,SPY" />
            </label>
            {datasetFormErrors.symbolsCsv ? <small className="error">{datasetFormErrors.symbolsCsv}</small> : null}
            <label>
              Saved universe ID
              <input value={datasetCreateForm.savedUniverseId} onChange={(event) => setDatasetCreateForm((prev) => ({ ...prev, savedUniverseId: event.target.value }))} placeholder="optional_universe_id" />
            </label>
            {datasetFormErrors.savedUniverseId ? <small className="error">{datasetFormErrors.savedUniverseId}</small> : null}
            <div style={{ display: 'grid', gap: '0.5rem', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))' }}>
              <label>
                Start date
                <input type="date" value={datasetCreateForm.startDate} onChange={(event) => setDatasetCreateForm((prev) => ({ ...prev, startDate: event.target.value }))} />
              </label>
              <label>
                End date
                <input type="date" value={datasetCreateForm.endDate} onChange={(event) => setDatasetCreateForm((prev) => ({ ...prev, endDate: event.target.value }))} />
              </label>
            </div>
            {datasetFormErrors.startDate ? <small className="error">{datasetFormErrors.startDate}</small> : null}
            {datasetFormErrors.endDate ? <small className="error">{datasetFormErrors.endDate}</small> : null}
            <label>
              Finest resolution target
              <input value={datasetCreateForm.finestResolution} onChange={(event) => setDatasetCreateForm((prev) => ({ ...prev, finestResolution: event.target.value }))} placeholder="1m, 5m, 1h, 1d" />
            </label>
            {datasetFormErrors.finestResolution ? <small className="error">{datasetFormErrors.finestResolution}</small> : null}
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <input type="checkbox" checked={datasetCreateForm.featurePackEnabled} onChange={(event) => setDatasetCreateForm((prev) => ({ ...prev, featurePackEnabled: event.target.checked }))} />
              Feature pack enabled
            </label>
            <button type="button" onClick={() => void createDataset()}>Submit dataset creation</button>
          </div>
        ) : null}
        {datasetCreateNotice ? <p className="muted" style={{ marginTop: '0.75rem' }}>{datasetCreateNotice}</p> : null}
      </div>

      <div className="card" style={{ marginBottom: '1rem' }}>
        <h3>3) Select model config</h3>
        <ModelConfigSelect
          value={modelConfigId}
          options={compatibleModelConfigs}
          onChange={setModelConfigId}
          emptyLabel="Select compatible model config"
          hint={`Filtered by task compatibility (${taskType}).`}
        />
        {launchErrors.modelConfigId ? <small className="error">{launchErrors.modelConfigId}</small> : null}
      </div>

      <div className="card" style={{ marginBottom: '1rem' }}>
        <h3>4) Launch training run</h3>
        <div style={{ display: 'grid', gap: '0.5rem', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', marginBottom: '0.75rem' }}>
          {(['safe', 'balanced', 'aggressive'] as TrainingPreset[]).map((preset) => (
            <button key={preset} type="button" onClick={() => setSelectedPreset(preset)} disabled={selectedPreset === preset}>
              {preset}
            </button>
          ))}
        </div>
        {visibleParameterKeys.length > 0 ? (
          <div style={{ display: 'grid', gap: '0.5rem', marginBottom: '0.75rem' }}>
            {visibleParameterKeys.map((field) => (
              <label key={field}>
                {field}
                <input
                  value={String(parsedParameters[field] ?? '')}
                  onChange={(event) => updateParameterField(field, event.target.value)}
                  style={changedFields.includes(field) ? { borderColor: '#fbbf24', boxShadow: '0 0 0 1px #fbbf24' } : undefined}
                />
              </label>
            ))}
          </div>
        ) : null}
        {advancedParameterKeys.length > 0 ? (
          <details open={showAdvancedParameters} onToggle={(event) => setShowAdvancedParameters(event.currentTarget.open)} style={{ marginBottom: '0.75rem' }}>
            <summary>Advanced parameters</summary>
            <div style={{ display: 'grid', gap: '0.5rem', marginTop: '0.5rem' }}>
              {advancedParameterKeys.map((field) => (
                <label key={field}>
                  {field}
                  <input
                    value={String(parsedParameters[field] ?? '')}
                    onChange={(event) => updateParameterField(field, event.target.value)}
                    style={changedFields.includes(field) ? { borderColor: '#fbbf24', boxShadow: '0 0 0 1px #fbbf24' } : undefined}
                  />
                </label>
              ))}
            </div>
          </details>
        ) : null}
        <label>
          Parameters JSON
          <textarea rows={5} value={parametersJson} onChange={(event) => setParametersJson(event.target.value)} />
        </label>
        {launchErrors.parametersJson ? <small className="error">{launchErrors.parametersJson}</small> : null}
        <div style={{ marginTop: '0.75rem' }}>
          <button type="button" onClick={() => void launchTrainingRun()}>Launch training run</button>
        </div>
        {launchNotice ? <p className="muted" style={{ marginTop: '0.75rem' }}>{launchNotice}</p> : null}
      </div>
    </section>
  );
}
