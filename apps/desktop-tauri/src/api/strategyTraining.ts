import { requestJson } from './requestJson';

export type TrainingRunState = 'queued' | 'running' | 'completed' | 'failed';

export interface StrategyTrainingLaunchRequest {
  strategy_key: string;
  model_id: string;
  parameters: Record<string, unknown>;
}

export interface StrategyTrainingLaunchResponse {
  run_id: string;
  job_id: string;
  status: TrainingRunState;
  detail: string;
  created_at: string;
}

export interface StrategyTrainingModelSummary {
  id: string;
  label: string;
  family: string;
  created_at: string;
  sharpe?: number | null;
  max_drawdown?: number | null;
  latency_p95_ms?: number | null;
  readiness?: string | null;
  last_trained_at?: string | null;
}

export interface StrategyTrainingLiveStatus {
  run_id: string;
  job_id: string;
  status: TrainingRunState;
  detail: string;
  updated_at: string;
}

export interface StrategyServiceStatus {
  service: string;
  mode: 'paper' | 'live' | string;
  connected: boolean;
  status: string;
  detail: string;
  checked_at: string;
  endpoint?: string | null;
  upstream_http_status?: number | null;
  heartbeat_at?: string | null;
  heartbeat_age_seconds?: number | null;
  pnl?: number | null;
  exposure?: number | null;
}

export interface StrategyExternalServicesStatusResponse {
  paper: StrategyServiceStatus;
  live: StrategyServiceStatus;
}

export function listStrategyTrainingModels(baseUrl: string) {
  return requestJson<StrategyTrainingModelSummary[]>(baseUrl, '/api/v1/strategy/training/models');
}

export function launchStrategyTrainingRun(baseUrl: string, payload: StrategyTrainingLaunchRequest) {
  return requestJson<StrategyTrainingLaunchResponse>(baseUrl, '/api/v1/strategy/training/launch', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getStrategyTrainingLiveStatus(baseUrl: string, runId: string) {
  return requestJson<StrategyTrainingLiveStatus>(
    baseUrl,
    `/api/v1/strategy/training/runs/${encodeURIComponent(runId)}/live-status`,
  );
}

export function getStrategyExternalStatus(baseUrl: string) {
  return requestJson<StrategyExternalServicesStatusResponse>(baseUrl, '/api/v1/control-plane/services/external-status');
}
