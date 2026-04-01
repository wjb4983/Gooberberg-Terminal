import { NavLink, Outlet } from 'react-router-dom';

const navItems = [
  { label: 'Dashboard', to: '/' },
  { label: 'Jobs', to: '/jobs' },
  { label: 'Model Deployments', to: '/models' },
  { label: 'Strategies', to: '/strategies' },
  { label: 'Portfolio', to: '/portfolio' },
  { label: 'Graph', to: '/graph' },
  { label: 'Settings', to: '/settings' },
];

export function AppShell(): JSX.Element {
  return (
    <div className="app-shell">
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
        <Outlet />
      </main>
    </div>
  );
}
