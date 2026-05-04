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
}

export interface StrategyTrainingLiveStatus {
  run_id: string;
  job_id: string;
  status: TrainingRunState;
  detail: string;
  updated_at: string;
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

