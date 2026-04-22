import type { ReactNode } from 'react';

interface JobLifecyclePanelProps {
  submitContent: ReactNode;
  runningContent: ReactNode;
  artifactContent: ReactNode;
}

export function JobLifecyclePanel({ submitContent, runningContent, artifactContent }: JobLifecyclePanelProps): JSX.Element {
  return (
    <div className="card" style={{ marginTop: '1rem' }}>
      <h3>Job lifecycle</h3>
      <div style={{ display: 'grid', gap: '1rem' }}>
        <section>
          <h4>Submit job</h4>
          {submitContent}
        </section>
        <section>
          <h4>Running on server</h4>
          {runningContent}
        </section>
        <section>
          <h4>Artifact ready</h4>
          {artifactContent}
        </section>
      </div>
    </div>
  );
}
