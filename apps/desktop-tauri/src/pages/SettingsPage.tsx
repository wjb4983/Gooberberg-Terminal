import { useState } from 'react';
import type { ThemePreference } from '../types/api';

interface SettingsPageProps {
  baseUrl: string;
  theme: ThemePreference;
  compactLayout: boolean;
  defaultSeverity: 'all' | 'info' | 'warning' | 'critical';
  onSaveBaseUrl: (nextBaseUrl: string) => void;
  onSaveUiPreferences: (theme: ThemePreference, compactLayout: boolean, defaultSeverity: 'all' | 'info' | 'warning' | 'critical') => void;
  onSaveToken: (token: string) => Promise<void>;
}

export function SettingsPage({
  baseUrl,
  theme,
  compactLayout,
  defaultSeverity,
  onSaveBaseUrl,
  onSaveUiPreferences,
  onSaveToken,
}: SettingsPageProps): JSX.Element {
  const [baseUrlInput, setBaseUrlInput] = useState(baseUrl);
  const [tokenInput, setTokenInput] = useState('');
  const [themeInput, setThemeInput] = useState(theme);
  const [compactLayoutInput, setCompactLayoutInput] = useState(compactLayout);
  const [defaultSeverityInput, setDefaultSeverityInput] = useState(defaultSeverity);
  const [status, setStatus] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();

    onSaveBaseUrl(baseUrlInput);
    onSaveUiPreferences(themeInput, compactLayoutInput, defaultSeverityInput);
    await onSaveToken(tokenInput);
    setTokenInput('');
    setStatus('Settings saved. API token stored in OS secure credential storage.');
  };

  return (
    <section>
      <h2>Settings</h2>
      <form className="settings-form" onSubmit={(event) => void handleSubmit(event)}>
        <label htmlFor="api-base-url">API Base URL</label>
        <input
          id="api-base-url"
          type="url"
          value={baseUrlInput}
          onChange={(event) => setBaseUrlInput(event.target.value)}
          required
        />

        <label htmlFor="theme">Theme</label>
        <select id="theme" value={themeInput} onChange={(event) => setThemeInput(event.target.value as ThemePreference)}>
          <option value="dark">Dark</option>
          <option value="light">Light</option>
        </select>

        <label>
          <input type="checkbox" checked={compactLayoutInput} onChange={(event) => setCompactLayoutInput(event.target.checked)} />
          Compact layout
        </label>

        <label htmlFor="default-severity">Default alert severity filter</label>
        <select
          id="default-severity"
          value={defaultSeverityInput}
          onChange={(event) => setDefaultSeverityInput(event.target.value as 'all' | 'info' | 'warning' | 'critical')}
        >
          <option value="all">All</option>
          <option value="info">Info</option>
          <option value="warning">Warning</option>
          <option value="critical">Critical</option>
        </select>

        <label htmlFor="api-token">API Token</label>
        <input
          id="api-token"
          type="password"
          value={tokenInput}
          onChange={(event) => setTokenInput(event.target.value)}
          placeholder="Stored in OS keychain via Tauri secure storage command"
        />

        <button type="submit">Save Settings</button>
      </form>

      {status && <p>{status}</p>}
      <p>Non-sensitive preferences are persisted locally. Sensitive credentials are not persisted in localStorage.</p>
    </section>
  );
}
