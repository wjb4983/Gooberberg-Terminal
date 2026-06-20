import type { ApiPreferences } from '../types/api';

const PREFERENCES_KEY = 'desktop-tauri.preferences.v2';

export const DEFAULT_API_BASE_URL = normalizeApiBaseUrl(
  import.meta.env.VITE_GB_API_BASE_URL ?? 'http://127.0.0.1:8000',
);

export function normalizeApiBaseUrl(value: string): string {
  const trimmed = value.trim().replace(/\/$/, '');
  try {
    const parsed = new URL(trimmed);
    if (parsed.hostname === 'localhost') {
      parsed.hostname = '127.0.0.1';
    }
    return parsed.toString().replace(/\/$/, '');
  } catch {
    return trimmed;
  }
}

const defaultPreferences: ApiPreferences = {
  baseUrl: DEFAULT_API_BASE_URL,
  theme: 'dark',
  compactLayout: false,
  filterDefaults: {
    severity: 'all',
  },
};

export function loadPreferences(): ApiPreferences {
  try {
    const raw = localStorage.getItem(PREFERENCES_KEY);
    if (!raw) {
      return defaultPreferences;
    }

    const parsed = JSON.parse(raw) as Partial<ApiPreferences>;

    return {
      baseUrl: defaultPreferences.baseUrl,
      theme: parsed.theme === 'light' ? 'light' : 'dark',
      compactLayout: Boolean(parsed.compactLayout),
      filterDefaults: {
        severity:
          parsed.filterDefaults?.severity === 'info' ||
          parsed.filterDefaults?.severity === 'warning' ||
          parsed.filterDefaults?.severity === 'critical'
            ? parsed.filterDefaults.severity
            : 'all',
      },
    };
  } catch {
    return defaultPreferences;
  }
}

export function savePreferences(preferences: ApiPreferences): void {
  localStorage.setItem(
    PREFERENCES_KEY,
    JSON.stringify({
      ...preferences,
      baseUrl: defaultPreferences.baseUrl,
    }),
  );
}
