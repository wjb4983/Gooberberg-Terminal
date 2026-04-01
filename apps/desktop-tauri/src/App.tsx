import { Route, Routes } from 'react-router-dom';

import { AppShell } from './layout/AppShell';
import { StrategiesPage } from './pages/StrategiesPage';
import { DashboardPage } from './pages/DashboardPage';
import { JobsPage } from './pages/JobsPage';
import { ModelDeploymentsPage } from './pages/ModelDeploymentsPage';
import { SettingsPage } from './pages/SettingsPage';
import { GraphPage } from './pages/GraphPage';
import { AlertsHealthPage } from './pages/AlertsHealthPage';
import { PortfolioPage } from './pages/PortfolioPage';
import { loadPreferences, savePreferences } from './settings/preferences';
import { createTokenStorage } from './settings/tokenStorage';
import { useMemo, useState } from 'react';

export function App(): JSX.Element {
  const [baseUrl, setBaseUrl] = useState(() => loadPreferences().baseUrl);
  const tokenStorage = useMemo(() => createTokenStorage(), []);

  const saveBaseUrl = (nextBaseUrl: string): void => {
    setBaseUrl(nextBaseUrl);
    savePreferences({ baseUrl: nextBaseUrl });
  };

  return (
    <Routes>
      <Route path="/" element={<AppShell />}>
        <Route index element={<DashboardPage baseUrl={baseUrl} getToken={() => tokenStorage.getToken()} />} />
        <Route path="jobs" element={<JobsPage baseUrl={baseUrl} />} />
        <Route path="models" element={<ModelDeploymentsPage baseUrl={baseUrl} />} />
        <Route path="strategies" element={<StrategiesPage baseUrl={baseUrl} />} />
        <Route path="portfolio" element={<PortfolioPage baseUrl={baseUrl} />} />
        <Route path="graph" element={<GraphPage baseUrl={baseUrl} />} />
        <Route path="alerts-health" element={<AlertsHealthPage baseUrl={baseUrl} />} />
        <Route
          path="settings"
          element={
            <SettingsPage
              baseUrl={baseUrl}
              onSaveBaseUrl={saveBaseUrl}
              onSaveToken={(token) => tokenStorage.save({ token })}
            />
          }
        />
      </Route>
    </Routes>
  );
}
