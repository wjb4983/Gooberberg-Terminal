import { Navigate, Route, Routes } from 'react-router-dom';

import { AppShell } from './layout/AppShell';
import { StrategiesPage } from './pages/StrategiesPage';
import { DashboardPage } from './pages/DashboardPage';
import { JobsPage } from './pages/JobsPage';
import { SettingsPage } from './pages/SettingsPage';
import { AlertsHealthPage } from './pages/AlertsHealthPage';
import { ModelMonitorPage } from './pages/ModelMonitorPage';
import { PortfolioPage } from './pages/PortfolioPage';
import { DataCachePage } from './pages/DataCachePage';
import { loadPreferences, savePreferences } from './settings/preferences';
import { createTokenStorage } from './settings/tokenStorage';
import { useCallback, useMemo, useState } from 'react';
import { OperatorConsoleProvider } from './context/OperatorConsoleContext';
import type { ThemePreference } from './types/api';
import { ErrorBoundary } from './components/ErrorBoundary';
import { ParameterizationPage } from './pages/ParameterizationPage';
import { TestingPage } from './pages/TestingPage';
import { JobDetailPage } from './pages/JobDetailPage';
import { ParameterSweepsPage } from './pages/ParameterSweepsPage';
import { TrainingRunsPage } from './pages/TrainingRunsPage';
import { BacktestsPage } from './pages/BacktestsPage';
import { BuildingModelsPage } from './pages/BuildingModelsPage';
import { ModelDeploymentsPage } from './pages/ModelDeploymentsPage';
import { ModelCatalogPage } from './pages/ModelCatalogPage';
import { StrategyWorkbenchPage } from './pages/StrategyWorkbenchPage';
import { DatasetCreationPage } from './pages/DatasetCreationPage';

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
  const saveToken = useCallback((token: string) => tokenStorage.save({ token }), [tokenStorage]);
  const loadToken = useCallback(() => tokenStorage.getToken(), [tokenStorage]);
  const clearToken = useCallback(() => tokenStorage.clear(), [tokenStorage]);

  const saveBaseUrl = (nextBaseUrl: string): void => {
    setPreferences((previous) => {
      const next = { ...previous, baseUrl: nextBaseUrl };
      savePreferences(next);
      return next;
    });
  };

  const saveUiPreferences = (nextTheme: ThemePreference, compactLayout: boolean, defaultSeverity: 'all' | 'info' | 'warning' | 'critical'): void => {
    setPreferences((previous) => {
      const next = {
        ...previous,
        theme: nextTheme,
        compactLayout,
        filterDefaults: { severity: defaultSeverity },
      };
      savePreferences(next);
      return next;
    });
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

          <Route path="models">
            <Route path="build" element={<ErrorBoundary><BuildingModelsPage baseUrl={preferences.baseUrl} /></ErrorBoundary>} />
            <Route path="train" element={<ErrorBoundary><TrainingRunsPage baseUrl={preferences.baseUrl} /></ErrorBoundary>} />
            <Route path="backtest" element={<ErrorBoundary><BacktestsPage baseUrl={preferences.baseUrl} /></ErrorBoundary>} />
            <Route path="deploy" element={<ErrorBoundary><ModelDeploymentsPage baseUrl={preferences.baseUrl} /></ErrorBoundary>} />
            <Route path="monitor" element={<ErrorBoundary><ModelMonitorPage baseUrl={preferences.baseUrl} defaultSeverity={preferences.filterDefaults.severity} /></ErrorBoundary>} />
            <Route index element={<Navigate to="build" replace />} />
          </Route>

          <Route path="model-catalog" element={<ErrorBoundary><ModelCatalogPage baseUrl={preferences.baseUrl} /></ErrorBoundary>} />
          <Route path="parameterization" element={<ErrorBoundary><ParameterizationPage baseUrl={preferences.baseUrl} /></ErrorBoundary>} />
          <Route path="datasets/create" element={<ErrorBoundary><DatasetCreationPage baseUrl={preferences.baseUrl} /></ErrorBoundary>} />
          <Route path="parameter-sweeps" element={<ErrorBoundary><ParameterSweepsPage baseUrl={preferences.baseUrl} /></ErrorBoundary>} />
          <Route path="testing" element={<ErrorBoundary><TestingPage baseUrl={preferences.baseUrl} /></ErrorBoundary>} />

          {/* Legacy aliases (kept for backward compatibility) */}
          <Route path="training-runs" element={<Navigate to="/models/train" replace />} />
          <Route path="backtests" element={<Navigate to="/models/backtest" replace />} />
          <Route path="model-deployments" element={<Navigate to="/models/deploy" replace />} />
          <Route path="graphing" element={<Navigate to="/models/monitor" replace />} />
          <Route path="building-models" element={<Navigate to="/models/build" replace />} />
          <Route path="full-on-backtesting" element={<Navigate to="/models/backtest" replace />} />
          <Route path="graph" element={<Navigate to="/models/monitor" replace />} />

          <Route path="data-cache" element={<ErrorBoundary><DataCachePage baseUrl={preferences.baseUrl} /></ErrorBoundary>} />
          <Route path="strategies" element={<ErrorBoundary><StrategiesPage baseUrl={preferences.baseUrl} /></ErrorBoundary>} />
          <Route path="strategies/workbench" element={<ErrorBoundary><StrategyWorkbenchPage baseUrl={preferences.baseUrl} /></ErrorBoundary>} />
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
                  onSaveToken={saveToken}
                  onLoadToken={loadToken}
                  onClearToken={clearToken}
                />
              </ErrorBoundary>
            }
          />
        </Route>
      </Routes>
    </OperatorConsoleProvider>
  );
}
