import { HealthWidget } from '../components/HealthWidget';

interface DashboardPageProps {
  baseUrl: string;
  getToken: () => Promise<string>;
}

export function DashboardPage({ baseUrl, getToken }: DashboardPageProps): JSX.Element {
  return (
    <div>
      <h2>Dashboard</h2>
      <p>Overview of system state.</p>
      <HealthWidget baseUrl={baseUrl} getToken={getToken} />
    </div>
  );
}
