import { Link, useSearchParams } from 'react-router-dom';
import { GraphPage } from './GraphPage';
import { JobLifecyclePanel } from '../components/JobLifecyclePanel';

interface GraphingPageProps {
  baseUrl: string;
}

export function GraphingPage({ baseUrl }: GraphingPageProps): JSX.Element {
  const [searchParams, setSearchParams] = useSearchParams();
  const jobId = searchParams.get('job_id') ?? '';

  return (
    <section>
      <h2>Graphing</h2>
      <p className="muted">Migration anchor: this workflow currently maps to Graph.</p>
      <GraphPage baseUrl={baseUrl} />
      <JobLifecyclePanel
        submitContent={<p>Provide a <code>job_id</code> to link this graphing session to a run-detail route.</p>}
        runningContent={<input value={jobId} onChange={(event) => setSearchParams({ job_id: event.target.value })} placeholder="Enter job_id" />}
        artifactContent={jobId ? <p><Link to={`/jobs/${encodeURIComponent(jobId)}`}>Open run detail view for job {jobId}</Link></p> : <p className="muted">Enter a job_id to enable run-detail navigation.</p>}
      />
    </section>
  );
}
