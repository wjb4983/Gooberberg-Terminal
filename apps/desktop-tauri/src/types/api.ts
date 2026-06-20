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

export const TASK_TYPES = ['time_series_momentum', 'cross_sectional', 'volatility', 'regime_switching'] as const;
export type TaskType = (typeof TASK_TYPES)[number];

export const SUBTASK_TYPES = ['ranking', 'entry_signal', 'exit_signal', 'regime_state', 'other'] as const;
export type SubtaskType = (typeof SUBTASK_TYPES)[number];
