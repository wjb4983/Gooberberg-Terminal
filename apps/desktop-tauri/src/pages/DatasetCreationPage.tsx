import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { fetchUniverseSymbols } from '../api/universes';
import { requestJson } from '../api/requestJson';
import { DATASET_PRESETS, type DatasetCreateForm, type DatasetFormErrors, type DatasetPreset } from '../features/datasets/forms';

interface DatasetCreationPageProps { baseUrl: string; }
interface IngestionItem { request_id?: string; dataset_id?: string; status?: string; }

function resolveManualSymbols(args: { manualSymbolsCsv: string; symbolStrategy: DatasetPreset['symbolStrategy']; }): string[] {
  const manualSymbols = args.manualSymbolsCsv.split(',').map((item) => item.trim().toUpperCase()).filter(Boolean);
  if (manualSymbols.length > 0) return Array.from(new Set(manualSymbols));
  return [];
}

export function DatasetCreationPage({ baseUrl }: DatasetCreationPageProps): JSX.Element {
  const [selectedDatasetPresetId, setSelectedDatasetPresetId] = useState<DatasetPreset['id']>('sp500_default');
  const [datasetCreateForm, setDatasetCreateForm] = useState<DatasetCreateForm>({ universeType: 'stocks', symbolsCsv: 'AAPL,MSFT,SPY', savedUniverseId: '', startDate: '2024-01-01', endDate: '2024-12-31', finestResolution: '1d', featurePackEnabled: true });
  const [datasetFormErrors, setDatasetFormErrors] = useState<DatasetFormErrors>({});
  const [notice, setNotice] = useState<string | null>(null);

  const selectedDatasetPreset = useMemo(() => DATASET_PRESETS.find((preset) => preset.id === selectedDatasetPresetId) ?? DATASET_PRESETS[0], [selectedDatasetPresetId]);

  const validateDatasetForm = async (): Promise<{ errors: DatasetFormErrors; symbols: string[] }> => {
    const errors: DatasetFormErrors = {};
    let symbols = resolveManualSymbols({ manualSymbolsCsv: datasetCreateForm.symbolsCsv, symbolStrategy: selectedDatasetPreset.symbolStrategy });
    if (selectedDatasetPreset.symbolStrategy === 'manual_symbols' && symbols.length === 0) errors.symbolsCsv = 'Provide a symbols list.';
    if (selectedDatasetPreset.symbolStrategy === 'saved_universe') {
      const normalizedUniverseId = datasetCreateForm.savedUniverseId.trim();
      if (!normalizedUniverseId) {
        errors.savedUniverseId = 'Saved universe ID is required.';
      } else {
        try {
          symbols = await fetchUniverseSymbols(baseUrl, normalizedUniverseId);
          if (symbols.length === 0) {
            errors.savedUniverseId = `Saved universe "${normalizedUniverseId}" returned no members from backend.`;
          }
        } catch (error) {
          const detail = error instanceof Error ? error.message : 'Unknown backend error.';
          errors.savedUniverseId = `Failed to load saved universe "${normalizedUniverseId}" from backend: ${detail}`;
        }
      }
    }
    if (!datasetCreateForm.startDate) errors.startDate = 'Start date is required.';
    if (!datasetCreateForm.endDate) errors.endDate = 'End date is required.';
    if (datasetCreateForm.startDate && datasetCreateForm.endDate && datasetCreateForm.startDate > datasetCreateForm.endDate) errors.endDate = 'End date must be on or after start date.';
    if (!datasetCreateForm.finestResolution.trim()) errors.finestResolution = 'Finest resolution target is required.';
    return { errors, symbols };
  };

  const createDataset = async (): Promise<void> => {
    const { errors, symbols } = await validateDatasetForm();
    setDatasetFormErrors(errors);
    if (Object.keys(errors).length > 0) return;
    const payload = await requestJson<IngestionItem>(baseUrl, '/api/v1/market-data/ingestions', { method: 'POST', body: JSON.stringify({ provider: 'massive', asset_class: datasetCreateForm.universeType, universe_members: symbols, symbols, resolutions: [datasetCreateForm.finestResolution.trim()], timeframe: datasetCreateForm.finestResolution.trim(), start_date: datasetCreateForm.startDate, end_date: datasetCreateForm.endDate, feature_recipe_version: datasetCreateForm.featurePackEnabled ? 'v2' : 'v1', label_recipe_version: 'v1', alias: datasetCreateForm.savedUniverseId.trim() || undefined }) });
    const id = payload.dataset_id || (payload.request_id ? `ingestion:${payload.request_id}` : 'submitted');
    setNotice(`Dataset creation submitted: ${id}`);
  };

  return (
    <section>
      <h2>Dataset creation</h2>
      <p className="muted">Configure universe, date window, and resolution before launching training.</p>
      <p><Link to="/parameterization">Back to parameterization</Link></p>
      <div className="card" style={{ display: 'grid', gap: '0.5rem' }}>
        <label>Dataset preset
          <select value={selectedDatasetPresetId} onChange={(event) => setSelectedDatasetPresetId(event.target.value as DatasetPreset['id'])}>
            {DATASET_PRESETS.map((preset) => <option key={preset.id} value={preset.id}>{preset.label}</option>)}
          </select>
        </label>
        <label>Universe type
          <select value={datasetCreateForm.universeType} onChange={(event) => setDatasetCreateForm((prev) => ({ ...prev, universeType: event.target.value as DatasetCreateForm['universeType'] }))}><option value="stocks">stocks</option><option value="options">options</option></select>
        </label>
        <label>Symbols list (comma separated)
          <input value={datasetCreateForm.symbolsCsv} onChange={(event) => setDatasetCreateForm((prev) => ({ ...prev, symbolsCsv: event.target.value }))} disabled={selectedDatasetPreset.symbolStrategy !== 'manual_symbols'} />
        </label>
        <label>Saved universe ID
          <input value={datasetCreateForm.savedUniverseId} onChange={(event) => setDatasetCreateForm((prev) => ({ ...prev, savedUniverseId: event.target.value }))} disabled={selectedDatasetPreset.symbolStrategy !== 'saved_universe'} />
        </label>
        <label>Start date<input type="date" value={datasetCreateForm.startDate} onChange={(event) => setDatasetCreateForm((prev) => ({ ...prev, startDate: event.target.value }))} /></label>
        <label>End date<input type="date" value={datasetCreateForm.endDate} onChange={(event) => setDatasetCreateForm((prev) => ({ ...prev, endDate: event.target.value }))} /></label>
        <label>Finest resolution<input value={datasetCreateForm.finestResolution} onChange={(event) => setDatasetCreateForm((prev) => ({ ...prev, finestResolution: event.target.value }))} /></label>
        <label><input type="checkbox" checked={datasetCreateForm.featurePackEnabled} onChange={(event) => setDatasetCreateForm((prev) => ({ ...prev, featurePackEnabled: event.target.checked }))} /> Feature pack enabled</label>
        <button type="button" onClick={() => void createDataset()}>Start dataset download on server</button>
        {Object.values(datasetFormErrors)[0] ? <small className="error">{Object.values(datasetFormErrors).filter(Boolean).join(' ')}</small> : null}
        {notice ? <p className="muted">{notice}</p> : null}
      </div>
    </section>
  );
}
