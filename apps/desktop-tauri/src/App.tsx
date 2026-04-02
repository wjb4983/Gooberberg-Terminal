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
import { OperatorConsoleProvider } from './context/OperatorConsoleContext';
import type { ThemePreference } from './types/api';
import { ErrorBoundary } from './components/ErrorBoundary';

interface ToastItem {
  id: number;
  message: string;
  tone: 'warning' | 'critical';
}

export function App(): JSX.Element {
  const [preferences, setPreferences] = useState(() => loadPreferences());
  const tokenStorage = useMemo(() => createTokenStorage(), []);
  const [apiStatus, setApiStatus] = useState<'connected' | 'degraded' | 'offline'>('degraded');
  const [wsStatus, setWsStatus] = useState('connecting');
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const saveBaseUrl = (nextBaseUrl: string): void => {
    const next = { ...preferences, baseUrl: nextBaseUrl };
    setPreferences(next);
    savePreferences(next);
  };

  const saveUiPreferences = (nextTheme: ThemePreference, compactLayout: boolean, defaultSeverity: 'all' | 'info' | 'warning' | 'critical'): void => {
    const next = {
      ...preferences,
      theme: nextTheme,
      compactLayout,
      filterDefaults: { severity: defaultSeverity },
    };
    setPreferences(next);
    savePreferences(next);
  };

  const pushToast = (toast: { message: string; tone: 'warning' | 'critical' }): void => {
    const id = Date.now();
    setToasts((previous) => [...previous, { id, ...toast }]);
    setTimeout(() => {
      setToasts((previous) => previous.filter((item) => item.id !== id));
    }, 5000);
  };

  return (
    <OperatorConsoleProvider value={{ reportApiStatus: setApiStatus, reportWebSocketStatus: setWsStatus, pushToast }}>
      <Routes>
        <Route path="/" element={<AppShell apiStatus={apiStatus} wsStatus={wsStatus} toasts={toasts} theme={preferences.theme} compactLayout={preferences.compactLayout} />}>
          <Route index element={<ErrorBoundary><DashboardPage baseUrl={preferences.baseUrl} /></ErrorBoundary>} />
          <Route path="jobs" element={<ErrorBoundary><JobsPage baseUrl={preferences.baseUrl} /></ErrorBoundary>} />
          <Route path="models" element={<ErrorBoundary><ModelDeploymentsPage baseUrl={preferences.baseUrl} /></ErrorBoundary>} />
          <Route path="strategies" element={<ErrorBoundary><StrategiesPage baseUrl={preferences.baseUrl} /></ErrorBoundary>} />
          <Route path="portfolio" element={<ErrorBoundary><PortfolioPage baseUrl={preferences.baseUrl} /></ErrorBoundary>} />
          <Route path="graph" element={<ErrorBoundary><GraphPage baseUrl={preferences.baseUrl} /></ErrorBoundary>} />
          <Route path="alerts-health" element={<ErrorBoundary><AlertsHealthPage baseUrl={preferences.baseUrl} defaultSeverity={preferences.filterDefaults.severity} /></ErrorBoundary>} />
          <Route
            path="settings"
            element={
              <ErrorBoundary>
                <SettingsPage
                  baseUrl={preferences.baseUrl}
                  theme={preferences.theme}
                  compactLayout={preferences.compactLayout}
                  defaultSeverity={preferences.filterDefaults.severity}
                  onSaveBaseUrl={saveBaseUrl}
                  onSaveUiPreferences={saveUiPreferences}
                  onSaveToken={(token) => tokenStorage.save({ token })}
                />
              </ErrorBoundary>
            }
          />
        </Route>
      </Routes>
    </OperatorConsoleProvider>
  );
}
