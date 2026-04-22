import { NavLink, Outlet } from 'react-router-dom';
import type { ThemePreference } from '../types/api';

const navGroups = [
  {
    label: 'Workflows',
    items: [
      { label: 'Building Models', to: '/building-models' },
      { label: 'Parameterization', to: '/parameterization' },
      { label: 'Testing', to: '/testing' },
      { label: 'Full-on Backtesting', to: '/full-on-backtesting' },
      { label: 'Graphing', to: '/graphing' },
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
      { label: 'Settings', to: '/settings' },
    ],
  },
];

interface AppShellProps {
  apiStatus: 'connected' | 'degraded' | 'offline';
  wsStatus: string;
  theme: ThemePreference;
  compactLayout: boolean;
  toasts: Array<{ id: number; message: string; tone: 'warning' | 'critical' }>;
}

export function AppShell({ apiStatus, wsStatus, theme, compactLayout, toasts }: AppShellProps): JSX.Element {
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
        <div className="status-bar">
          <span>API: <strong>{apiStatus}</strong></span>
          <span>WebSocket: <strong>{wsStatus}</strong></span>
        </div>
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
