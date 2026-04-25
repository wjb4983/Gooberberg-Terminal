import { useCallback, useEffect, useMemo, useState } from 'react';
import { SUBTASK_TYPES, TASK_TYPES, type SubtaskType, type TaskType } from '../types/api';

interface ParameterizationPageProps {
  baseUrl: string;
}

interface ParameterSetItem {
  id: string;
  model_config_id: string;
  name: string;
  parameters: Record<string, unknown>;
  version_tag: string;
  parent_set_id: string | null;
  provenance_metadata: Record<string, unknown>;
  created_at: string;
}

interface ParameterSweepItem {
  id: string;
  model_config_id: string;
  parameter_set_id: string | null;
  task_type: TaskType;
  subtask_type: SubtaskType;
  objective: string;
  search_space: Record<string, unknown>;
  provenance_snapshot: Record<string, unknown>;
  job_id: string;
  status: string;
  created_at: string;
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
  if (!response.ok) {
    throw new Error(`Request failed (${response.status}) for ${path}`);
  }
  return (await response.json()) as T;
}

function flattenRecord(input: Record<string, unknown>, prefix = ''): Record<string, string> {
  const output: Record<string, string> = {};
  Object.entries(input).forEach(([key, value]) => {
    const nextKey = prefix ? `${prefix}.${key}` : key;
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      Object.assign(output, flattenRecord(value as Record<string, unknown>, nextKey));
      return;
    }
    output[nextKey] = JSON.stringify(value);
  });
  return output;
}

export function ParameterizationPage({ baseUrl }: ParameterizationPageProps): JSX.Element {
  const [templates, setTemplates] = useState<ParameterSetItem[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>('');
  const [history, setHistory] = useState<ParameterSetItem[]>([]);
  const [objective, setObjective] = useState('maximize_sharpe');
  const [taskType, setTaskType] = useState<TaskType>('time_series_momentum');
  const [subtaskType, setSubtaskType] = useState<SubtaskType>('ranking');
  const [searchSpaceJson, setSearchSpaceJson] = useState('{"learning_rate": [0.0005, 0.001, 0.01], "hidden_size": [32, 64]}');
  const [batchCount, setBatchCount] = useState(3);
  const [batchTag, setBatchTag] = useState('sweep-batch');
  const [createdSweeps, setCreatedSweeps] = useState<ParameterSweepItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [tableScrollTop, setTableScrollTop] = useState(0);

  const rowHeight = 42;
  const tableHeight = 320;

  const selectedTemplate = useMemo(
    () => templates.find((template) => template.id === selectedTemplateId) ?? null,
    [templates, selectedTemplateId],
  );
  const parentTemplate = useMemo(
    () => templates.find((template) => template.id === selectedTemplate?.parent_set_id) ?? null,
    [templates, selectedTemplate],
  );

  const visibleWindow = useMemo(() => {
    const startIndex = Math.max(0, Math.floor(tableScrollTop / rowHeight) - 4);
    const visibleCount = Math.ceil(tableHeight / rowHeight) + 8;
    return {
      startIndex,
      endIndex: Math.min(templates.length, startIndex + visibleCount),
    };
  }, [tableScrollTop, templates.length]);

  const refreshTemplates = useCallback(async (): Promise<void> => {
    const payload = await requestJson<ParameterSetItem[]>(baseUrl, '/api/v1/parameter-sets');
    setTemplates(payload);
    if (!selectedTemplateId && payload.length > 0) {
      setSelectedTemplateId(payload[0].id);
    }
  }, [baseUrl, selectedTemplateId]);

  useEffect(() => {
    void refreshTemplates().catch((loadError: unknown) => {
      setError(loadError instanceof Error ? loadError.message : 'Failed loading template library.');
    });
  }, [refreshTemplates]);

  useEffect(() => {
    if (!selectedTemplateId) {
      setHistory([]);
      return;
    }
    void requestJson<ParameterSetItem[]>(baseUrl, `/api/v1/parameter-sets/${encodeURIComponent(selectedTemplateId)}/versions`)
      .then(setHistory)
      .catch(() => setHistory([]));
  }, [baseUrl, selectedTemplateId]);

  const cloneSelected = async (): Promise<void> => {
    if (!selectedTemplateId || !selectedTemplate) {
      setError('Select a template before cloning.');
      return;
    }
    try {
      setError(null);
      await requestJson<ParameterSetItem>(baseUrl, `/api/v1/parameter-sets/${encodeURIComponent(selectedTemplateId)}/clone`, {
        method: 'POST',
        body: JSON.stringify({
          name: `${selectedTemplate.name} clone`,
          version_tag: `${selectedTemplate.version_tag}.clone`,
        }),
      });
      await refreshTemplates();
    } catch (cloneError) {
      setError(cloneError instanceof Error ? cloneError.message : 'Failed cloning template.');
    }
  };

  const submitSweepBatch = async (): Promise<void> => {
    if (!selectedTemplate) {
      setError('Template selection is required before launching sweeps.');
      return;
    }
    let parsedSearchSpace: Record<string, unknown>;
    try {
      parsedSearchSpace = JSON.parse(searchSpaceJson) as Record<string, unknown>;
    } catch {
      setError('Search space JSON is invalid.');
      return;
    }

    try {
      setError(null);
      if (subtaskType === 'regime_state' && taskType !== 'regime_switching') {
        setError('Subtask regime_state is only valid with task type regime_switching.');
        return;
      }
      const launchJobs = Array.from({ length: batchCount }, (_, index) =>
        requestJson<ParameterSweepItem>(baseUrl, '/api/v1/parameter-sweeps', {
          method: 'POST',
          body: JSON.stringify({
            model_config_id: selectedTemplate.model_config_id,
            parameter_set_id: selectedTemplate.id,
            task_type: taskType,
            subtask_type: subtaskType,
            objective,
            search_space: { ...parsedSearchSpace, batch_index: index, batch_tag: batchTag },
            provenance_snapshot: {
              ...selectedTemplate.provenance_metadata,
              parameter_set_version_tag: selectedTemplate.version_tag,
              immutable_template_id: selectedTemplate.id,
            },
          }),
        }),
      );
      const created = await Promise.all(launchJobs);
      setCreatedSweeps((previous) => [...created, ...previous].slice(0, 20));
    } catch (batchError) {
      setError(batchError instanceof Error ? batchError.message : 'Failed submitting sweep batch.');
    }
  };

  const leftFlat = flattenRecord(parentTemplate?.parameters ?? {});
  const rightFlat = flattenRecord(selectedTemplate?.parameters ?? {});
  const diffKeys = Array.from(new Set([...Object.keys(leftFlat), ...Object.keys(rightFlat)])).sort();

  return (
    <section>
      <h2>Parameterization</h2>
      <p className="muted">Manage reusable parameter templates, review version lineage, and launch provenance-linked sweep batches.</p>
      {error ? <p className="error">{error}</p> : null}

      <div className="card" style={{ maxWidth: '100%', marginBottom: '1rem' }}>
        <h3>Template library (virtualized)</h3>
        <div style={{ border: '1px solid #2b3558', borderRadius: 6, overflow: 'auto', height: tableHeight }} onScroll={(event) => setTableScrollTop((event.target as HTMLDivElement).scrollTop)}>
          <div style={{ position: 'relative', height: templates.length * rowHeight }}>
            {templates.slice(visibleWindow.startIndex, visibleWindow.endIndex).map((template, visibleIndex) => {
              const realIndex = visibleWindow.startIndex + visibleIndex;
              return (
                <button
                  key={template.id}
                  type="button"
                  onClick={() => setSelectedTemplateId(template.id)}
                  style={{
                    position: 'absolute',
                    top: realIndex * rowHeight,
                    height: rowHeight - 2,
                    left: 0,
                    right: 0,
                    border: 0,
                    borderBottom: '1px solid #2b3558',
                    background: selectedTemplateId === template.id ? 'rgba(127,127,127,0.2)' : 'transparent',
                    color: 'inherit',
                    textAlign: 'left',
                    display: 'grid',
                    gridTemplateColumns: '1.2fr 1fr 1fr',
                    padding: '0 0.75rem',
                    cursor: 'pointer',
                  }}
                >
                  <span>{template.name}</span>
                  <span>{template.version_tag}</span>
                  <span>{new Date(template.created_at).toLocaleDateString()}</span>
                </button>
              );
            })}
          </div>
        </div>
        <div style={{ marginTop: '0.75rem', display: 'flex', gap: '0.5rem' }}>
          <button type="button" onClick={() => void cloneSelected()} disabled={!selectedTemplateId}>Clone selected</button>
        </div>
      </div>

      <div className="card" style={{ maxWidth: '100%', marginBottom: '1rem' }}>
        <h3>Side-by-side JSON diff</h3>
        <p className="muted">Comparing selected template against parent version.</p>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
          <div>
            <h4>Parent</h4>
            <pre>{JSON.stringify(parentTemplate?.parameters ?? {}, null, 2)}</pre>
          </div>
          <div>
            <h4>Selected</h4>
            <pre>{JSON.stringify(selectedTemplate?.parameters ?? {}, null, 2)}</pre>
          </div>
        </div>
        <table className="jobs-table" style={{ marginTop: '0.5rem' }}>
          <thead><tr><th>Path</th><th>Parent</th><th>Selected</th></tr></thead>
          <tbody>
            {diffKeys.length === 0 ? <tr><td colSpan={3}>No comparable keys.</td></tr> : null}
            {diffKeys.map((key) => (
              <tr key={key} style={{ background: leftFlat[key] === rightFlat[key] ? 'transparent' : 'rgba(245, 158, 11, 0.12)' }}>
                <td>{key}</td>
                <td>{leftFlat[key] ?? '—'}</td>
                <td>{rightFlat[key] ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="muted">Version history: {history.map((item) => item.version_tag).join(' → ') || 'No lineage selected.'}</p>
      </div>

      <div className="card" style={{ maxWidth: '100%' }}>
        <h3>Batch sweep submit</h3>
        <div style={{ display: 'grid', gap: '0.5rem', maxWidth: 720 }}>
          <div style={{ display: 'grid', gap: '0.5rem', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))' }}>
            <select value={taskType} onChange={(event) => setTaskType(event.target.value as TaskType)}>
              {TASK_TYPES.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
            <select value={subtaskType} onChange={(event) => setSubtaskType(event.target.value as SubtaskType)}>
              {SUBTASK_TYPES.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          </div>
          <input value={objective} onChange={(event) => setObjective(event.target.value)} placeholder="Objective" />
          <textarea rows={5} value={searchSpaceJson} onChange={(event) => setSearchSpaceJson(event.target.value)} />
          <input type="number" min={1} max={25} value={batchCount} onChange={(event) => setBatchCount(Number(event.target.value) || 1)} />
          <input value={batchTag} onChange={(event) => setBatchTag(event.target.value)} placeholder="Batch tag" />
          <button type="button" onClick={() => void submitSweepBatch()} disabled={!selectedTemplate}>Submit sweep batch</button>
        </div>
        <table className="jobs-table" style={{ marginTop: '1rem' }}>
          <thead><tr><th>Job</th><th>Template</th><th>Status</th><th>Provenance hash</th></tr></thead>
          <tbody>
            {createdSweeps.length === 0 ? <tr><td colSpan={4}>No sweeps launched in this session.</td></tr> : null}
            {createdSweeps.map((item) => (
              <tr key={item.id}>
                <td>{item.job_id.slice(0, 8)}</td>
                <td>{item.parameter_set_id?.slice(0, 8) ?? '—'}</td>
                <td>{item.status}</td>
                <td>{String(item.provenance_snapshot.config_hash ?? 'n/a')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
