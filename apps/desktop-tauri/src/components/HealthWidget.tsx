import { useEffect } from 'react';
import { formatHealthLabel } from '@gb/ui-components';

import { useOperatorConsole } from '../context/OperatorConsoleContext';
import { useSystemStatus } from '../hooks/useSystemStatus';
import { ApiErrorCallout } from './ApiErrorCallout';

interface HealthWidgetProps {
  baseUrl: string;
}

export function HealthWidget({ baseUrl }: HealthWidgetProps): JSX.Element {
  const { data: health, error, isLoading, refetch } = useSystemStatus(baseUrl);
  const { reportApiStatus } = useOperatorConsole();

  useEffect(() => {
    reportApiStatus(error ? 'offline' : 'connected');
  }, [error, reportApiStatus]);

  return (
    <section className="card">
      <h2>Service Health</h2>
      {isLoading && <p>Loading /api/v1/health ...</p>}
      {!isLoading && error && <ApiErrorCallout message={error instanceof Error ? error.message : 'Unknown error'} onRetry={() => void refetch()} />}
      {!isLoading && !error && health && <p>{formatHealthLabel(health)}</p>}
      {!isLoading && !error && !health && <p>No health data yet.</p>}
    </section>
  );
}
