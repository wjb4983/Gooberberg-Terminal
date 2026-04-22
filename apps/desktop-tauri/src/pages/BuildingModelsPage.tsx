import { ModelsPage } from './ModelsPage';

interface BuildingModelsPageProps {
  baseUrl: string;
}

export function BuildingModelsPage({ baseUrl }: BuildingModelsPageProps): JSX.Element {
  return (
    <section>
      <h2>Building Models</h2>
      <p className="muted">Migration anchor: this workflow currently maps to the existing Models experience.</p>
      <ModelsPage baseUrl={baseUrl} />
    </section>
  );
}
