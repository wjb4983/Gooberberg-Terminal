import type { ApiPreferences } from '../types/api';

const PREFERENCES_KEY = 'desktop-tauri.preferences.v1';

const defaultPreferences: ApiPreferences = {
  baseUrl: 'http://localhost:8000',
};

export function loadPreferences(): ApiPreferences {
  try {
    const raw = localStorage.getItem(PREFERENCES_KEY);
    if (!raw) {
      return defaultPreferences;
    }

    const parsed = JSON.parse(raw) as Partial<ApiPreferences>;

    if (typeof parsed.baseUrl !== 'string' || parsed.baseUrl.length === 0) {
      return defaultPreferences;
    }

    return { baseUrl: parsed.baseUrl };
  } catch {
    return defaultPreferences;
  }
}

export function savePreferences(preferences: ApiPreferences): void {
  localStorage.setItem(PREFERENCES_KEY, JSON.stringify(preferences));
}
