import type {
  CreateJobRequest,
  CreateJobResponse,
  CreateModelDeploymentRequest,
  CreateStrategyInstanceRequest,
  GraphTopology,
  HealthResponse,
  JobLifecyclePayload,
  JobStatusResponse,
  ModelDeployment,
  ModelDeploymentActionResponse,
  ModelDeploymentEventPayload,
  ModelDeploymentStatus,
  PortfolioSnapshot,
  ServiceHealth,
  StrategyInstance,
  StrategyInstanceActionResponse,
  StrategyMode,
  StrategyInstanceStatus,
  WebSocketEventEnvelope,
  WebSocketTopic,
} from '@gb/schemas';
import { parseGraphTopology } from '@gb/schemas';

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


  async getPortfolioSnapshot(): Promise<PortfolioSnapshot> {
    const payload = await this.requestJson<unknown>(`${this.apiPrefix}/portfolio/snapshot`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    });

    return parsePortfolioSnapshot(payload);
  }

  async getGraphTopology(): Promise<GraphTopology> {
    const payload = await this.requestJson<unknown>(`${this.apiPrefix}/graph/topology`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    });

    return parseGraphTopology(payload);
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

  async listModelDeployments(): Promise<ModelDeployment[]> {
    const payload = await this.requestJson<unknown>(`${this.apiPrefix}/models/deployments`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    });

    return parseModelDeployments(payload);
  }

  async createModelDeployment(request: CreateModelDeploymentRequest): Promise<ModelDeployment> {
    const payload = await this.requestJson<unknown>(`${this.apiPrefix}/models/deployments`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({
        model_name: request.modelName,
        model_version: request.modelVersion,
        artifact_ref: request.artifactRef,
      }),
    });

    return parseModelDeployment(payload);
  }

  async activateModelDeployment(deploymentId: string): Promise<ModelDeploymentActionResponse> {
    const payload = await this.requestJson<unknown>(`${this.apiPrefix}/models/deployments/${encodeURIComponent(deploymentId)}/activate`, {
      method: 'POST',
      headers: { Accept: 'application/json' },
    });

    return parseModelDeploymentActionResponse(payload);
  }

  async deactivateModelDeployment(deploymentId: string): Promise<ModelDeploymentActionResponse> {
    const payload = await this.requestJson<unknown>(`${this.apiPrefix}/models/deployments/${encodeURIComponent(deploymentId)}/deactivate`, {
      method: 'POST',
      headers: { Accept: 'application/json' },
    });

    return parseModelDeploymentActionResponse(payload);
  }

  async listStrategyInstances(): Promise<StrategyInstance[]> {
    const payload = await this.requestJson<unknown>(`${this.apiPrefix}/strategies/instances`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    });

    return parseStrategyInstances(payload);
  }

  async createStrategyInstance(request: CreateStrategyInstanceRequest): Promise<StrategyInstance> {
    const payload = await this.requestJson<unknown>(`${this.apiPrefix}/strategies/instances`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({
        strategy_key: request.strategyKey,
        mode: request.mode,
        intent: request.intent ?? { params: {} },
      }),
    });

    return parseStrategyInstance(payload);
  }

  async startStrategyInstance(instanceId: string): Promise<StrategyInstanceActionResponse> {
    const payload = await this.requestJson<unknown>(`${this.apiPrefix}/strategies/instances/${encodeURIComponent(instanceId)}/start`, {
      method: 'POST',
      headers: { Accept: 'application/json' },
    });

    return parseStrategyInstanceActionResponse(payload);
  }

  async stopStrategyInstance(instanceId: string): Promise<StrategyInstanceActionResponse> {
    const payload = await this.requestJson<unknown>(`${this.apiPrefix}/strategies/instances/${encodeURIComponent(instanceId)}/stop`, {
      method: 'POST',
      headers: { Accept: 'application/json' },
    });

    return parseStrategyInstanceActionResponse(payload);
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

export function parseModelDeploymentPayload(payload: unknown): ModelDeploymentEventPayload | null {
  if (!isRecord(payload)) return null;
  if (typeof payload.deployment_id !== 'string') return null;
  if (typeof payload.model_name !== 'string') return null;
  if (typeof payload.model_version !== 'string') return null;
  if (typeof payload.artifact_ref !== 'string') return null;
  if (!isModelDeploymentStatus(payload.status)) return null;
  if (payload.previous_status !== undefined && !isModelDeploymentStatus(payload.previous_status)) return null;
  if (typeof payload.event_type !== 'string') return null;
  if (typeof payload.detail !== 'string') return null;
  if (typeof payload.updated_at !== 'string') return null;
  return {
    deployment_id: payload.deployment_id,
    model_name: payload.model_name,
    model_version: payload.model_version,
    artifact_ref: payload.artifact_ref,
    status: payload.status,
    previous_status: payload.previous_status,
    event_type: payload.event_type,
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


function parsePortfolioSnapshot(payload: unknown): PortfolioSnapshot {
  if (!isRecord(payload)) throw new Error('Portfolio snapshot payload must be an object.');
  if (typeof payload.account_id !== 'string') throw new Error('Portfolio snapshot account_id is malformed.');
  if (typeof payload.timestamp !== 'string') throw new Error('Portfolio snapshot timestamp is malformed.');
  if (!Array.isArray(payload.positions)) throw new Error('Portfolio snapshot positions is malformed.');

  const positions = payload.positions.map((position, index) => {
    if (!isRecord(position)) throw new Error(`Portfolio position at index ${index} must be an object.`);
    if (typeof position.symbol !== 'string') throw new Error(`Portfolio position at index ${index} has malformed symbol.`);
    return {
      symbol: position.symbol,
      quantity: Number(position.quantity ?? 0),
      averagePrice: Number(position.average_price ?? 0),
      marketPrice: Number(position.market_price ?? 0),
      marketValue: Number(position.market_value ?? 0),
      unrealizedPnl: Number(position.unrealized_pnl ?? 0),
      side: position.side === 'short' ? 'short' : 'long',
    };
  });

  return {
    accountId: payload.account_id,
    timestampIso: payload.timestamp,
    equity: Number(payload.equity ?? 0),
    cash: Number(payload.cash ?? 0),
    buyingPower: Number(payload.buying_power ?? 0),
    grossExposure: Number(payload.gross_exposure ?? 0),
    netExposure: Number(payload.net_exposure ?? 0),
    unrealizedPnl: Number(payload.unrealized_pnl ?? 0),
    realizedPnl: Number(payload.realized_pnl ?? 0),
    positions,
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


function parseStrategyInstances(payload: unknown): StrategyInstance[] {
  if (!Array.isArray(payload)) throw new Error('Strategy instances payload must be an array.');
  return payload.map((item, index) => parseStrategyInstance(item, index));
}

function parseStrategyInstance(payload: unknown, index = 0): StrategyInstance {
  if (!isRecord(payload)) throw new Error(`Strategy instance at index ${index} must be an object.`);
  if (typeof payload.id !== 'string') throw new Error(`Strategy instance at index ${index} has malformed id.`);
  if (typeof payload.strategy_key !== 'string') throw new Error(`Strategy instance at index ${index} has malformed strategy_key.`);
  if ((payload.mode !== 'paper' && payload.mode !== 'live')) throw new Error(`Strategy instance at index ${index} has malformed mode.`);
  if (!isStrategyStatus(payload.status)) throw new Error(`Strategy instance at index ${index} has malformed status.`);
  if (!isRecord(payload.intent)) throw new Error(`Strategy instance at index ${index} has malformed intent.`);
  if (typeof payload.created_at !== 'string') throw new Error(`Strategy instance at index ${index} has malformed created_at.`);
  if (typeof payload.updated_at !== 'string') throw new Error(`Strategy instance at index ${index} has malformed updated_at.`);

  return {
    id: payload.id,
    strategyKey: payload.strategy_key,
    mode: payload.mode as StrategyMode,
    status: payload.status as StrategyInstanceStatus,
    intent: {
      notes: typeof payload.intent.notes === 'string' ? payload.intent.notes : undefined,
      params: isRecord(payload.intent.params) ? payload.intent.params : {},
    },
    createdAtIso: payload.created_at,
    updatedAtIso: payload.updated_at,
    startedAtIso: typeof payload.started_at === 'string' ? payload.started_at : undefined,
    stoppedAtIso: typeof payload.stopped_at === 'string' ? payload.stopped_at : undefined,
  };
}

function parseStrategyInstanceActionResponse(payload: unknown): StrategyInstanceActionResponse {
  if (!isRecord(payload)) throw new Error('Strategy action payload must be an object.');
  if (typeof payload.detail !== 'string') throw new Error('Strategy action payload detail is malformed.');

  return {
    detail: payload.detail,
    instance: parseStrategyInstance(payload.instance),
  };
}

function isStrategyStatus(value: unknown): value is StrategyInstanceStatus {
  return value === 'created' || value === 'running' || value === 'stopped';
}

function parseModelDeployments(payload: unknown): ModelDeployment[] {
  if (!Array.isArray(payload)) throw new Error('Model deployments payload must be an array.');
  return payload.map((item, index) => parseModelDeployment(item, index));
}

function parseModelDeployment(payload: unknown, index = 0): ModelDeployment {
  if (!isRecord(payload)) throw new Error(`Model deployment at index ${index} must be an object.`);
  if (typeof payload.id !== 'string') throw new Error(`Model deployment at index ${index} has malformed id.`);
  if (typeof payload.model_name !== 'string') throw new Error(`Model deployment at index ${index} has malformed model_name.`);
  if (typeof payload.model_version !== 'string') throw new Error(`Model deployment at index ${index} has malformed model_version.`);
  if (typeof payload.artifact_ref !== 'string') throw new Error(`Model deployment at index ${index} has malformed artifact_ref.`);
  if (!isModelDeploymentStatus(payload.status)) throw new Error(`Model deployment at index ${index} has malformed status.`);
  if (typeof payload.created_at !== 'string') throw new Error(`Model deployment at index ${index} has malformed created_at.`);
  if (typeof payload.updated_at !== 'string') throw new Error(`Model deployment at index ${index} has malformed updated_at.`);
  return {
    id: payload.id,
    modelName: payload.model_name,
    modelVersion: payload.model_version,
    artifactRef: payload.artifact_ref,
    status: payload.status,
    createdAtIso: payload.created_at,
    updatedAtIso: payload.updated_at,
  };
}

function parseModelDeploymentActionResponse(payload: unknown): ModelDeploymentActionResponse {
  if (!isRecord(payload)) throw new Error('Model deployment action payload must be an object.');
  if (typeof payload.detail !== 'string') throw new Error('Model deployment action payload detail is malformed.');
  return {
    detail: payload.detail,
    deployment: parseModelDeployment(payload.deployment),
  };
}

function isModelDeploymentStatus(value: unknown): value is ModelDeploymentStatus {
  return value === 'deploying' || value === 'active' || value === 'inactive';
}
