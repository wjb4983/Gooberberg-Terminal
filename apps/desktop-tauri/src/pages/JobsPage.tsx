import { GbApiClient, parseJobLifecyclePayload } from '@gb/api-client';
import type { JobLifecyclePayload } from '@gb/schemas';
import { useEffect, useMemo, useRef, useState } from 'react';

interface JobsPageProps {
  baseUrl: string;
}

export function JobsPage({ baseUrl }: JobsPageProps): JSX.Element {
  const client = useMemo(() => new GbApiClient({ baseHttpUrl: baseUrl }), [baseUrl]);
  const [events, setEvents] = useState<JobLifecyclePayload[]>([]);
  const [connectionState, setConnectionState] = useState('connecting');
  const lastSeqRef = useRef<number | undefined>(undefined);

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

        setEvents((previous) => [payload, ...previous].slice(0, 50));
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
      <p className="muted">Connection: {connectionState}</p>

      <div className="card jobs-card">
        <table className="jobs-table">
          <thead>
            <tr>
              <th>Job ID</th>
              <th>Status</th>
              <th>Detail</th>
              <th>Updated</th>
            </tr>
          </thead>
          <tbody>
            {events.length === 0 ? (
              <tr>
                <td colSpan={4}>Waiting for job events…</td>
              </tr>
            ) : (
              events.map((event) => (
                <tr key={`${event.job_id}-${event.updated_at}`}>
                  <td>{event.job_id}</td>
                  <td>{event.status}</td>
                  <td>{event.detail}</td>
                  <td>{new Date(event.updated_at).toLocaleString()}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
