import { useEffect, useMemo, useState } from 'react';

import { GbApiClient } from '@gb/api-client';
import type { PortfolioSnapshot } from '@gb/schemas';

interface PortfolioPageProps {
  baseUrl: string;
}

export function PortfolioPage({ baseUrl }: PortfolioPageProps): JSX.Element {
  const [snapshot, setSnapshot] = useState<PortfolioSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const client = useMemo(() => new GbApiClient({ baseHttpUrl: baseUrl }), [baseUrl]);

  useEffect(() => {
    let active = true;

    const load = async (): Promise<void> => {
      try {
        const next = await client.getPortfolioSnapshot();
        if (!active) return;
        setSnapshot(next);
        setError(null);
      } catch (err) {
        if (!active) return;
        setError(err instanceof Error ? err.message : 'Failed to load portfolio snapshot.');
      } finally {
        if (active) setLoading(false);
      }
    };

    void load();
    const timer = setInterval(() => {
      void load();
    }, 2_000);

    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [client]);

  return (
    <div>
      <h2>Portfolio</h2>
      <p>Latest account snapshot from control-plane API.</p>
      {loading && <p className="muted">Loading snapshot...</p>}
      {error && <p className="error">{error}</p>}
      {snapshot && (
        <div className="card jobs-card">
          <p><strong>Account:</strong> {snapshot.accountId}</p>
          <p><strong>Gross Exposure:</strong> {snapshot.grossExposure.toFixed(2)}</p>
          <p><strong>Net Exposure:</strong> {snapshot.netExposure.toFixed(2)}</p>
          <p><strong>Unrealized PnL:</strong> {snapshot.unrealizedPnl.toFixed(2)}</p>
          <table className="jobs-table">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Qty</th>
                <th>Avg Px</th>
                <th>Mkt Px</th>
                <th>Mkt Value</th>
                <th>Unrealized PnL</th>
              </tr>
            </thead>
            <tbody>
              {snapshot.positions.map((position) => (
                <tr key={position.symbol}>
                  <td>{position.symbol}</td>
                  <td>{position.quantity.toFixed(2)}</td>
                  <td>{position.averagePrice.toFixed(2)}</td>
                  <td>{position.marketPrice.toFixed(2)}</td>
                  <td>{position.marketValue.toFixed(2)}</td>
                  <td>{position.unrealizedPnl.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
