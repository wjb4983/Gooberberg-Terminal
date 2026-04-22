import { useEffect } from 'react';
import { DataTable } from '../components/DataTable';
import { useOperatorConsole } from '../context/OperatorConsoleContext';
import { useJobLifecycle } from '../hooks/useJobLifecycle';

interface JobsPageProps {
  baseUrl: string;
}

export function JobsPage({ baseUrl }: JobsPageProps): JSX.Element {
  const { items: events, connectionState } = useJobLifecycle(baseUrl);
  const { reportWebSocketStatus } = useOperatorConsole();

  useEffect(() => {
    reportWebSocketStatus(connectionState);
  }, [connectionState, reportWebSocketStatus]);

  return (
    <section>
      <h2>Jobs</h2>
      <p>Live job lifecycle updates via topic WebSocket.</p>
      <DataTable
        title="Job events"
        rows={events}
        emptyLabel="Waiting for job events…"
        searchPlaceholder="Search by id/status/detail"
        searchValue={(event) => `${event.job_id} ${event.status} ${event.detail}`}
        columns={[
          { key: 'job', header: 'Job ID', render: (event) => event.job_id },
          { key: 'status', header: 'Status', render: (event) => event.status },
          { key: 'detail', header: 'Detail', render: (event) => event.detail },
          { key: 'updated', header: 'Updated', render: (event) => new Date(event.updated_at).toLocaleString() },
        ]}
      />
    </section>
  );
}
