import { HealthWidget } from '../components/HealthWidget';

interface DashboardPageProps {
  baseUrl: string;
}

export function DashboardPage({ baseUrl }: DashboardPageProps): JSX.Element {
  return (
    <div>
      <h2>Dashboard</h2>
      <p>Overview of system state.</p>
      <HealthWidget baseUrl={baseUrl} />
    </div>
  );
}
