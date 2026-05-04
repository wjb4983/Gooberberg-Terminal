import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  getStrategyExternalStatus,
  getStrategyTrainingLiveStatus,
  launchStrategyTrainingRun,
  listStrategyTrainingModels,
  type StrategyServiceStatus,
  type StrategyTrainingLaunchResponse,
} from '../api/strategyTraining';

interface StrategyWorkbenchPageProps {
  baseUrl: string;
}

export function StrategyWorkbenchPage({ baseUrl }: StrategyWorkbenchPageProps): JSX.Element {
  const [riskTolerance, setRiskTolerance] = useState(35);
  const [positionCap, setPositionCap] = useState(8);
  const [explorationWeight, setExplorationWeight] = useState(20);
  const [selectedModelId, setSelectedModelId] = useState('');
  const [trainingRun, setTrainingRun] = useState<StrategyTrainingLaunchResponse | null>(null);
  const [launchError, setLaunchError] = useState<string | null>(null);

  const modelsQuery = useQuery({
    queryKey: ['strategy-training', 'models', baseUrl],
    queryFn: () => listStrategyTrainingModels(baseUrl),
  });

  const liveStatusQuery = useQuery({
    queryKey: ['strategy-training', 'live-status', baseUrl, trainingRun?.run_id],
    queryFn: () => getStrategyTrainingLiveStatus(baseUrl, trainingRun?.run_id ?? ''),
    enabled: Boolean(trainingRun?.run_id),
    refetchInterval: (query) => {
      const status = query.state.data?.status ?? trainingRun?.status;
      return status === 'queued' || status === 'running' ? 2_500 : false;
    },
  });
  const externalStatusQuery = useQuery({
    queryKey: ['strategy-training', 'external-status', baseUrl],
    queryFn: () => getStrategyExternalStatus(baseUrl),
    refetchInterval: 10_000,
  });

  const selectedModel = (modelsQuery.data ?? [])[0];
  const staleModelSummary = selectedModel
    ? Date.now() - new Date(selectedModel.last_trained_at ?? selectedModel.created_at).getTime() > 24 * 60 * 60 * 1000
    : false;

  const handleLaunchTraining = async (): Promise<void> => {
    const modelId = selectedModelId || modelsQuery.data?.[0]?.id || '';
    if (!modelId) {
      setLaunchError('Select a model to launch training.');
      return;
    }

    setLaunchError(null);
    try {
      const created = await launchStrategyTrainingRun(baseUrl, {
        strategy_key: 'strategy-workbench',
        model_id: modelId,
        parameters: { riskTolerance, positionCap, explorationWeight },
      });
      setTrainingRun(created);
    } catch (error) {
      setLaunchError(error instanceof Error ? error.message : 'Failed to launch training run.');
    }
  };

  return (
    <section>
      <h2>Strategy Workbench</h2>
      <p>Design, gate, and observe strategy experiments before rolling changes into paper or live modes.</p>
      <p className="muted">Execution routing is handled by external paper/live services and only observed here.</p>

      <div className="card" style={{ marginBottom: '1rem' }}>
        <h3>KPI strip</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: '0.75rem' }}>
          <div><strong>Model:</strong> {selectedModel?.label ?? '—'}</div>
          <div><strong>Family:</strong> {selectedModel?.family ?? '—'}</div>
          <div><strong>Sharpe:</strong> {selectedModel?.sharpe ?? '—'}</div>
          <div><strong>Max DD:</strong> {selectedModel?.max_drawdown != null ? `${selectedModel.max_drawdown}%` : '—'}</div>
          <div><strong>Latency p95:</strong> {selectedModel?.latency_p95_ms != null ? `${selectedModel.latency_p95_ms}ms` : '—'}</div>
          <div><strong>Readiness:</strong> {selectedModel?.readiness ?? '—'}</div>
          <div><strong>Last trained:</strong> {selectedModel ? new Date(selectedModel.last_trained_at ?? selectedModel.created_at).toLocaleString() : '—'}</div>
        </div>
        {staleModelSummary ? <p className="muted">⚠️ Model summary data is stale (&gt;24h old).</p> : null}
      </div>

      <div className="card" style={{ marginBottom: '1rem' }}>
        <h3>Hypothesis</h3>
        <p>
          We expect a volatility-sensitive signal blend to reduce drawdown during high-spread windows while preserving directional
          alpha in stable sessions.
        </p>
      </div>

      <div className="card" style={{ marginBottom: '1rem' }}>
        <h3>Responsible deployment guidance</h3>
        <ol>
          <li>Validate feature drift and regime changes before promoting model snapshots.</li>
          <li>Promote to paper mode with minimum 24-hour soak and alert-on-anomaly checks enabled.</li>
          <li>Enable phased live rollout with capped exposure and explicit kill-switch ownership.</li>
        </ol>
      </div>

      <div className="card" style={{ marginBottom: '1rem' }}>
        <h3>Model controls</h3>
        <div style={{ display: 'grid', gap: '0.75rem' }}>
          <label>
            Risk tolerance ({riskTolerance}%)
            <input type="range" min={0} max={100} value={riskTolerance} onChange={(event) => setRiskTolerance(Number(event.target.value))} />
          </label>
          <label>
            Position cap ({positionCap}%)
            <input type="range" min={1} max={25} value={positionCap} onChange={(event) => setPositionCap(Number(event.target.value))} />
          </label>
          <label>
            Exploration weight ({explorationWeight}%)
            <input
              type="range"
              min={0}
              max={50}
              value={explorationWeight}
              onChange={(event) => setExplorationWeight(Number(event.target.value))}
            />
          </label>
        </div>
      </div>

      <div className="card" style={{ marginBottom: '1rem' }}>
        <h3>Training actions</h3>
        <div style={{ display: 'grid', gap: '0.75rem' }}>
          <label>
            Training model
            <select
              value={selectedModelId}
              onChange={(event) => setSelectedModelId(event.target.value)}
              disabled={modelsQuery.isLoading || modelsQuery.data?.length === 0}
            >
              <option value="">{modelsQuery.isLoading ? 'Loading models…' : 'Select a model'}</option>
              {(modelsQuery.data ?? []).map((model) => (
                <option key={model.id} value={model.id}>
                  {model.label} ({model.family})
                </option>
              ))}
            </select>
          </label>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <button type="button" onClick={() => void handleLaunchTraining()}>Queue incremental retraining</button>
            <button type="button">Run stress-test backfill</button>
            <button type="button">Export training report</button>
          </div>
          {modelsQuery.isError ? <p className="muted">Paper/live model service not implemented yet.</p> : null}
          {modelsQuery.data && modelsQuery.data.length === 0 ? <p className="muted">No models available yet from training model service.</p> : null}
          {launchError ? <p className="muted">Error: {launchError}</p> : null}
          {trainingRun ? (
            <p className="muted">
              Training run {trainingRun.run_id} launched as job {trainingRun.job_id}.
            </p>
          ) : null}
        </div>
      </div>

      <div className="card" style={{ marginBottom: '1rem' }}>
        <h3>Model comparison</h3>
        <table className="jobs-table">
          <thead>
            <tr>
              <th>Model</th>
              <th>Sharpe</th>
              <th>Max drawdown</th>
              <th>Latency p95</th>
              <th>Readiness</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>signal-transformer-v4</td>
              <td>1.47</td>
              <td>-5.2%</td>
              <td>84ms</td>
              <td>Candidate</td>
            </tr>
            <tr>
              <td>signal-transformer-v3</td>
              <td>1.34</td>
              <td>-6.1%</td>
              <td>78ms</td>
              <td>Baseline</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className="card">
        <h3>Live status dashboard</h3>
        {liveStatusQuery.isError ? <p className="muted">Paper/live status microservice not implemented yet.</p> : null}
        {!trainingRun ? <p className="muted">Launch a training run to monitor queued/running/completed/failed status.</p> : null}
        {trainingRun ? (
          <ul>
            <li>Run: {trainingRun.run_id}</li>
            <li>Job: {trainingRun.job_id}</li>
            <li>Status: {(liveStatusQuery.data?.status ?? trainingRun.status).toUpperCase()}</li>
            <li>Detail: {liveStatusQuery.data?.detail ?? trainingRun.detail}</li>
            <li>Last updated: {new Date(liveStatusQuery.data?.updated_at ?? trainingRun.created_at).toLocaleString()}</li>
          </ul>
        ) : null}
      </div>

      <div className="card" style={{ marginTop: '1rem' }}>
        <h3>External execution status</h3>
        <p className="muted">Paper/live execution is performed outside this UI. Status below reflects upstream connectivity snapshots.</p>
        {externalStatusQuery.isError ? <p className="muted">Unable to load external service status.</p> : null}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '0.75rem' }}>
          {(['paper', 'live'] as const).map((mode) => (
            <ServiceStatusWidget key={mode} label={mode.toUpperCase()} status={externalStatusQuery.data?.[mode]} />
          ))}
        </div>
      </div>
    </section>
  );
}

function ServiceStatusWidget({ label, status }: { label: string; status?: StrategyServiceStatus }): JSX.Element {
  if (!status) {
    return <div className="card"><strong>{label}</strong><p className="muted">No status available.</p></div>;
  }
  const staleHeartbeat = status.heartbeat_age_seconds != null && status.heartbeat_age_seconds > 90;
  return (
    <div className="card">
      <strong>{label} service</strong>
      <ul>
        <li>Connectivity: {status.connected ? 'connected' : 'disconnected'}</li>
        <li>Probe status: {status.status}</li>
        <li>Heartbeat: {status.heartbeat_at ? new Date(status.heartbeat_at).toLocaleString() : 'not provided'}</li>
        <li>Heartbeat age: {status.heartbeat_age_seconds != null ? `${Math.round(status.heartbeat_age_seconds)}s` : 'not provided'}</li>
        {status.pnl != null ? <li>PnL: {status.pnl}</li> : null}
        {status.exposure != null ? <li>Exposure: {status.exposure}</li> : null}
      </ul>
      {staleHeartbeat ? <p className="muted">⚠️ Stale heartbeat detected for {label.toLowerCase()} service.</p> : null}
    </div>
  );
}
