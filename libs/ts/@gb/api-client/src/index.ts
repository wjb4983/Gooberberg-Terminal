import type {
  CreateJobRequest,
  CreateJobResponse,
  HealthResponse,
  JobLifecyclePayload,
  JobStatusResponse,
  ServiceHealth,
  WebSocketEventEnvelope,
  WebSocketTopic,
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

export interface ReconnectingSocketOptions {
  topics: WebSocketTopic[];
  onEvent: (event: WebSocketEventEnvelope) => void;
  minBackoffMs?: number;
  maxBackoffMs?: number;
  getResumeSeq?: () => number | undefined;
  onStatus?: (status: 'connecting' | 'connected' | 'reconnecting' | 'closed') => void;
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

  connectTopicWebSocket(options: ReconnectingSocketOptions): { close: () => void } {
    const minBackoffMs = options.minBackoffMs ?? 500;
    const maxBackoffMs = options.maxBackoffMs ?? 10_000;
    let attempts = 0;
    let closed = false;
    let socket: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

    const connect = (): void => {
      if (closed) return;
      options.onStatus?.(attempts > 0 ? 'reconnecting' : 'connecting');

      const wsUrl = this.withResumeSeq(this.resolveWebSocketUrl(), options.getResumeSeq?.());
      socket = new WebSocket(wsUrl);

      socket.addEventListener('open', () => {
        attempts = 0;
        options.onStatus?.('connected');
        socket?.send(JSON.stringify({ action: 'subscribe', topics: options.topics }));
      });

      socket.addEventListener('message', (event) => {
        if (typeof event.data !== 'string') return;
        const parsed = parseWebSocketEvent(event.data);
        if (parsed) options.onEvent(parsed);
      });

      socket.addEventListener('close', () => {
        if (closed) return;
        attempts += 1;
        const delay = Math.min(minBackoffMs * 2 ** (attempts - 1), maxBackoffMs);
        reconnectTimer = setTimeout(connect, delay);
      });
    };

    connect();

    return {
      close: () => {
        closed = true;
        if (reconnectTimer) clearTimeout(reconnectTimer);
        socket?.close();
        options.onStatus?.('closed');
      },
    };
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

  private withResumeSeq(url: string, lastSeq?: number): string {
    if (lastSeq === undefined) return url;
    const separator = url.includes('?') ? '&' : '?';
    return `${url}${separator}last_seq=${encodeURIComponent(String(lastSeq))}`;
  }
}

export function parseWebSocketEvent(raw: string): WebSocketEventEnvelope | null {
  let payload: unknown;
  try {
    payload = JSON.parse(raw);
  } catch {
    return null;
  }
  if (!isRecord(payload)) return null;
  if (typeof payload.event_id !== 'string') return null;
  if (typeof payload.seq !== 'number') return null;
  if (typeof payload.topic !== 'string') return null;
  if (typeof payload.timestamp !== 'string') return null;
  if (typeof payload.version !== 'string') return null;
  if (!isRecord(payload.payload)) return null;

  return {
    event_id: payload.event_id,
    seq: payload.seq,
    topic: payload.topic as WebSocketTopic,
    timestamp: payload.timestamp,
    payload: payload.payload,
    version: payload.version,
  };
}

export function parseJobLifecyclePayload(payload: unknown): JobLifecyclePayload | null {
  if (!isRecord(payload)) return null;
  if (typeof payload.job_id !== 'string') return null;
  if (typeof payload.trace_id !== 'string') return null;
  if (typeof payload.status !== 'string') return null;
  if (typeof payload.detail !== 'string') return null;
  if (typeof payload.updated_at !== 'string') return null;
  return {
    job_id: payload.job_id,
    trace_id: payload.trace_id,
    status: payload.status as JobLifecyclePayload['status'],
    detail: payload.detail,
    updated_at: payload.updated_at,
  };
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
