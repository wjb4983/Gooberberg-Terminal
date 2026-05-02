import { requestJson } from './requestJson';
import { type SubtaskType, type TaskType } from '../types/api';

export interface TrainingRunValidationResponse {
  normalized_payload: {
    model_config_id: string;
    dataset_id: string;
    task_type: TaskType;
    subtask_type: SubtaskType;
    parameters: Record<string, unknown>;
  };
  warnings: string[];
  errors: string[];
  compatible: boolean;
  valid: boolean;
}

export interface TrainingRunCompatibilityRequestPayload {
  model_config_id: string;
  dataset_id: string;
  task_type: TaskType;
  subtask_type: SubtaskType;
  parameters: Record<string, unknown>;
}

export interface TrainingRunPreflightAttempt {
  preflight: TrainingRunValidationResponse;
  skippedValidation: boolean;
}

function getHttpStatusFromError(error: unknown): number | null {
  if (!(error instanceof Error)) {
    return null;
  }
  const statusMatch = error.message.match(/status (\d{3})/i);
  if (!statusMatch) {
    return null;
  }
  const parsed = Number(statusMatch[1]);
  return Number.isFinite(parsed) ? parsed : null;
}

export function isTrainingValidationEndpointUnavailable(error: unknown): boolean {
  const status = getHttpStatusFromError(error);
  return status === 404 || status === 405 || status === 501;
}

export async function requestTrainingRunPreflight(
  baseUrl: string,
  payload: TrainingRunCompatibilityRequestPayload,
): Promise<TrainingRunValidationResponse> {
  try {
    return await requestJson<TrainingRunValidationResponse>(baseUrl, '/api/v1/training-runs/preflight', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  } catch (preflightError) {
    if (!isTrainingValidationEndpointUnavailable(preflightError)) {
      throw preflightError;
    }
  }

  return requestJson<TrainingRunValidationResponse>(baseUrl, '/api/v1/training-runs/compatibility', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function requestTrainingRunPreflightOrBypass(
  baseUrl: string,
  payload: TrainingRunCompatibilityRequestPayload,
): Promise<TrainingRunPreflightAttempt> {
  try {
    return {
      preflight: await requestTrainingRunPreflight(baseUrl, payload),
      skippedValidation: false,
    };
  } catch (validationError) {
    if (!isTrainingValidationEndpointUnavailable(validationError)) {
      throw validationError;
    }
  }

  return {
    preflight: {
      normalized_payload: {
        model_config_id: payload.model_config_id,
        dataset_id: payload.dataset_id.trim(),
        task_type: payload.task_type,
        subtask_type: payload.subtask_type,
        parameters: payload.parameters,
      },
      warnings: [],
      errors: [],
      compatible: true,
      valid: true,
    },
    skippedValidation: true,
  };
}
