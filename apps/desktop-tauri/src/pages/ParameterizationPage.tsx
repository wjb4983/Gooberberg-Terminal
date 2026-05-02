import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { requestJson } from '../api/requestJson';
import {
  requestTrainingRunPreflightOrBypass,
  type TrainingRunValidationResponse,
} from '../api/trainingRuns';
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
  submit?: string;
}
interface TrainingTemplate {
  id: string;
  name: string;
  task_type: TaskType;
  subtask_type: SubtaskType;
  validation_profile: string;
  parameter_preset: { name: string; parameters: Record<string, unknown> };
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


interface DatasetPreset {
  id: 'sp500_default' | 'all_stocks_etfs_us' | 'top_liquid_etfs' | 'custom_manual';
  label: string;
  universe_type: DatasetCreateForm['universeType'];
  symbolStrategy: 'saved_universe' | 'manual_symbols';
  savedUniverseId?: string;
  defaultTimeframe: string;
  defaultDateWindow: {
    mode: 'fixed_range' | 'rolling_window';
    startDate: string;
    endDate: string;
    label: string;
  };
  notes?: string;
  estimatedCoverage: string;
  roughSizeCostHint: string;
}

const DATASET_PRESETS: DatasetPreset[] = [
  {
    id: 'sp500_default',
    label: 'S&P 500 (default)',
    universe_type: 'stocks',
    symbolStrategy: 'saved_universe',
    savedUniverseId: 'sp500',
    defaultTimeframe: '1d',
    defaultDateWindow: {
      mode: 'fixed_range',
      startDate: '2024-01-01',
      endDate: '2024-12-31',
      label: 'Calendar year 2024 baseline',
    },
    notes: 'Balanced baseline for broad US large-cap coverage.',
    estimatedCoverage: '~500 tickers',
    roughSizeCostHint: 'Moderate ingestion/runtime cost; good starter benchmark.',
  },
  {
    id: 'all_stocks_etfs_us',
    label: 'All US stocks + ETFs',
    universe_type: 'stocks',
    symbolStrategy: 'saved_universe',
    savedUniverseId: 'all_stocks_etfs_us',
    defaultTimeframe: '1d',
    defaultDateWindow: {
      mode: 'rolling_window',
      startDate: '2024-01-01',
      endDate: '2024-12-31',
      label: 'Broad market window (large footprint)',
    },
    notes: 'Max-coverage preset for discovery and cross-sectional experiments.',
    estimatedCoverage: 'Thousands of symbols',
    roughSizeCostHint: 'High ingestion/runtime cost; expect longer queue and compute time.',
  },
  {
    id: 'top_liquid_etfs',
    label: 'Top liquid ETFs',
    universe_type: 'stocks',
    symbolStrategy: 'saved_universe',
    savedUniverseId: 'top_liquid_etfs',
    defaultTimeframe: '1h',
    defaultDateWindow: {
      mode: 'rolling_window',
      startDate: '2024-07-01',
      endDate: '2024-12-31',
      label: 'Recent liquid ETF window',
    },
    notes: 'Liquidity-focused for lower slippage assumptions and tighter spread behavior.',
    estimatedCoverage: '~25-150 ETFs',
    roughSizeCostHint: 'Lower-to-moderate cost; good for faster iteration loops.',
  },
  {
    id: 'custom_manual',
    label: 'Custom manual symbols',
    universe_type: 'stocks',
    symbolStrategy: 'manual_symbols',
    defaultTimeframe: '1d',
    defaultDateWindow: {
      mode: 'fixed_range',
      startDate: '2024-01-01',
      endDate: '2024-12-31',
      label: 'Manual baseline (editable)',
    },
    notes: 'Uses current manual input flow and preserves backward-compatible behavior.',
    estimatedCoverage: 'User-defined',
    roughSizeCostHint: 'Cost depends on symbol count and timeframe.',
  },
];

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
  const [preflightWarnings, setPreflightWarnings] = useState<string[]>([]);
  const [preflightErrors, setPreflightErrors] = useState<string[]>([]);
  const [preflightPayloadJson, setPreflightPayloadJson] = useState<string>('');
  const [warningConfirmationChecked, setWarningConfirmationChecked] = useState(false);

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
  const [selectedDatasetPresetId, setSelectedDatasetPresetId] = useState<DatasetPreset['id']>('sp500_default');
  const [templates, setTemplates] = useState<TrainingTemplate[]>([]);
  const [templateName, setTemplateName] = useState('My Template');
  const [selectedTemplateId, setSelectedTemplateId] = useState('');

  const load = useCallback(async (): Promise<void> => {
    setPageError(null);
    try {
      const [configsPayload, runsPayload, templatePayload] = await Promise.all([
        requestJson<ModelConfigItem[]>(baseUrl, '/api/v1/model-configs'),
        requestJson<TrainingRunItem[]>(baseUrl, '/api/v1/training-runs'),
        requestJson<TrainingTemplate[]>(baseUrl, '/api/v1/training-runs/templates'),
      ]);
      setModelConfigs(configsPayload);
      setTrainingRuns(runsPayload);
      setTemplates(templatePayload);
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
  const compatibleFamilies = useMemo(
    () => Array.from(new Set(compatibleModelConfigs.map((item) => item.model_family))).sort((a, b) => a.localeCompare(b)),
    [compatibleModelConfigs],
  );
  const [selectedModelFamily, setSelectedModelFamily] = useState('');
  useEffect(() => {
    if (!compatibleFamilies.includes(selectedModelFamily)) {
      setSelectedModelFamily(compatibleFamilies[0] ?? '');
    }
  }, [compatibleFamilies, selectedModelFamily]);
  const familyCompatibleConfigs = useMemo(
    () => compatibleModelConfigs.filter((item) => item.model_family === selectedModelFamily),
    [compatibleModelConfigs, selectedModelFamily],
  );

  useEffect(() => {
    if (!familyCompatibleConfigs.some((item) => item.id === modelConfigId)) {
      setModelConfigId(familyCompatibleConfigs[0]?.id ?? '');
    }
  }, [familyCompatibleConfigs, modelConfigId]);

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
      const { preflight, skippedValidation } = await requestTrainingRunPreflightOrBypass(baseUrl, {
        model_config_id: modelConfigId,
        dataset_id: datasetId.trim(),
        task_type: taskType,
        subtask_type: subtaskType,
        parameters: JSON.parse(parametersJson) as Record<string, unknown>,
      });
      setPreflightWarnings(preflight.warnings);
      setPreflightErrors(preflight.errors);
      setPreflightPayloadJson(JSON.stringify(preflight.normalized_payload, null, 2));
      if (!preflight.valid) {
        setLaunchErrors({ submit: preflight.errors.join(' ') || 'Preflight validation failed.' });
        return;
      }
      if (!skippedValidation && preflight.warnings.length > 0 && !warningConfirmationChecked) {
        setLaunchErrors({ submit: 'Preflight warnings detected. Confirm acknowledgement before launching.' });
        return;
      }
      const created = await requestJson<TrainingRunItem>(baseUrl, '/api/v1/training-runs', {
        method: 'POST',
        body: JSON.stringify(preflight.normalized_payload),
      });
      setLaunchNotice(`Training run queued: ${created.id} (job ${created.job_id}).`);
      setTrainingRuns((previous) => [created, ...previous]);
    } catch (submitError) {
      setPageError(submitError instanceof Error ? submitError.message : 'Failed launching training run.');
    }
  };

  const selectedDatasetPreset = useMemo(
    () => DATASET_PRESETS.find((preset) => preset.id === selectedDatasetPresetId) ?? DATASET_PRESETS[0],
    [selectedDatasetPresetId],
  );

  useEffect(() => {
    setDatasetCreateForm((previous) => ({
      ...previous,
      universeType: selectedDatasetPreset.universe_type,
      savedUniverseId: selectedDatasetPreset.symbolStrategy === 'saved_universe' ? (selectedDatasetPreset.savedUniverseId ?? '') : '',
      finestResolution: selectedDatasetPreset.defaultTimeframe,
      startDate: selectedDatasetPreset.defaultDateWindow.startDate,
      endDate: selectedDatasetPreset.defaultDateWindow.endDate,
      symbolsCsv: selectedDatasetPreset.symbolStrategy === 'manual_symbols' ? previous.symbolsCsv : '',
    }));
  }, [selectedDatasetPreset]);

  const validateDatasetForm = (): DatasetFormErrors => {
    const errors: DatasetFormErrors = {};
    const symbols = datasetCreateForm.symbolsCsv.split(',').map((item) => item.trim()).filter(Boolean);
    const requiresManualSymbols = selectedDatasetPreset.symbolStrategy === 'manual_symbols';
    if (!datasetCreateForm.savedUniverseId.trim() && symbols.length === 0) {
      errors.symbolsCsv = 'Provide symbols list or a saved universe ID.';
      errors.savedUniverseId = requiresManualSymbols ? undefined : 'Provide symbols list or a saved universe ID.';
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

  const createTemplate = async (): Promise<void> => {
    try {
      const parsed = JSON.parse(parametersJson) as Record<string, unknown>;
      await requestJson<TrainingTemplate>(baseUrl, '/api/v1/training-runs/templates', {
        method: 'POST',
        body: JSON.stringify({
          name: templateName,
          task_type: taskType,
          subtask_type: subtaskType,
          validation_profile: 'standard',
          dataset_constraints: {},
          parameter_preset: { name: selectedPreset, parameters: parsed },
        }),
      });
      setLaunchNotice('Template saved.');
      await load();
    } catch (submitError) {
      setPageError(submitError instanceof Error ? submitError.message : 'Failed creating template.');
    }
  };

  const applyTemplate = async (): Promise<void> => {
    if (!selectedTemplateId || !datasetId.trim() || !modelConfigId) return;
    const payload = await requestJson<TrainingRunValidationResponse>(baseUrl, `/api/v1/training-runs/templates/${selectedTemplateId}/apply`, {
      method: 'POST',
      body: JSON.stringify({
        task_type: taskType,
        subtask_type: subtaskType,
        model_config_id: modelConfigId,
        dataset_id: datasetId.trim(),
        parameters: {},
      }),
    });
    setTaskType(payload.normalized_payload.task_type);
    setSubtaskType(payload.normalized_payload.subtask_type);
    setParametersJson(JSON.stringify(payload.normalized_payload.parameters, null, 2));
    setPreflightWarnings(payload.warnings);
    setPreflightErrors(payload.errors);
    setPreflightPayloadJson(JSON.stringify(payload.normalized_payload, null, 2));
  };

  return (
    <section>
      <h2>Parameterization</h2>
      <p className="muted">Guide training launches through a 4-step flow: tasking, dataset, compatible model config, then run submission.</p>
      <p style={{ marginTop: 0 }}><Link to="/model-catalog">Browse model catalog</Link> to compare metadata while selecting compatible configs.</p>
      {pageError ? <p className="error">{pageError}</p> : null}
      <div className="card" style={{ marginBottom: '1rem' }}>
        <h3>Reusable templates</h3>
        <div style={{ display: 'grid', gap: '0.5rem', gridTemplateColumns: '2fr 1fr 1fr' }}>
          <label>
            Template name
            <input value={templateName} onChange={(event) => setTemplateName(event.target.value)} />
          </label>
          <button type="button" onClick={() => void createTemplate()}>Save template</button>
          <label>
            Apply existing
            <select value={selectedTemplateId} onChange={(event) => setSelectedTemplateId(event.target.value)}>
              <option value="">Select template</option>
              {templates.map((template) => <option key={template.id} value={template.id}>{template.name}</option>)}
            </select>
          </label>
        </div>
        <button type="button" onClick={() => void applyTemplate()} disabled={!selectedTemplateId || !datasetId.trim() || !modelConfigId}>Apply + preflight</button>
      </div>

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
              {SUBTASK_TYPES.map((item) => (
                <option key={item} value={item} disabled={item === 'regime_state' && taskType !== 'regime_switching'}>
                  {item}{item === 'regime_state' && taskType !== 'regime_switching' ? ' (requires regime_switching)' : ''}
                </option>
              ))}
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
              Dataset preset
              <select value={selectedDatasetPresetId} onChange={(event) => setSelectedDatasetPresetId(event.target.value as DatasetPreset['id'])}>
                {DATASET_PRESETS.map((preset) => <option key={preset.id} value={preset.id}>{preset.label}</option>)}
              </select>
            </label>
            <p className="muted" style={{ margin: 0 }}>
              {selectedDatasetPreset.notes} Coverage: {selectedDatasetPreset.estimatedCoverage}. {selectedDatasetPreset.roughSizeCostHint} Date window: {selectedDatasetPreset.defaultDateWindow.label}.
            </p>
            <label>
              Universe type
              <select value={datasetCreateForm.universeType} onChange={(event) => setDatasetCreateForm((prev) => ({ ...prev, universeType: event.target.value as DatasetCreateForm['universeType'] }))}>
                <option value="stocks">stocks</option>
                <option value="options">options</option>
              </select>
            </label>
            <label style={selectedDatasetPreset.symbolStrategy === 'manual_symbols' ? undefined : { opacity: 0.6 }}>
              Symbols list (comma separated){selectedDatasetPreset.symbolStrategy === 'manual_symbols' ? '' : ' (manual override only)'}
              <input
                value={datasetCreateForm.symbolsCsv}
                onChange={(event) => setDatasetCreateForm((prev) => ({ ...prev, symbolsCsv: event.target.value }))}
                placeholder="AAPL,MSFT,SPY"
                disabled={selectedDatasetPreset.symbolStrategy !== 'manual_symbols'}
              />
            </label>
            {datasetFormErrors.symbolsCsv ? <small className="error">{datasetFormErrors.symbolsCsv}</small> : null}
            <label style={selectedDatasetPreset.symbolStrategy === 'saved_universe' ? undefined : { opacity: 0.6 }}>
              Saved universe ID
              <input value={datasetCreateForm.savedUniverseId} onChange={(event) => setDatasetCreateForm((prev) => ({ ...prev, savedUniverseId: event.target.value }))} placeholder="optional_universe_id" disabled={selectedDatasetPreset.symbolStrategy !== 'saved_universe'} />
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
        <label>
          Model family
          <select value={selectedModelFamily} onChange={(event) => setSelectedModelFamily(event.target.value)} disabled={!datasetId.trim()}>
            <option value="">Select compatible family</option>
            {compatibleFamilies.map((family) => <option key={family} value={family}>{family}</option>)}
          </select>
        </label>
        <ModelConfigSelect
          value={modelConfigId}
          options={familyCompatibleConfigs}
          onChange={setModelConfigId}
          emptyLabel="Select compatible model config"
          hint={`Filtered by task (${taskType}) and model family (${selectedModelFamily || 'none'}).`}
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
          <label style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginBottom: '0.5rem' }}>
            <input type="checkbox" checked={warningConfirmationChecked} onChange={(event) => setWarningConfirmationChecked(event.target.checked)} />
            Acknowledge preflight warnings (required only when warnings are present)
          </label>
          <button type="button" onClick={() => void launchTrainingRun()} disabled={!taskType || !datasetId.trim() || !subtaskType || !selectedModelFamily || !modelConfigId}>
            Launch training run
          </button>
        </div>
        {launchErrors.submit ? <small className="error">{launchErrors.submit}</small> : null}
        {(preflightWarnings.length > 0 || preflightErrors.length > 0 || preflightPayloadJson) ? (
          <div style={{ marginTop: '0.75rem', border: '1px solid #2b3558', borderRadius: 8, padding: '0.75rem' }}>
            <h4 style={{ marginTop: 0, marginBottom: '0.5rem' }}>Preflight plan</h4>
            {preflightWarnings.length > 0 ? <p className="muted" style={{ margin: '0.25rem 0' }}><strong>Warnings:</strong> {preflightWarnings.join(' · ')}</p> : <p className="muted" style={{ margin: '0.25rem 0' }}>Warnings: none</p>}
            {preflightErrors.length > 0 ? <p className="error" style={{ margin: '0.25rem 0' }}><strong>Errors:</strong> {preflightErrors.join(' · ')}</p> : <p className="muted" style={{ margin: '0.25rem 0' }}>Errors: none</p>}
            {preflightPayloadJson ? (
              <label>
                Normalized launch payload
                <textarea rows={6} readOnly value={preflightPayloadJson} />
              </label>
            ) : null}
          </div>
        ) : null}
        {launchNotice ? <p className="muted" style={{ marginTop: '0.75rem' }}>{launchNotice}</p> : null}
      </div>
    </section>
  );
}
