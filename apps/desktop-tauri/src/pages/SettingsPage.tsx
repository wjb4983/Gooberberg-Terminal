import { useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import type { ThemePreference } from '../types/api';
import { normalizeApiBaseUrl } from '../settings/preferences';

interface SettingsPageProps {
  baseUrl: string;
  theme: ThemePreference;
  compactLayout: boolean;
  defaultSeverity: 'all' | 'info' | 'warning' | 'critical';
  onSaveBaseUrl: (nextBaseUrl: string) => void;
  onSaveUiPreferences: (
    theme: ThemePreference,
    compactLayout: boolean,
    defaultSeverity: 'all' | 'info' | 'warning' | 'critical',
  ) => void;
  onSaveToken: (token: string) => Promise<void>;
  onLoadToken: () => Promise<string>;
  onClearToken: () => Promise<void>;
}

async function probeSavedConnection(baseUrl: string, token: string): Promise<string> {
  const normalizedBaseUrl = normalizeApiBaseUrl(baseUrl);
  const headers = { Accept: 'application/json' };
  const [liveness, health, queue, protectedRoute] = await Promise.allSettled([
    fetch(`${normalizedBaseUrl}/healthz`, { headers }),
    fetch(`${normalizedBaseUrl}/api/v1/health`, { headers }),
    fetch(`${normalizedBaseUrl}/api/v1/health/queue`, { headers }),
    fetch(`${normalizedBaseUrl}/api/v1/models/deployments`, {
      headers: {
        ...headers,
        ...(token.trim() ? { Authorization: `Bearer ${token.trim()}` } : {}),
      },
    }),
  ]);

  const isOk = (result: PromiseSettledResult<Response>): boolean =>
    result.status === 'fulfilled' && result.value.ok;
  const protectedOk = protectedRoute.status === 'fulfilled' && protectedRoute.value.ok;
  const protectedStatus =
    protectedRoute.status === 'fulfilled' ? protectedRoute.value.status : 'request failed';
  const protectedDetail =
    protectedRoute.status === 'rejected' && protectedRoute.reason instanceof Error
      ? `; ${protectedRoute.reason.message}`
      : '';

  return [
    `Settings saved.`,
    `/healthz ${isOk(liveness) ? 'ok' : 'failed'}.`,
    `/api/v1/health ${isOk(health) ? 'ok' : 'failed'}.`,
    `Queue ${isOk(queue) ? 'reachable' : 'failed'}.`,
    `Token ${protectedOk ? 'accepted' : `not accepted (${protectedStatus}${protectedDetail})`}.`,
  ].join(' ');
}

export function SettingsPage({
  baseUrl,
  theme,
  compactLayout,
  defaultSeverity,
  onSaveBaseUrl,
  onSaveUiPreferences,
  onSaveToken,
  onLoadToken,
  onClearToken,
}: SettingsPageProps): JSX.Element {
  const [baseUrlInput, setBaseUrlInput] = useState(baseUrl);
  const [tokenInput, setTokenInput] = useState('');
  const [themeInput, setThemeInput] = useState(theme);
  const [compactLayoutInput, setCompactLayoutInput] = useState(compactLayout);
  const [defaultSeverityInput, setDefaultSeverityInput] = useState(defaultSeverity);
  const [status, setStatus] = useState<string | null>(null);
  const queryClient = useQueryClient();

  useEffect(() => {
    setBaseUrlInput(baseUrl);
    setThemeInput(theme);
    setCompactLayoutInput(compactLayout);
    setDefaultSeverityInput(defaultSeverity);
  }, [baseUrl, compactLayout, defaultSeverity, theme]);

  useEffect(() => {
    let cancelled = false;
    onLoadToken()
      .then((token) => {
        if (!cancelled) {
          setTokenInput(token);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setTokenInput('');
        }
      });
    return () => {
      cancelled = true;
    };
  }, [onLoadToken]);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();

    const nextBaseUrl = normalizeApiBaseUrl(baseUrlInput);
    onSaveBaseUrl(nextBaseUrl);
    onSaveUiPreferences(themeInput, compactLayoutInput, defaultSeverityInput);
    if (tokenInput.trim()) {
      await onSaveToken(tokenInput);
    }
    setStatus('Settings saved. Checking connection...');
    setStatus(await probeSavedConnection(nextBaseUrl, tokenInput));
    await queryClient.invalidateQueries({ queryKey: ['system'] });
  };

  const handleClearToken = async (): Promise<void> => {
    await onClearToken();
    setTokenInput('');
    setStatus(
      'Stored API token cleared. Re-authentication is required before protected API calls can succeed.',
    );
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

        <label htmlFor="api-token">API Token</label>
        <input
          id="api-token"
          type="password"
          value={tokenInput}
          onChange={(event) => setTokenInput(event.target.value)}
          placeholder="Stored in OS keychain via Tauri secure storage command"
        />

        <button type="submit">Save Settings</button>
        <button type="button" onClick={() => void handleClearToken()}>
          Clear Stored Token
        </button>
      </form>

      {status && <p>{status}</p>}
      <p>
        Preferences are persisted locally. Tauri builds use OS credential storage for the API token;
        browser dev mode stores it in localStorage.
      </p>
      <p>
        If a token expires or is revoked, the API returns 401 and you must set a new token here to
        re-authenticate.
      </p>
    </section>
  );
}
