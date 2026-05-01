import { NavLink, Outlet } from 'react-router-dom';
import type { ThemePreference } from '../types/api';
import { SystemStatusBar } from '../components/SystemStatusBar';

const navGroups = [
  {
    label: 'Model Lifecycle',
    items: [
      { label: 'Build', to: '/models/build' },
      { label: 'Train', to: '/models/train' },
      { label: 'Backtest', to: '/models/backtest' },
      { label: 'Deploy', to: '/models/deploy' },
      { label: 'Monitor', to: '/models/monitor' },
    ],
  },
  {
    label: 'Operations',
    items: [
      { label: 'Dashboard', to: '/' },
      { label: 'Jobs', to: '/jobs' },
      { label: 'Data Cache', to: '/data-cache' },
      { label: 'Strategies', to: '/strategies' },
      { label: 'Portfolio', to: '/portfolio' },
      { label: 'Alerts/Health', to: '/alerts-health' },
      { label: 'Graphing', to: '/graphing' },
      { label: 'Settings', to: '/settings' },
    ],
  },
];

interface AppShellProps {
  baseUrl: string;
  wsStatus: string;
  theme: ThemePreference;
  compactLayout: boolean;
  toasts: Array<{ id: number; message: string; tone: 'warning' | 'critical' }>;
}

export function AppShell({ baseUrl, wsStatus, theme, compactLayout, toasts }: AppShellProps): JSX.Element {
  return (
    <div className={`app-shell theme-${theme} ${compactLayout ? 'compact-layout' : ''}`}>
      <aside className="sidebar">
        <h1>Gooberberg</h1>
        <nav>
          {navGroups.map((group) => (
            <div key={group.label} style={{ marginBottom: '0.75rem' }}>
              <small className="muted">{group.label}</small>
              <ul>
                {group.items.map((item) => (
                  <li key={item.to}>
                    <NavLink to={item.to} className={({ isActive }) => (isActive ? 'active-link' : undefined)} end={item.to === '/'}>
                      {item.label}
                    </NavLink>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>
      </aside>
      <main className="content">
        <SystemStatusBar baseUrl={baseUrl} wsStatus={wsStatus} />
        <Outlet />
      </main>
      <div className="toast-layer">
        {toasts.map((toast) => (
          <div key={toast.id} className={`toast toast-${toast.tone}`}>{toast.message}</div>
        ))}
      </div>
    </div>
  );
}
