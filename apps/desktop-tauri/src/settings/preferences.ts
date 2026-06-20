import type { ApiPreferences } from '../types/api';

const PREFERENCES_KEY = 'desktop-tauri.preferences.v2';

const defaultPreferences: ApiPreferences = {
  baseUrl: 'http://127.0.0.1:8000',
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
      baseUrl: typeof parsed.baseUrl === 'string' && parsed.baseUrl.length > 0 ? parsed.baseUrl : defaultPreferences.baseUrl,
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
  localStorage.setItem(PREFERENCES_KEY, JSON.stringify(preferences));
}
