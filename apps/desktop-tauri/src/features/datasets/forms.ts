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
  id:
    | 'sp500_default'
    | 'sp100_liquid_daily'
    | 'all_stocks_etfs_us'
    | 'top_liquid_etfs'
    | 'sector_etfs_rotational'
    | 'us_equities_small_mid_intraday'
    | 'options_top_underlyings'
    | 'custom_manual';
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
  estimatedSymbolCount: number | null;
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

