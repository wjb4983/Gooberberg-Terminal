export type ThemePreference = 'dark' | 'light';

export interface UiPreferences {
  theme: ThemePreference;
  compactLayout: boolean;
  filterDefaults: {
    severity: 'all' | 'info' | 'warning' | 'critical';
  };
}

export interface ApiPreferences extends UiPreferences {
  baseUrl: string;
}

export interface ApiCredentials {
  token: string;
}
