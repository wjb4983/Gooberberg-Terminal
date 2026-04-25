import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { createDesktopApiClient } from '../api/client';
import { requestJson } from '../api/requestJson';
import { JobLifecyclePanel } from '../components/JobLifecyclePanel';

interface BacktestsPageProps { baseUrl: string; }
interface BacktestRunItem {
  id: string;
  strategy_key: string;
  model_config_id: string | null;
  window_start: string;
  window_end: string;
  parameters: Record<string, unknown>;
  job_id: string;
  status: string;
  created_at: string;
}
interface ModelConfigItem { id: string; config: Record<string, unknown>; }
interface RunEvent { timestamp: string; status: string; detail: string; }
interface PreflightEstimate {
  symbol_count: number;
  date_span_days: number;
  estimated_units: number;
  oversized_threshold: number;
  requires_confirmation: boolean;
  confirmation_token: string | null;
  heuristic: string;
}
interface PagedRows { items: Array<Record<string, unknown>>; next_offset: number | null; }

type DetailTab = 'status' | 'events' | 'metrics' | 'trades' | 'equity';

function VirtualizedRows({ rows }: { rows: Array<Record<string, unknown>> }): JSX.Element {
  const rowHeight = 28;
  const viewportHeight = 260;
  const [scrollTop, setScrollTop] = useState(0);
  const start = Math.max(0, Math.floor(scrollTop / rowHeight) - 3);
  const visibleCount = Math.ceil(viewportHeight / rowHeight) + 6;
  const end = Math.min(rows.length, start + visibleCount);
  const visibleRows = rows.slice(start, end);

  return (
    <div style={{ maxHeight: viewportHeight, overflowY: 'auto', border: '1px solid var(--border-color)' }} onScroll={(event) => setScrollTop(event.currentTarget.scrollTop)}>
      <div style={{ height: rows.length * rowHeight, position: 'relative' }}>
        <div style={{ position: 'absolute', top: start * rowHeight, left: 0, right: 0 }}>
          {visibleRows.map((row, idx) => (
            <div key={`${String(row.id ?? row.timestamp ?? idx)}-${start + idx}`} style={{ height: rowHeight, padding: '4px 8px', borderBottom: '1px solid var(--border-color)', fontFamily: 'monospace', fontSize: '0.8rem' }}>
              {JSON.stringify(row)}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export function BacktestsPage({ baseUrl }: BacktestsPageProps): JSX.Element {
  const client = useMemo(() => createDesktopApiClient({ baseHttpUrl: baseUrl }), [baseUrl]);
  const [searchParams, setSearchParams] = useSearchParams();
  const [runs, setRuns] = useState<BacktestRunItem[]>([]);
  const [configs, setConfigs] = useState<ModelConfigItem[]>([]);
  const [strategyKey, setStrategyKey] = useState('mean_reversion');
  const [selectedConfigId, setSelectedConfigId] = useState('');
  const [windowStart, setWindowStart] = useState('2024-01-01T00:00:00Z');
  const [windowEnd, setWindowEnd] = useState('2024-12-31T00:00:00Z');
  const [paramsJson, setParamsJson] = useState('{"slippage_bps": 2, "symbols": ["AAPL", "MSFT"]}');
  const [eventsByJob, setEventsByJob] = useState<Record<string, RunEvent[]>>({});
  const [summary, setSummary] = useState('No run selected.');
  const [error, setError] = useState<string | null>(null);
  const [estimate, setEstimate] = useState<PreflightEstimate | null>(null);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [pendingConfirmationToken, setPendingConfirmationToken] = useState<string | null>(null);
  const [detailTab, setDetailTab] = useState<DetailTab>('status');
  const [detailEvents, setDetailEvents] = useState<Array<Record<string, unknown>>>([]);
  const [detailTrades, setDetailTrades] = useState<Array<Record<string, unknown>>>([]);
  const [nextEventsOffset, setNextEventsOffset] = useState<number | null>(0);
  const [nextTradesOffset, setNextTradesOffset] = useState<number | null>(0);
  const [metrics, setMetrics] = useState<Record<string, unknown>>({});
  const [equityRefs, setEquityRefs] = useState<string[]>([]);
  const lastSeqRef = useRef<number | undefined>(undefined);
  const pollDebounceRef = useRef<number | null>(null);

  const selectedJobId = searchParams.get('job_id');
  const selectedRun = useMemo(() => runs.find((item) => item.job_id === selectedJobId) ?? null, [runs, selectedJobId]);

  const setSelectedJobId = (jobId: string): void => {
    setSearchParams((previous) => {
      const next = new URLSearchParams(previous);
      next.set('job_id', jobId);
      return next;
    });
  };

  const load = useCallback(async (): Promise<void> => {
    try {
      const [runPayload, configPayload] = await Promise.all([
        requestJson<BacktestRunItem[]>(baseUrl, '/api/v1/backtest-runs'),
        requestJson<ModelConfigItem[]>(baseUrl, '/api/v1/model-configs'),
      ]);
      setRuns(runPayload);
      setConfigs(configPayload);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Failed loading backtests.');
    }
  }, [baseUrl]);

  const runPreflight = useCallback(async (): Promise<PreflightEstimate | null> => {
    let parsedParameters: Record<string, unknown>;
    try { parsedParameters = JSON.parse(paramsJson) as Record<string, unknown>; } catch { setError('Parameters must be valid JSON.'); return null; }

    const payload = await requestJson<PreflightEstimate>(baseUrl, '/api/v1/backtest-runs/preflight', {
      method: 'POST',
      body: JSON.stringify({ strategy_key: strategyKey, model_config_id: selectedConfigId || null, window_start: windowStart, window_end: windowEnd, parameters: parsedParameters }),
    });
    setEstimate(payload);
    return payload;
  }, [baseUrl, paramsJson, selectedConfigId, strategyKey, windowEnd, windowStart]);

  useEffect(() => { void load(); }, [load]);

  useEffect(() => {
    const timer = window.setTimeout(() => { void runPreflight().catch(() => undefined); }, 300);
    return () => window.clearTimeout(timer);
  }, [runPreflight]);

  useEffect(() => {
    const connection = client.connectTopicWebSocket({
      topics: ['backtests'],
      getResumeSeq: () => lastSeqRef.current,
      onEvent: (event) => {
        if (event.topic !== 'backtests') return;
        lastSeqRef.current = event.seq;
        const payload = event.payload as Record<string, unknown>;
        const jobId = typeof payload.job_id === 'string' ? payload.job_id : '';
        if (!jobId) return;
        const next: RunEvent = {
          timestamp: typeof payload.updated_at === 'string' ? payload.updated_at : event.timestamp,
          status: typeof payload.status === 'string' ? payload.status : 'unknown',
          detail: typeof payload.message === 'string' ? payload.message : JSON.stringify(payload),
        };
        setEventsByJob((prev) => ({ ...prev, [jobId]: [next, ...(prev[jobId] ?? [])].slice(0, 200) }));
        if (selectedRun?.job_id === jobId) setSummary(`${next.status}: ${next.detail}`);
      },
    });
    return () => connection.close();
  }, [client, selectedRun]);

  useEffect(() => {
    if (!selectedRun) return;
    const pollStatus = (): void => {
      if (pollDebounceRef.current) window.clearTimeout(pollDebounceRef.current);
      pollDebounceRef.current = window.setTimeout(() => {
        void requestJson<{ status: string; summary: string }>(baseUrl, `/api/v1/backtest-runs/${encodeURIComponent(selectedRun.id)}/status`)
          .then((payload) => setSummary(`${payload.status}: ${payload.summary}`))
          .catch(() => undefined);
      }, 500);
    };

    pollStatus();
    const interval = window.setInterval(pollStatus, 5000);
    return () => {
      window.clearInterval(interval);
      if (pollDebounceRef.current) window.clearTimeout(pollDebounceRef.current);
    };
  }, [baseUrl, selectedRun]);

  const launch = async (confirmationToken: string | null = null): Promise<void> => {
    setError(null);
    let parsedParameters: Record<string, unknown>;
    try { parsedParameters = JSON.parse(paramsJson) as Record<string, unknown>; } catch { setError('Parameters must be valid JSON.'); return; }

    try {
      const preflight = await runPreflight();
      if (!preflight) return;
      if (preflight.requires_confirmation && !confirmationToken) {
        setPendingConfirmationToken(preflight.confirmation_token ?? null);
        setShowConfirmModal(true);
        return;
      }

      const created = await requestJson<BacktestRunItem>(baseUrl, '/api/v1/backtest-runs', {
        method: 'POST',
        body: JSON.stringify({
          strategy_key: strategyKey,
          model_config_id: selectedConfigId || null,
          window_start: windowStart,
          window_end: windowEnd,
          parameters: parsedParameters,
          confirmation_token: confirmationToken,
        }),
      });
      setRuns((prev) => [created, ...prev]);
      setSelectedJobId(created.job_id);
      setSummary('queued: backtest run accepted by api-control-plane');
      setShowConfirmModal(false);
      setPendingConfirmationToken(null);
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : 'Failed launching backtest.');
    }
  };

  const fetchRows = useCallback(async (type: 'events' | 'trades'): Promise<void> => {
    if (!selectedRun) return;
    const nextOffset = type === 'events' ? nextEventsOffset : nextTradesOffset;
    if (nextOffset === null) return;
    const payload = await requestJson<PagedRows>(baseUrl, `/api/v1/backtest-runs/${encodeURIComponent(selectedRun.id)}/${type}?offset=${nextOffset}&limit=200`);
    if (type === 'events') {
      setDetailEvents((prev) => [...prev, ...payload.items]);
      setNextEventsOffset(payload.next_offset);
    } else {
      setDetailTrades((prev) => [...prev, ...payload.items]);
      setNextTradesOffset(payload.next_offset);
    }
  }, [baseUrl, nextEventsOffset, nextTradesOffset, selectedRun]);

  useEffect(() => {
    if (!selectedRun) return;
    setDetailEvents([]); setDetailTrades([]); setNextEventsOffset(0); setNextTradesOffset(0); setMetrics({}); setEquityRefs([]);
    void requestJson<{ metrics: Record<string, unknown> }>(baseUrl, `/api/v1/backtest-runs/${encodeURIComponent(selectedRun.id)}/metrics`).then((r) => setMetrics(r.metrics)).catch(() => undefined);
    void requestJson<{ refs: string[] }>(baseUrl, `/api/v1/backtest-runs/${encodeURIComponent(selectedRun.id)}/equity-refs`).then((r) => setEquityRefs(r.refs)).catch(() => undefined);
  }, [baseUrl, selectedRun]);

  return (
    <section>
      <h2>Backtests</h2>
      <p>Launch backtests with server-side preflight estimate, explicit oversize confirmation, and staged run details.</p>
      {error ? <p className="muted">Error: {error}</p> : null}

      <div className="card" style={{ marginBottom: '1rem' }}>
        <h3>Launch backtest</h3>
        <div style={{ display: 'grid', gap: '0.5rem' }}>
          <input value={strategyKey} onChange={(event) => setStrategyKey(event.target.value)} placeholder="Strategy key" />
          <select value={selectedConfigId} onChange={(event) => setSelectedConfigId(event.target.value)}>
            <option value="">No model config</option>
            {configs.map((config) => <option key={config.id} value={config.id}>{typeof config.config.name === 'string' ? config.config.name : config.id}</option>)}
          </select>
          <input value={windowStart} onChange={(event) => setWindowStart(event.target.value)} placeholder="Window start (ISO)" />
          <input value={windowEnd} onChange={(event) => setWindowEnd(event.target.value)} placeholder="Window end (ISO)" />
          <textarea value={paramsJson} onChange={(event) => setParamsJson(event.target.value)} rows={3} />
          <div className="card" style={{ margin: 0 }}>
            <strong>Preflight estimate</strong>
            <p style={{ margin: '0.2rem 0' }}>
              {estimate ? `symbols=${estimate.symbol_count}, days=${estimate.date_span_days}, units=${estimate.estimated_units} (${estimate.heuristic})` : 'No estimate yet.'}
            </p>
            {estimate?.requires_confirmation ? <p className="muted">Large run: exceeds threshold {estimate.oversized_threshold} and requires confirmation.</p> : null}
          </div>
          <button type="button" onClick={() => void launch()}>Launch backtest</button>
        </div>
      </div>

      {showConfirmModal ? (
        <div className="card" style={{ border: '1px solid #d8a', marginBottom: '1rem' }}>
          <h4>Confirm oversized run</h4>
          <p>This run exceeds server threshold. Confirm to continue.</p>
          <button type="button" onClick={() => void launch(pendingConfirmationToken)}>Confirm and launch</button>{' '}
          <button type="button" onClick={() => setShowConfirmModal(false)}>Cancel</button>
        </div>
      ) : null}

      <div className="card jobs-card">
        <table className="jobs-table">
          <thead><tr><th>ID</th><th>Job ID</th><th>Strategy</th><th>Model Config</th><th>Status</th><th>Window</th></tr></thead>
          <tbody>
            {runs.length === 0 ? <tr><td colSpan={6}>No backtests yet.</td></tr> : null}
            {runs.map((run) => (
              <tr key={run.id} onClick={() => setSelectedJobId(run.job_id)} style={{ cursor: 'pointer', background: selectedJobId === run.job_id ? 'rgba(127,127,127,0.12)' : undefined }}>
                <td>{run.id.slice(0, 8)}</td><td>{run.job_id.slice(0, 8)}</td><td>{run.strategy_key}</td><td>{run.model_config_id ? run.model_config_id.slice(0, 8) : '-'}</td><td>{run.status}</td><td>{new Date(run.window_start).toLocaleDateString()} → {new Date(run.window_end).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card" style={{ marginTop: '1rem' }}>
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem' }}>
          {(['status', 'events', 'metrics', 'trades', 'equity'] as DetailTab[]).map((tab) => <button key={tab} type="button" onClick={() => setDetailTab(tab)} style={{ opacity: detailTab === tab ? 1 : 0.65 }}>{tab}</button>)}
        </div>
        {!selectedRun ? <p className="muted">Select a run to inspect details.</p> : null}
        {selectedRun && detailTab === 'status' ? <p><strong>Persisted summary:</strong> {summary}</p> : null}
        {selectedRun && detailTab === 'events' ? <><VirtualizedRows rows={detailEvents} /><button type="button" onClick={() => void fetchRows('events')} disabled={nextEventsOffset === null}>Load more events</button></> : null}
        {selectedRun && detailTab === 'trades' ? <><VirtualizedRows rows={detailTrades} /><button type="button" onClick={() => void fetchRows('trades')} disabled={nextTradesOffset === null}>Load more trades</button></> : null}
        {selectedRun && detailTab === 'metrics' ? <pre>{JSON.stringify(metrics, null, 2)}</pre> : null}
        {selectedRun && detailTab === 'equity' ? <ul>{equityRefs.map((ref) => <li key={ref}>{ref}</li>)}</ul> : null}
      </div>

      <JobLifecyclePanel
        submitContent={<p>Submissions now include preflight sizing and optional explicit confirmation for oversized runs.</p>}
        runningContent={!selectedRun ? <p className="muted">Select a run to inspect details.</p> : (
          <ul>
            {(eventsByJob[selectedRun.job_id] ?? []).slice(0, 40).map((event, index) => (
              <li key={`${event.timestamp}-${index}`}>{new Date(event.timestamp).toLocaleTimeString()} · {event.status} · {event.detail}</li>
            ))}
            {(eventsByJob[selectedRun.job_id] ?? []).length === 0 ? <li>No live events yet.</li> : null}
          </ul>
        )}
        artifactContent={!selectedRun ? <p className="muted">Select a run to open job detail.</p> : <p><Link to={`/jobs/${encodeURIComponent(selectedRun.job_id)}`}>Open run detail view for job {selectedRun.job_id}</Link></p>}
      />
    </section>
  );
}
