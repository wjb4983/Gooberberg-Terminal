import { Route, Routes } from 'react-router-dom';

import { AppShell } from './layout/AppShell';
import { PlaceholderPage } from './pages/PlaceholderPage';
import { DashboardPage } from './pages/DashboardPage';
import { JobsPage } from './pages/JobsPage';
import { SettingsPage } from './pages/SettingsPage';
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
        <Route index element={<DashboardPage baseUrl={baseUrl} />} />
        <Route path="jobs" element={<JobsPage baseUrl={baseUrl} />} />
        <Route path="strategies" element={<PlaceholderPage title="Strategies" description="Strategy catalog and controls." />} />
        <Route path="portfolio" element={<PlaceholderPage title="Portfolio" description="Portfolio overview and positions." />} />
        <Route path="graph" element={<PlaceholderPage title="Graph" description="Graph exploration and analysis." />} />
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
