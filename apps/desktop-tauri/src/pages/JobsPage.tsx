import { GbApiClient, parseJobLifecyclePayload } from '@gb/api-client';
import type { JobLifecyclePayload } from '@gb/schemas';
import { useEffect, useMemo, useRef, useState } from 'react';
import { DataTable } from '../components/DataTable';
import { useOperatorConsole } from '../context/OperatorConsoleContext';

interface JobsPageProps {
  baseUrl: string;
}

export function JobsPage({ baseUrl }: JobsPageProps): JSX.Element {
  const client = useMemo(() => new GbApiClient({ baseHttpUrl: baseUrl }), [baseUrl]);
  const [events, setEvents] = useState<JobLifecyclePayload[]>([]);
  const [connectionState, setConnectionState] = useState('connecting');
  const lastSeqRef = useRef<number | undefined>(undefined);
  const { reportWebSocketStatus } = useOperatorConsole();

  useEffect(() => {
    reportWebSocketStatus(connectionState);
  }, [connectionState, reportWebSocketStatus]);

  useEffect(() => {
    const connection = client.connectTopicWebSocket({
      topics: ['jobs'],
      getResumeSeq: () => lastSeqRef.current,
      onStatus: setConnectionState,
      onEvent: (event) => {
        if (event.topic !== 'jobs') {
          return;
        }

        lastSeqRef.current = event.seq;
        const payload = parseJobLifecyclePayload(event.payload);
        if (!payload) {
          return;
        }

        setEvents((previous) => [payload, ...previous].slice(0, 100));
      },
    });

    return () => {
      connection.close();
    };
  }, [client]);

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
