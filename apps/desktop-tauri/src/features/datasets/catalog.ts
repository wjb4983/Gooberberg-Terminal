import type { DatasetPreset } from './forms';

export interface QuickStartTemplate {
  id: string;
  label: string;
  description: string;
  datasetPresetId: DatasetPreset['id'];
  trainingPreset: 'safe' | 'balanced' | 'aggressive';
}

export const DATASET_PRESETS: DatasetPreset[] = [
  {
    id: 'sp500_default', label: 'S&P 500 (default)', universe_type: 'stocks', symbolStrategy: 'saved_universe', savedUniverseId: 'sp500', defaultTimeframe: '1d',
    defaultDateWindow: { mode: 'fixed_range', startDate: '2024-01-01', endDate: '2024-12-31', label: 'Calendar year 2024 baseline' },
    notes: 'Balanced baseline for broad US large-cap coverage.', estimatedCoverage: '~500 tickers', estimatedSymbolCount: 500, roughSizeCostHint: 'Moderate ingestion/runtime cost; good starter benchmark.',
  },
  {
    id: 'sp100_liquid_daily', label: 'S&P 100 liquid leaders', universe_type: 'stocks', symbolStrategy: 'saved_universe', savedUniverseId: 'sp100', defaultTimeframe: '1d',
    defaultDateWindow: { mode: 'rolling_window', startDate: '2024-07-01', endDate: '2024-12-31', label: 'Recent 6-month large-cap window' },
    notes: 'Large-cap liquidity-first setup for robust daily experiments.', estimatedCoverage: '~100 tickers', estimatedSymbolCount: 100, roughSizeCostHint: 'Low-to-moderate ingestion cost; quick model iteration cycles.',
  },
  {
    id: 'all_stocks_etfs_us', label: 'All US stocks + ETFs', universe_type: 'stocks', symbolStrategy: 'saved_universe', savedUniverseId: 'all_stocks_etfs_us', defaultTimeframe: '15m',
    defaultDateWindow: { mode: 'rolling_window', startDate: '2024-09-01', endDate: '2024-12-31', label: 'Recent intraday research window' },
    notes: 'Max-coverage preset for discovery and cross-sectional experiments.', estimatedCoverage: 'Thousands of symbols', estimatedSymbolCount: 8000, roughSizeCostHint: 'High ingestion/runtime cost; expect longer queue and compute time.',
  },
  {
    id: 'top_liquid_etfs', label: 'Top liquid ETFs', universe_type: 'stocks', symbolStrategy: 'saved_universe', savedUniverseId: 'top_liquid_etfs', defaultTimeframe: '1h',
    defaultDateWindow: { mode: 'rolling_window', startDate: '2024-07-01', endDate: '2024-12-31', label: 'Recent liquid ETF window' },
    notes: 'Liquidity-focused for lower slippage assumptions and tighter spread behavior.', estimatedCoverage: '~25-150 ETFs', estimatedSymbolCount: 100, roughSizeCostHint: 'Lower-to-moderate cost; good for faster iteration loops.',
  },
  {
    id: 'sector_etfs_rotational', label: 'Sector ETF rotation basket', universe_type: 'stocks', symbolStrategy: 'saved_universe', savedUniverseId: 'sector_etfs_us', defaultTimeframe: '1h',
    defaultDateWindow: { mode: 'rolling_window', startDate: '2024-04-01', endDate: '2024-12-31', label: '9-month sector rotation window' },
    notes: 'Sector tilt signals and rotation studies.', estimatedCoverage: '~11-30 ETFs', estimatedSymbolCount: 20, roughSizeCostHint: 'Low cost and fast ingestion; ideal for rapid hypothesis testing.',
  },
  {
    id: 'us_equities_small_mid_intraday', label: 'US SMID intraday tier', universe_type: 'stocks', symbolStrategy: 'saved_universe', savedUniverseId: 'us_smid_liquid', defaultTimeframe: '15m',
    defaultDateWindow: { mode: 'rolling_window', startDate: '2024-10-01', endDate: '2024-12-31', label: 'Quarterly intraday small/mid-cap sample' },
    notes: 'Higher dispersion universe for momentum and mean-reversion research.', estimatedCoverage: '~400-1200 symbols', estimatedSymbolCount: 700, roughSizeCostHint: 'Moderate-to-high cost; expect longer feature materialization.',
  },
  {
    id: 'options_top_underlyings', label: 'Options on top underlyings', universe_type: 'options', symbolStrategy: 'saved_universe', savedUniverseId: 'options_top_underlyings', defaultTimeframe: '1h',
    defaultDateWindow: { mode: 'rolling_window', startDate: '2024-11-01', endDate: '2024-12-31', label: 'Recent options-focused research window' },
    notes: 'Use only if options ingest is enabled for your environment.', estimatedCoverage: '~25-75 underlyings', estimatedSymbolCount: 50, roughSizeCostHint: 'Potentially high due to chain breadth; validate provider quotas before launch.',
  },
  {
    id: 'custom_manual', label: 'Custom manual symbols', universe_type: 'stocks', symbolStrategy: 'manual_symbols', defaultTimeframe: '1d',
    defaultDateWindow: { mode: 'fixed_range', startDate: '2024-01-01', endDate: '2024-12-31', label: 'Manual baseline (editable)' },
    notes: 'Uses current manual input flow and preserves backward-compatible behavior.', estimatedCoverage: 'User-defined', estimatedSymbolCount: null, roughSizeCostHint: 'Cost depends on symbol count and timeframe.',
  },
];

export const QUICK_START_TEMPLATES: QuickStartTemplate[] = [
  {
    id: 'large_cap_equities_daily_baseline',
    label: 'Large-cap equities daily baseline',
    description: 'S&P 500 daily dataset baseline with balanced training defaults.',
    datasetPresetId: 'sp500_default',
    trainingPreset: 'balanced',
  },
  {
    id: 'sp100_fast_iteration_baseline',
    label: 'S&P 100 fast iteration baseline',
    description: 'Focused large-cap universe for shorter ingestion and faster reruns.',
    datasetPresetId: 'sp100_liquid_daily',
    trainingPreset: 'safe',
  },
  {
    id: 'sector_rotation_starter',
    label: 'Sector rotation starter',
    description: 'Sector ETF research starter tuned for regime and rotation studies.',
    datasetPresetId: 'sector_etfs_rotational',
    trainingPreset: 'aggressive',
  },
  {
    id: 'smid_intraday_research_starter',
    label: 'SMID intraday research starter',
    description: 'SMID tier preset for broader alpha discovery with intraday cadence.',
    datasetPresetId: 'us_equities_small_mid_intraday',
    trainingPreset: 'balanced',
  },
  {
    id: 'market_wide_intraday_research_starter',
    label: 'Market-wide intraday starter',
    description: 'Broad US equities + ETFs preset for widest coverage experiments.',
    datasetPresetId: 'all_stocks_etfs_us',
    trainingPreset: 'safe',
  },
  {
    id: 'options_research_starter',
    label: 'Options research starter',
    description: 'Options-focused starter when options ingestion is supported.',
    datasetPresetId: 'options_top_underlyings',
    trainingPreset: 'safe',
  },
];
