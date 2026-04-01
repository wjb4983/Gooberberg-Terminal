import { useEffect, useMemo, useState } from 'react';

import type { ServiceHealth } from '@gb/schemas';
import { formatHealthLabel } from '@gb/ui-components';

import { HttpApiClient } from '../api/httpApiClient';
import { useOperatorConsole } from '../context/OperatorConsoleContext';
import { ApiErrorCallout } from './ApiErrorCallout';

interface HealthWidgetProps {
  baseUrl: string;
  getToken: () => Promise<string>;
}

export function HealthWidget({ baseUrl, getToken }: HealthWidgetProps): JSX.Element {
  const apiClient = useMemo(() => new HttpApiClient(baseUrl, getToken), [baseUrl, getToken]);

  const [health, setHealth] = useState<ServiceHealth | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const { reportApiStatus } = useOperatorConsole();

  useEffect(() => {
    let cancelled = false;

    const run = async (): Promise<void> => {
      setIsLoading(true);
      setError(null);

      try {
        const result = await apiClient.getHealth();
        if (!cancelled) {
          setHealth(result);
          reportApiStatus('connected');
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : 'Unknown error');
          reportApiStatus('offline');
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
  }, [apiClient, reportApiStatus]);

  return (
    <section className="card">
      <h2>Service Health</h2>
      {isLoading && <p>Loading /health ...</p>}
      {!isLoading && error && <ApiErrorCallout message={error} onRetry={() => window.location.reload()} />}
      {!isLoading && !error && health && <p>{formatHealthLabel(health)}</p>}
      {!isLoading && !error && !health && <p>No health data yet.</p>}
    </section>
  );
}
