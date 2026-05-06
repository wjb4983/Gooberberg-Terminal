export interface DatasetCreateForm {
  universeType: 'stocks' | 'options';
  symbolsCsv: string;
  savedUniverseId: string;
  startDate: string;
  endDate: string;
  targetResolution: ResolutionOption;
  fetchResolution: ResolutionOption;
  featurePackEnabled: boolean;
}

export const RESOLUTION_OPTIONS = ['1m', '5m', '15m', '1h', '1d'] as const;
export type ResolutionOption = (typeof RESOLUTION_OPTIONS)[number];

export interface DatasetPreset {
  id: 'sp500_default' | 'all_stocks_etfs_us' | 'top_liquid_etfs' | 'custom_manual';
  label: string;
  universe_type: DatasetCreateForm['universeType'];
  symbolStrategy: 'saved_universe' | 'manual_symbols';
  savedUniverseId?: string;
  defaultTimeframe: ResolutionOption;
  defaultDateWindow: {
    mode: 'fixed_range' | 'rolling_window';
    startDate: string;
    endDate: string;
    label: string;
  };
  notes?: string;
  estimatedCoverage: string;
  roughSizeCostHint: string;
}

export interface DatasetFormErrors {
  symbolsCsv?: string;
  savedUniverseId?: string;
  startDate?: string;
  endDate?: string;
  targetResolution?: string;
  fetchResolution?: string;
}

interface IngestResolutionPayload {
  timeframe: ResolutionOption;
  resolutions: ResolutionOption[];
}

export function normalizeIngestResolution(args: {
  targetResolution: string;
  fetchResolution?: string;
}): IngestResolutionPayload | null {
  const target = RESOLUTION_OPTIONS.find((value) => value === args.targetResolution.trim());
  if (!target) return null;
  const fetchResolutionCandidate = args.fetchResolution?.trim() ?? target;
  const fetchResolution = RESOLUTION_OPTIONS.find((value) => value === fetchResolutionCandidate);
  if (!fetchResolution) return null;
  return {
    timeframe: target,
    resolutions: [fetchResolution],
  };
}

export const DATASET_PRESETS: DatasetPreset[] = [
  {
    id: 'sp500_default', label: 'S&P 500 (default)', universe_type: 'stocks', symbolStrategy: 'saved_universe', savedUniverseId: 'sp500', defaultTimeframe: '1d',
    defaultDateWindow: { mode: 'fixed_range', startDate: '2024-01-01', endDate: '2024-12-31', label: 'Calendar year 2024 baseline' },
    notes: 'Balanced baseline for broad US large-cap coverage.', estimatedCoverage: '~500 tickers', roughSizeCostHint: 'Moderate ingestion/runtime cost; good starter benchmark.',
  },
  {
    id: 'all_stocks_etfs_us', label: 'All US stocks + ETFs', universe_type: 'stocks', symbolStrategy: 'saved_universe', savedUniverseId: 'all_stocks_etfs_us', defaultTimeframe: '15m',
    defaultDateWindow: { mode: 'rolling_window', startDate: '2024-09-01', endDate: '2024-12-31', label: 'Recent intraday research window' },
    notes: 'Max-coverage preset for discovery and cross-sectional experiments.', estimatedCoverage: 'Thousands of symbols', roughSizeCostHint: 'High ingestion/runtime cost; expect longer queue and compute time.',
  },
  {
    id: 'top_liquid_etfs', label: 'Top liquid ETFs', universe_type: 'stocks', symbolStrategy: 'saved_universe', savedUniverseId: 'top_liquid_etfs', defaultTimeframe: '1h',
    defaultDateWindow: { mode: 'rolling_window', startDate: '2024-07-01', endDate: '2024-12-31', label: 'Recent liquid ETF window' },
    notes: 'Liquidity-focused for lower slippage assumptions and tighter spread behavior.', estimatedCoverage: '~25-150 ETFs', roughSizeCostHint: 'Lower-to-moderate cost; good for faster iteration loops.',
  },
  {
    id: 'custom_manual', label: 'Custom manual symbols', universe_type: 'stocks', symbolStrategy: 'manual_symbols', defaultTimeframe: '1d',
    defaultDateWindow: { mode: 'fixed_range', startDate: '2024-01-01', endDate: '2024-12-31', label: 'Manual baseline (editable)' },
    notes: 'Uses current manual input flow and preserves backward-compatible behavior.', estimatedCoverage: 'User-defined', roughSizeCostHint: 'Cost depends on symbol count and timeframe.',
  },
];
