import { useMemo, useState } from 'react';
import { createDesktopApiClient } from '../api/client';

interface StrategyWorkbenchPageProps {
  baseUrl: string;
}

export function StrategyWorkbenchPage({ baseUrl }: StrategyWorkbenchPageProps): JSX.Element {
  const client = useMemo(() => createDesktopApiClient({ baseHttpUrl: baseUrl }), [baseUrl]);
  const [riskTolerance, setRiskTolerance] = useState(35);
  const [positionCap, setPositionCap] = useState(8);
  const [explorationWeight, setExplorationWeight] = useState(20);

  void client;

  return (
    <section>
      <h2>Strategy Workbench</h2>
      <p>Design, gate, and observe strategy experiments before rolling changes into paper or live modes.</p>

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
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <button type="button">Queue incremental retraining</button>
          <button type="button">Run stress-test backfill</button>
          <button type="button">Export training report</button>
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
        <ul>
          <li>Inference stream: Healthy (0 dropped batches in last 15m)</li>
          <li>Paper rollout coverage: 42% of eligible symbols</li>
          <li>Guardrail alerts: 1 warning (spread anomaly) pending review</li>
        </ul>
      </div>
    </section>
  );
}
