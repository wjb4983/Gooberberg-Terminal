import { Route, Routes } from 'react-router-dom';

import { AppShell } from './layout/AppShell';
import { StrategiesPage } from './pages/StrategiesPage';
import { DashboardPage } from './pages/DashboardPage';
import { JobsPage } from './pages/JobsPage';
import { SettingsPage } from './pages/SettingsPage';
import { AlertsHealthPage } from './pages/AlertsHealthPage';
import { PortfolioPage } from './pages/PortfolioPage';
import { DataCachePage } from './pages/DataCachePage';
import { loadPreferences, savePreferences } from './settings/preferences';
import { createTokenStorage } from './settings/tokenStorage';
import { useMemo, useState } from 'react';
import { OperatorConsoleProvider } from './context/OperatorConsoleContext';
import type { ThemePreference } from './types/api';
import { ErrorBoundary } from './components/ErrorBoundary';
import { BuildingModelsPage } from './pages/BuildingModelsPage';
import { ParameterizationPage } from './pages/ParameterizationPage';
import { TestingPage } from './pages/TestingPage';
import { BacktestingPage } from './pages/BacktestingPage';
import { GraphingPage } from './pages/GraphingPage';
import { JobDetailPage } from './pages/JobDetailPage';

interface ToastItem {
  id: number;
  message: string;
  tone: 'warning' | 'critical';
}

export function App(): JSX.Element {
  const [preferences, setPreferences] = useState(() => loadPreferences());
  const tokenStorage = useMemo(() => createTokenStorage(), []);
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
    <OperatorConsoleProvider value={{ reportApiStatus: () => undefined, reportWebSocketStatus: setWsStatus, pushToast }}>
      <Routes>
        <Route path="/" element={<AppShell baseUrl={preferences.baseUrl} wsStatus={wsStatus} toasts={toasts} theme={preferences.theme} compactLayout={preferences.compactLayout} />}>
          <Route index element={<ErrorBoundary><DashboardPage baseUrl={preferences.baseUrl} /></ErrorBoundary>} />
          <Route path="jobs" element={<ErrorBoundary><JobsPage baseUrl={preferences.baseUrl} /></ErrorBoundary>} />
          <Route path="jobs/:jobId" element={<ErrorBoundary><JobDetailPage baseUrl={preferences.baseUrl} /></ErrorBoundary>} />

          <Route path="building-models" element={<ErrorBoundary><BuildingModelsPage baseUrl={preferences.baseUrl} /></ErrorBoundary>} />
          <Route path="parameterization" element={<ErrorBoundary><ParameterizationPage baseUrl={preferences.baseUrl} /></ErrorBoundary>} />
          <Route path="testing" element={<ErrorBoundary><TestingPage baseUrl={preferences.baseUrl} /></ErrorBoundary>} />
          <Route path="full-on-backtesting" element={<ErrorBoundary><BacktestingPage baseUrl={preferences.baseUrl} /></ErrorBoundary>} />
          <Route path="graphing" element={<ErrorBoundary><GraphingPage baseUrl={preferences.baseUrl} /></ErrorBoundary>} />

          <Route path="models" element={<ErrorBoundary><BuildingModelsPage baseUrl={preferences.baseUrl} /></ErrorBoundary>} />
          <Route path="training-runs" element={<ErrorBoundary><TestingPage baseUrl={preferences.baseUrl} /></ErrorBoundary>} />
          <Route path="parameter-sweeps" element={<ErrorBoundary><ParameterizationPage baseUrl={preferences.baseUrl} /></ErrorBoundary>} />
          <Route path="backtests" element={<ErrorBoundary><BacktestingPage baseUrl={preferences.baseUrl} /></ErrorBoundary>} />
          <Route path="graph" element={<ErrorBoundary><GraphingPage baseUrl={preferences.baseUrl} /></ErrorBoundary>} />

          <Route path="data-cache" element={<ErrorBoundary><DataCachePage baseUrl={preferences.baseUrl} /></ErrorBoundary>} />
          <Route path="strategies" element={<ErrorBoundary><StrategiesPage baseUrl={preferences.baseUrl} /></ErrorBoundary>} />
          <Route path="portfolio" element={<ErrorBoundary><PortfolioPage baseUrl={preferences.baseUrl} /></ErrorBoundary>} />
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
