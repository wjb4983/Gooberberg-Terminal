import { useState } from 'react';

interface SettingsPageProps {
  baseUrl: string;
  onSaveBaseUrl: (nextBaseUrl: string) => void;
  onSaveToken: (token: string) => Promise<void>;
}

export function SettingsPage({ baseUrl, onSaveBaseUrl, onSaveToken }: SettingsPageProps): JSX.Element {
  const [baseUrlInput, setBaseUrlInput] = useState(baseUrl);
  const [tokenInput, setTokenInput] = useState('');
  const [status, setStatus] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();

    onSaveBaseUrl(baseUrlInput);
    await onSaveToken(tokenInput);
    setTokenInput('');
    setStatus('Settings saved. API token stored using secure storage integration point.');
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

        <label htmlFor="api-token">API Token</label>
        <input
          id="api-token"
          type="password"
          value={tokenInput}
          onChange={(event) => setTokenInput(event.target.value)}
          placeholder="Stored in OS keychain via Tauri command"
        />

        <button type="submit">Save Settings</button>
      </form>

      {status && <p>{status}</p>}
      <p>Non-sensitive preferences are persisted locally. Sensitive credentials are not persisted in localStorage.</p>
    </section>
  );
}
