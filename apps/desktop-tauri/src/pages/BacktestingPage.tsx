import { BacktestsPage } from './BacktestsPage';

interface BacktestingPageProps {
  baseUrl: string;
}

export function BacktestingPage({ baseUrl }: BacktestingPageProps): JSX.Element {
  return (
    <section>
      <h2>Full-on Backtesting</h2>
      <p className="muted">Migration anchor: this workflow currently maps to Backtests.</p>
      <BacktestsPage baseUrl={baseUrl} />
    </section>
  );
}
