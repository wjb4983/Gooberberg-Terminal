import { NavLink, Outlet } from 'react-router-dom';
import type { ThemePreference } from '../types/api';

const navItems = [
  { label: 'Dashboard', to: '/' },
  { label: 'Jobs', to: '/jobs' },
  { label: 'Model Deployments', to: '/models' },
  { label: 'Strategies', to: '/strategies' },
  { label: 'Portfolio', to: '/portfolio' },
  { label: 'Graph', to: '/graph' },
  { label: 'Alerts/Health', to: '/alerts-health' },
  { label: 'Settings', to: '/settings' },
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
          <ul>
            {navItems.map((item) => (
              <li key={item.to}>
                <NavLink to={item.to} className={({ isActive }) => (isActive ? 'active-link' : undefined)} end={item.to === '/'}>
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
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
