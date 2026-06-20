import { useEffect, useState } from 'react';
import type { ThemePreference } from '../types/api';

interface SettingsPageProps {
  theme: ThemePreference;
  compactLayout: boolean;
  defaultSeverity: 'all' | 'info' | 'warning' | 'critical';
  onSaveUiPreferences: (
    theme: ThemePreference,
    compactLayout: boolean,
    defaultSeverity: 'all' | 'info' | 'warning' | 'critical',
  ) => void;
}

export function SettingsPage({
  theme,
  compactLayout,
  defaultSeverity,
  onSaveUiPreferences,
}: SettingsPageProps): JSX.Element {
  const [themeInput, setThemeInput] = useState(theme);
  const [compactLayoutInput, setCompactLayoutInput] = useState(compactLayout);
  const [defaultSeverityInput, setDefaultSeverityInput] = useState(defaultSeverity);
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    setThemeInput(theme);
    setCompactLayoutInput(compactLayout);
    setDefaultSeverityInput(defaultSeverity);
  }, [compactLayout, defaultSeverity, theme]);

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>): void => {
    event.preventDefault();

    onSaveUiPreferences(themeInput, compactLayoutInput, defaultSeverityInput);
    setStatus('Preferences saved.');
  };

  return (
    <section>
      <h2>Settings</h2>
      <form className="settings-form" onSubmit={handleSubmit}>
        <label htmlFor="theme">Theme</label>
        <select
          id="theme"
          value={themeInput}
          onChange={(event) => setThemeInput(event.target.value as ThemePreference)}
        >
          <option value="dark">Dark</option>
          <option value="light">Light</option>
        </select>

        <label>
          <input
            type="checkbox"
            checked={compactLayoutInput}
            onChange={(event) => setCompactLayoutInput(event.target.checked)}
          />
          Compact layout
        </label>

        <label htmlFor="default-severity">Default alert severity filter</label>
        <select
          id="default-severity"
          value={defaultSeverityInput}
          onChange={(event) =>
            setDefaultSeverityInput(event.target.value as 'all' | 'info' | 'warning' | 'critical')
          }
        >
          <option value="all">All</option>
          <option value="info">Info</option>
          <option value="warning">Warning</option>
          <option value="critical">Critical</option>
        </select>

        <button type="submit">Save Settings</button>
      </form>

      {status && <p>{status}</p>}
      <p>Preferences are persisted locally on this device.</p>
    </section>
  );
}
