import { TrainingRunsPage } from './TrainingRunsPage';

interface TestingPageProps {
  baseUrl: string;
}

export function TestingPage({ baseUrl }: TestingPageProps): JSX.Element {
  return (
    <section>
      <h2>Testing</h2>
      <p className="muted">Migration anchor: this workflow currently maps to Training Runs.</p>
      <TrainingRunsPage baseUrl={baseUrl} />
    </section>
  );
}
