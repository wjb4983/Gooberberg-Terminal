export type HealthStatus = 'healthy' | 'degraded' | 'unhealthy';

export interface ServiceHealth {
  service: string;
  status: HealthStatus;
  checkedAtIso: string;
  message?: string;
}

export type JobStatus = 'queued' | 'running' | 'success' | 'failed' | 'accepted' | 'pending' | 'succeeded' | 'cancelled';

export interface Job {
  id: string;
  jobType: string;
  status: JobStatus;
  payload: Record<string, unknown>;
  acceptedAtIso: string;
}

export interface StrategyInstance {
  id: string;
  strategyKey: string;
  status: 'inactive' | 'active' | 'paused' | 'error';
  symbols: string[];
  startedAtIso?: string;
  updatedAtIso: string;
}

export interface PortfolioSnapshot {
  accountId: string;
  timestampIso: string;
  equity: number;
  cash: number;
  buyingPower: number;
  positions: Array<{
    symbol: string;
    quantity: number;
    averagePrice: number;
    marketPrice?: number;
  }>;
}

export interface ContractEnvelopeBase {
  version: string;
  emittedAtIso: string;
}

export interface AlertEvent extends ContractEnvelopeBase {
  type: 'alert';
  severity: 'info' | 'warning' | 'critical';
  source: string;
  message: string;
  metadata?: Record<string, unknown>;
}

export interface LogEvent extends ContractEnvelopeBase {
  type: 'log';
  level: 'debug' | 'info' | 'warning' | 'error';
  source: string;
  message: string;
  fields?: Record<string, unknown>;
}

export type EventEnvelope = AlertEvent | LogEvent;

export interface DependencyStatus {
  configured: boolean;
  reachable: boolean | null;
  detail: string;
}

export interface HealthResponse {
  service: string;
  status: string;
  version: string;
  postgres: DependencyStatus;
  redis: DependencyStatus;
}

export interface CreateJobRequest {
  jobType: string;
  payload: Record<string, unknown>;
}

export interface CreateJobResponse {
  id: string;
  jobType: string;
  status: JobStatus;
  payload: Record<string, unknown>;
  acceptedAtIso: string;
}

export interface JobStatusResponse {
  id: string;
  status: JobStatus;
  detail: string;
}

export type WebSocketTopic = 'jobs' | 'alerts' | 'logs' | 'portfolio' | 'risk';

export interface WebSocketEventEnvelope<TPayload = Record<string, unknown>> {
  event_id: string;
  seq: number;
  topic: WebSocketTopic;
  timestamp: string;
  payload: TPayload;
  version: string;
}

export interface JobLifecyclePayload {
  job_id: string;
  trace_id: string;
  status: JobStatus;
  detail: string;
  updated_at: string;
}
