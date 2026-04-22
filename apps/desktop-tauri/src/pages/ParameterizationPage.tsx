import { ParameterSweepsPage } from './ParameterSweepsPage';

interface ParameterizationPageProps {
  baseUrl: string;
}

export function ParameterizationPage({ baseUrl }: ParameterizationPageProps): JSX.Element {
  return (
    <section>
      <h2>Parameterization</h2>
      <p className="muted">Migration anchor: this workflow currently maps to Parameter Sweeps.</p>
      <ParameterSweepsPage baseUrl={baseUrl} />
    </section>
  );
}
