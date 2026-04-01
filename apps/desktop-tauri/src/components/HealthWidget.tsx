import { useEffect, useMemo, useState } from 'react';

import type { ServiceHealth } from '@gb/schemas';
import { formatHealthLabel } from '@gb/ui-components';

import { HttpApiClient } from '../api/httpApiClient';

interface HealthWidgetProps {
  baseUrl: string;
}

export function HealthWidget({ baseUrl }: HealthWidgetProps): JSX.Element {
  const apiClient = useMemo(() => new HttpApiClient(baseUrl), [baseUrl]);

  const [health, setHealth] = useState<ServiceHealth | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const run = async (): Promise<void> => {
      setIsLoading(true);
      setError(null);

      try {
        const result = await apiClient.getHealth();
        if (!cancelled) {
          setHealth(result);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : 'Unknown error');
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    void run();

    return () => {
      cancelled = true;
    };
  }, [apiClient]);

  return (
    <section className="card">
      <h2>Service Health</h2>
      {isLoading && <p>Loading /health ...</p>}
      {!isLoading && error && <p className="error">{error}</p>}
      {!isLoading && !error && health && <p>{formatHealthLabel(health)}</p>}
      {!isLoading && !error && !health && <p>No health data yet.</p>}
    </section>
  );
}
