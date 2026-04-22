import { useMemo } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useJobLifecycle } from '../hooks/useJobLifecycle';

interface JobDetailPageProps {
  baseUrl: string;
}

export function JobDetailPage({ baseUrl }: JobDetailPageProps): JSX.Element {
  const { jobId } = useParams<{ jobId: string }>();
  const { items, statusQuery } = useJobLifecycle(baseUrl, jobId);

  const events = useMemo(() => items.filter((item) => item.job_id === jobId), [items, jobId]);

  if (!jobId) {
    return (
      <section>
        <h2>Run detail</h2>
        <p className="muted">Missing job_id parameter.</p>
      </section>
    );
  }

  return (
    <section>
      <h2>Run detail: {jobId}</h2>
      <p><Link to="/jobs">Back to jobs</Link></p>
      <div className="card" style={{ marginBottom: '1rem' }}>
        <h3>Persisted status</h3>
        {statusQuery.isLoading ? <p>Loading persisted status…</p> : null}
        {statusQuery.isError ? <p className="muted">Unable to fetch job status.</p> : null}
        {statusQuery.data ? (
          <p><strong>{statusQuery.data.status}</strong> · {statusQuery.data.detail}</p>
        ) : null}
      </div>
      <div className="card">
        <h3>Live updates</h3>
        <ul>
          {events.map((event, index) => (
            <li key={`${event.updated_at}-${index}`}>{new Date(event.updated_at).toLocaleTimeString()} · {event.status} · {event.detail}</li>
          ))}
          {events.length === 0 ? <li>No events yet for this job.</li> : null}
        </ul>
      </div>
    </section>
  );
}
