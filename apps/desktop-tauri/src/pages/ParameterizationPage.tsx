import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import type { DatasetPreset } from '../features/datasets/forms';
import { DATASET_PRESETS, QUICK_START_TEMPLATES, type QuickStartTemplate } from '../features/datasets/catalog';
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
  universe_type?: string;
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
type IngestionJobState = 'queued' | 'running' | 'succeeded' | 'failed';

interface IngestionJobRecord {
  requestId: string;
  datasetId: string | null;
  status: IngestionJobState;
  startedAt: string;
  lastUpdateAt: string;
  errorMessage: string | null;
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
  const [pageError, setPageError] = useState<string | null>(null);
  const [launchNotice, setLaunchNotice] = useState<string | null>(null);
  const [preflightWarnings, setPreflightWarnings] = useState<string[]>([]);
  const [preflightErrors, setPreflightErrors] = useState<string[]>([]);
  const [preflightPayloadJson, setPreflightPayloadJson] = useState<string>('');
  const [warningConfirmationChecked, setWarningConfirmationChecked] = useState(false);

  const [selectedDatasetPresetId, setSelectedDatasetPresetId] = useState<DatasetPreset['id']>('sp500_default');
  const [templates, setTemplates] = useState<TrainingTemplate[]>([]);
  const [templateName, setTemplateName] = useState('My Template');
  const [selectedTemplateId, setSelectedTemplateId] = useState('');
  const [selectedQuickStartId, setSelectedQuickStartId] = useState('');

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

  const selectedDatasetMetadata = useMemo(() => {
    if (!datasetId) return null;
    const matchingIngestion = ingestions.find((ingestion) => {
      const candidateId = (typeof ingestion.dataset_id === 'string' && ingestion.dataset_id)
        || (typeof ingestion.request_id === 'string' && ingestion.request_id ? `ingestion:${ingestion.request_id}` : '');
      return candidateId === datasetId;
    });

    if (!matchingIngestion) {
      return { coverage: selectedDatasetCoverage, universeType: null, timeframe: null, dateWindow: null };
    }

    const startDate = matchingIngestion.start_date?.trim() ?? '';
    const endDate = matchingIngestion.end_date?.trim() ?? '';
    const dateWindow = startDate && endDate ? `${startDate} → ${endDate}` : null;

    return {
      coverage: typeof matchingIngestion.coverage_pct === 'number' ? matchingIngestion.coverage_pct : selectedDatasetCoverage,
      universeType: matchingIngestion.universe_type ?? null,
      timeframe: matchingIngestion.timeframe ?? null,
      dateWindow,
    };
  }, [datasetId, ingestions, selectedDatasetCoverage]);

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

  const selectedQuickStartTemplate = useMemo(
    () => QUICK_START_TEMPLATES.find((template) => template.id === selectedQuickStartId) ?? null,
    [selectedQuickStartId],
  );

  const applyQuickStartTemplate = useCallback((template: QuickStartTemplate): void => {
    setSelectedDatasetPresetId(template.datasetPresetId);
    setSelectedPreset(template.trainingPreset);
    setLaunchNotice(`Quick start applied: ${template.label}. You can adjust any advanced settings before launch.`);
  }, []);

  return (
    <section>
      <h2>Parameterization</h2>
      <p className="muted">Guide training launches through a 4-step flow: tasking, dataset, compatible model config, then run submission.</p>
      <p style={{ marginTop: 0 }}><Link to="/model-catalog">Browse model catalog</Link> to compare metadata while selecting compatible configs.</p>
      {pageError ? <p className="error">{pageError}</p> : null}
      <div className="card" style={{ marginBottom: '1rem' }}>
        <h3>Quick start</h3>
        <p className="muted" style={{ marginTop: 0 }}>Apply a recommended template, then fine-tune any settings below.</p>
        <div style={{ display: 'grid', gap: '0.5rem', gridTemplateColumns: '2fr 1fr' }}>
          <label>
            Recommended templates
            <select value={selectedQuickStartId} onChange={(event) => setSelectedQuickStartId(event.target.value)}>
              <option value="">Select quick start template</option>
              {QUICK_START_TEMPLATES.map((template) => (
                <option key={template.id} value={template.id}>{template.label}</option>
              ))}
            </select>
          </label>
          <button type="button" onClick={() => selectedQuickStartTemplate && applyQuickStartTemplate(selectedQuickStartTemplate)} disabled={!selectedQuickStartTemplate}>
            Apply quick start
          </button>
        </div>
        {selectedQuickStartTemplate ? <p className="muted" style={{ marginBottom: 0 }}>{selectedQuickStartTemplate.description}</p> : null}
      </div>
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
          <p className="muted" style={{ margin: 0 }}>
            Need a new dataset configuration? Use the dedicated creation flow for universe, timeframe, and ingestion setup.
          </p>
          <Link to="/datasets/create">
            <button type="button">Create new dataset in full page</button>
          </Link>
          {selectedDatasetMetadata ? (
            <p className="muted" style={{ margin: 0 }}>
              Summary: coverage {selectedDatasetMetadata.coverage === null ? 'Unknown' : `${selectedDatasetMetadata.coverage.toFixed(1)}%`}
              {selectedDatasetMetadata.universeType ? ` · universe ${selectedDatasetMetadata.universeType}` : ''}
              {selectedDatasetMetadata.timeframe ? ` · timeframe ${selectedDatasetMetadata.timeframe}` : ''}
              {selectedDatasetMetadata.dateWindow ? ` · ${selectedDatasetMetadata.dateWindow}` : ''}
            </p>
          ) : null}
          {launchErrors.datasetId ? <small className="error">{launchErrors.datasetId}</small> : null}
        </div>
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
