import type {
  CreateJobRequest,
  CreateJobResponse,
  HealthResponse,
  JobStatusResponse,
  ServiceHealth,
} from '@gb/schemas';

export interface ApiClientOptions {
  baseHttpUrl: string;
  apiPrefix?: string;
  websocketUrl?: string;
  fetchImpl?: typeof fetch;
}

export interface ConnectWebSocketOptions {
  onMessage?: (event: MessageEvent<string>) => void;
  onOpen?: (event: Event) => void;
  onError?: (event: Event) => void;
  onClose?: (event: CloseEvent) => void;
}

export class GbApiClient {
  private readonly fetchImpl: typeof fetch;
  private readonly baseHttpUrl: string;
  private readonly apiPrefix: string;
  private readonly websocketUrl?: string;

  constructor(options: ApiClientOptions) {
    this.fetchImpl = options.fetchImpl ?? fetch;
    this.baseHttpUrl = options.baseHttpUrl.replace(/\/$/, '');
    this.apiPrefix = options.apiPrefix ?? '/api/v1';
    this.websocketUrl = options.websocketUrl;
  }

  async getHealth(): Promise<HealthResponse> {
    const payload = await this.requestJson<unknown>(`${this.apiPrefix}/health`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    });

    return parseHealthResponse(payload);
  }

  async createJob(request: CreateJobRequest): Promise<CreateJobResponse> {
    const payload = await this.requestJson<unknown>(`${this.apiPrefix}/jobs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({
        job_type: request.jobType,
        payload: request.payload,
      }),
    });

    return parseCreateJobResponse(payload);
  }

  async getJob(jobId: string): Promise<JobStatusResponse> {
    const payload = await this.requestJson<unknown>(`${this.apiPrefix}/jobs/${encodeURIComponent(jobId)}`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    });

    return parseJobStatusResponse(payload);
  }

  connectWebSocket(options: ConnectWebSocketOptions = {}): WebSocket {
    const wsUrl = this.resolveWebSocketUrl();
    const socket = new WebSocket(wsUrl);

    if (options.onMessage) socket.addEventListener('message', options.onMessage);
    if (options.onOpen) socket.addEventListener('open', options.onOpen);
    if (options.onError) socket.addEventListener('error', options.onError);
    if (options.onClose) socket.addEventListener('close', options.onClose);

    return socket;
  }

  private async requestJson<T>(path: string, init: RequestInit): Promise<T> {
    const response = await this.fetchImpl(`${this.baseHttpUrl}${path}`, init);
    if (!response.ok) {
      throw new Error(`Request failed for ${path} with status ${response.status}`);
    }

    return (await response.json()) as T;
  }

  private resolveWebSocketUrl(): string {
    if (this.websocketUrl) {
      return this.websocketUrl;
    }

    const normalized = this.baseHttpUrl.replace(/^http/, 'ws');
    return `${normalized}/ws`;
  }
}

export function parseServiceHealth(payload: unknown): ServiceHealth | null {
  if (!isRecord(payload)) return null;

  if (typeof payload.service !== 'string') return null;
  if (payload.status !== 'healthy' && payload.status !== 'degraded' && payload.status !== 'unhealthy') return null;
  if (typeof payload.checkedAtIso !== 'string') return null;

  return {
    service: payload.service,
    status: payload.status,
    checkedAtIso: payload.checkedAtIso,
    message: typeof payload.message === 'string' ? payload.message : undefined,
  }; 
}

function parseHealthResponse(payload: unknown): HealthResponse {
  if (!isRecord(payload)) throw new Error('Health payload must be an object.');
  if (typeof payload.service !== 'string') throw new Error('Health payload service is malformed.');
  if (typeof payload.status !== 'string') throw new Error('Health payload status is malformed.');
  if (typeof payload.version !== 'string') throw new Error('Health payload version is malformed.');

  return {
    service: payload.service,
    status: payload.status,
    version: payload.version,
    postgres: payload.postgres as HealthResponse['postgres'],
    redis: payload.redis as HealthResponse['redis'],
  };
}

function parseCreateJobResponse(payload: unknown): CreateJobResponse {
  if (!isRecord(payload)) throw new Error('Create job payload must be an object.');
  if (typeof payload.id !== 'string') throw new Error('Create job payload id is malformed.');
  if (typeof payload.job_type !== 'string') throw new Error('Create job payload job_type is malformed.');
  if (typeof payload.status !== 'string') throw new Error('Create job payload status is malformed.');
  if (!isRecord(payload.payload)) throw new Error('Create job payload payload is malformed.');
  if (typeof payload.accepted_at !== 'string') throw new Error('Create job payload accepted_at is malformed.');

  return {
    id: payload.id,
    jobType: payload.job_type,
    status: payload.status as CreateJobResponse['status'],
    payload: payload.payload,
    acceptedAtIso: payload.accepted_at,
  };
}

function parseJobStatusResponse(payload: unknown): JobStatusResponse {
  if (!isRecord(payload)) throw new Error('Job status payload must be an object.');
  if (typeof payload.id !== 'string') throw new Error('Job status payload id is malformed.');
  if (typeof payload.status !== 'string') throw new Error('Job status payload status is malformed.');
  if (typeof payload.detail !== 'string') throw new Error('Job status payload detail is malformed.');

  return {
    id: payload.id,
    status: payload.status as JobStatusResponse['status'],
    detail: payload.detail,
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}
