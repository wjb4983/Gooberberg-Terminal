import type {
  AlertEvent,
  BacktestRun,
  CreateBacktestRunRequest,
  CreateJobRequest,
  CreateJobResponse,
  CreateModelConfigRequest,
  CreateModelDeploymentRequest,
  CreateParameterSweepRequest,
  CreateStrategyInstanceRequest,
  CreateTrainingRunRequest,
  GraphTopology,
  HealthResponse,
  QueueHealthResponse,
  JobLifecyclePayload,
  JobLogPayload,
  JobProgressPayload,
  JobStatusResponse,
  MarketDataCacheCoverageResponse,
  MarketDataIngestionRequest,
  MarketDataIngestionResponse,
  ModelConfig,
  ModelDeployment,
  ModelDeploymentActionResponse,
  ModelDeploymentEventPayload,
  ModelDeploymentStatus,
  ParameterSweepRun,
  PortfolioSnapshot,
  StrategyInstance,
  StrategyInstanceActionResponse,
  StrategyInstanceStatus,
  StrategyMode,
  TrainingRun,
  UpdateModelConfigRequest,
  WebSocketEventEnvelope,
  WebSocketTopic,
  LogEvent,
} from '@gb/schemas';
import {
  parseBacktestRun,
  parseGraphTopology,
  parseMarketDataCacheCoverageResponse,
  parseMarketDataIngestionResponse,
  parseModelConfig,
  parseParameterSweepRun,
  parseTrainingRun,
} from '@gb/schemas';

export interface ApiClientOptions {
  baseHttpUrl: string;
  apiPrefix?: string;
  websocketUrl?: string;
  fetchImpl?: typeof fetch;
  authHeaderProvider?: AuthHeaderProvider;
}

export type AuthHeaderProvider = (path: string, init: ApiRequestOptions) => string | null | undefined | Promise<string | null | undefined>;

export type ApiRequestQuery = Record<string, string | number | boolean | null | undefined>;

export interface ApiRequestOptions extends Omit<RequestInit, 'headers'> {
  headers?: HeadersInit;
  query?: ApiRequestQuery;
  includeAuth?: boolean;
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
  private readonly authHeaderProvider?: AuthHeaderProvider;

  constructor(options: ApiClientOptions) {
    this.fetchImpl = options.fetchImpl ?? fetch;
    this.baseHttpUrl = options.baseHttpUrl.replace(/\/$/, '');
    this.apiPrefix = options.apiPrefix ?? '/api/v1';
    this.websocketUrl = options.websocketUrl;
    this.authHeaderProvider = options.authHeaderProvider;
  }

  async getHealth(): Promise<HealthResponse> {
    const payload = await this.requestJson<unknown>(`${this.apiPrefix}/health`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      includeAuth: false,
    });

    return parseHealthResponse(payload);
  }

  async getQueueHealth(): Promise<QueueHealthResponse> {
    const payload = await this.requestJson<unknown>(`${this.apiPrefix}/health/queue`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      includeAuth: false,
    });

    return parseQueueHealthResponse(payload);
  }

  async getAlerts(): Promise<AlertEvent[]> {
    const payload = await this.requestJson<unknown>(`${this.apiPrefix}/alerts`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    });

    return parseAlerts(payload);
  }

  async acknowledgeAlert(alertId: string): Promise<AlertEvent> {
    const payload = await this.requestJson<unknown>(`${this.apiPrefix}/alerts/${encodeURIComponent(alertId)}/ack`, {
      method: 'POST',
      headers: { Accept: 'application/json' },
    });

    if (!isRecord(payload) || !isRecord(payload.alert)) {
      throw new Error('Acknowledge alert payload is malformed.');
    }

    return parseAlert(payload.alert);
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
        run_id: request.runId,
        run_type: request.runType,
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

  async listJobEvents(jobId: string): Promise<JobStatusResponse[]> {
    const payload = await this.requestJson<unknown>(`${this.apiPrefix}/jobs/${encodeURIComponent(jobId)}/events`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    });

    if (!Array.isArray(payload)) throw new Error('Job events payload must be an array.');
    return payload.map((event) => parseJobStatusResponse(event));
  }

  async listModelConfigs(): Promise<ModelConfig[]> {
    const payload = await this.requestJson<unknown>(`${this.apiPrefix}/model-configs`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    });
    if (!Array.isArray(payload)) throw new Error('Model configs payload must be an array.');
    return payload.map((item) => parseModelConfig(item));
  }

  async createModelConfig(request: CreateModelConfigRequest): Promise<ModelConfig> {
    const payload = await this.requestJson<unknown>(`${this.apiPrefix}/model-configs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({
        model_family: request.modelFamily,
        config: request.config,
      }),
    });
    return parseModelConfig(payload);
  }

  async getModelConfig(modelConfigId: string): Promise<ModelConfig> {
    const payload = await this.requestJson<unknown>(`${this.apiPrefix}/model-configs/${encodeURIComponent(modelConfigId)}`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    });
    return parseModelConfig(payload);
  }

  async updateModelConfig(modelConfigId: string, request: UpdateModelConfigRequest): Promise<ModelConfig> {
    const payload = await this.requestJson<unknown>(`${this.apiPrefix}/model-configs/${encodeURIComponent(modelConfigId)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ config: request.config }),
    });
    return parseModelConfig(payload);
  }

  async listTrainingRuns(): Promise<TrainingRun[]> {
    const payload = await this.requestJson<unknown>(`${this.apiPrefix}/training-runs`, { method: 'GET', headers: { Accept: 'application/json' } });
    if (!Array.isArray(payload)) throw new Error('Training runs payload must be an array.');
    return payload.map((item) => parseTrainingRun(item));
  }

  async createTrainingRun(request: CreateTrainingRunRequest): Promise<TrainingRun> {
    const payload = await this.requestJson<unknown>(`${this.apiPrefix}/training-runs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({
        model_config_id: request.modelConfigId,
        dataset_id: request.datasetId,
        parameters: request.parameters ?? {},
      }),
    });
    return parseTrainingRun(payload);
  }

  async getTrainingRun(runId: string): Promise<TrainingRun> {
    const payload = await this.requestJson<unknown>(`${this.apiPrefix}/training-runs/${encodeURIComponent(runId)}`, { method: 'GET', headers: { Accept: 'application/json' } });
    return parseTrainingRun(payload);
  }

  async listParameterSweeps(): Promise<ParameterSweepRun[]> {
    const payload = await this.requestJson<unknown>(`${this.apiPrefix}/parameter-sweeps`, { method: 'GET', headers: { Accept: 'application/json' } });
    if (!Array.isArray(payload)) throw new Error('Parameter sweeps payload must be an array.');
    return payload.map((item) => parseParameterSweepRun(item));
  }

  async createParameterSweep(request: CreateParameterSweepRequest): Promise<ParameterSweepRun> {
    const payload = await this.requestJson<unknown>(`${this.apiPrefix}/parameter-sweeps`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({
        model_config_id: request.modelConfigId,
        objective: request.objective,
        search_space: request.searchSpace ?? {},
      }),
    });
    return parseParameterSweepRun(payload);
  }

  async getParameterSweep(sweepId: string): Promise<ParameterSweepRun> {
    const payload = await this.requestJson<unknown>(`${this.apiPrefix}/parameter-sweeps/${encodeURIComponent(sweepId)}`, { method: 'GET', headers: { Accept: 'application/json' } });
    return parseParameterSweepRun(payload);
  }

  async listBacktestRuns(): Promise<BacktestRun[]> {
    const payload = await this.requestJson<unknown>(`${this.apiPrefix}/backtest-runs`, { method: 'GET', headers: { Accept: 'application/json' } });
    if (!Array.isArray(payload)) throw new Error('Backtest runs payload must be an array.');
    return payload.map((item) => parseBacktestRun(item));
  }

  async createBacktestRun(request: CreateBacktestRunRequest): Promise<BacktestRun> {
    const payload = await this.requestJson<unknown>(`${this.apiPrefix}/backtest-runs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({
        strategy_key: request.strategyKey,
        model_config_id: request.modelConfigId,
        window_start: request.windowStartIso,
        window_end: request.windowEndIso,
        parameters: request.parameters ?? {},
      }),
    });
    return parseBacktestRun(payload);
  }

  async getBacktestRun(runId: string): Promise<BacktestRun> {
    const payload = await this.requestJson<unknown>(`${this.apiPrefix}/backtest-runs/${encodeURIComponent(runId)}`, { method: 'GET', headers: { Accept: 'application/json' } });
    return parseBacktestRun(payload);
  }

  async requestMarketDataIngestion(request: MarketDataIngestionRequest): Promise<MarketDataIngestionResponse> {
    const payload = await this.requestJson<unknown>(`${this.apiPrefix}/market-data/ingestions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({
        source: request.source,
        symbols: request.symbols,
        timeframe: request.timeframe,
        start_date: request.startDate,
        end_date: request.endDate,
      }),
    });
    return parseMarketDataIngestionResponse(payload);
  }

  async getMarketDataCacheCoverage(symbol: string, timeframe: string): Promise<MarketDataCacheCoverageResponse> {
    const params = new URLSearchParams({ symbol, timeframe });
    const payload = await this.requestJson<unknown>(`${this.apiPrefix}/market-data/cache-coverage?${params.toString()}`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    });
    return parseMarketDataCacheCoverageResponse(payload);
  }

  async listModelDeployments(): Promise<ModelDeployment[]> { /* unchanged */
    const payload = await this.requestJson<unknown>(`${this.apiPrefix}/models/deployments`, { method: 'GET', headers: { Accept: 'application/json' } });
    return parseModelDeployments(payload);
  }

  async createModelDeployment(request: CreateModelDeploymentRequest): Promise<ModelDeployment> {
    const payload = await this.requestJson<unknown>(`${this.apiPrefix}/models/deployments`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ model_name: request.modelName, model_version: request.modelVersion, artifact_ref: request.artifactRef }),
    });
    return parseModelDeployment(payload);
  }

  async activateModelDeployment(deploymentId: string): Promise<ModelDeploymentActionResponse> { const payload = await this.requestJson<unknown>(`${this.apiPrefix}/models/deployments/${encodeURIComponent(deploymentId)}/activate`, { method: 'POST', headers: { Accept: 'application/json' } }); return parseModelDeploymentActionResponse(payload); }
  async deactivateModelDeployment(deploymentId: string): Promise<ModelDeploymentActionResponse> { const payload = await this.requestJson<unknown>(`${this.apiPrefix}/models/deployments/${encodeURIComponent(deploymentId)}/deactivate`, { method: 'POST', headers: { Accept: 'application/json' } }); return parseModelDeploymentActionResponse(payload); }
  async listStrategyInstances(): Promise<StrategyInstance[]> { const payload = await this.requestJson<unknown>(`${this.apiPrefix}/strategies/instances`, { method: 'GET', headers: { Accept: 'application/json' } }); return parseStrategyInstances(payload); }
  async createStrategyInstance(request: CreateStrategyInstanceRequest): Promise<StrategyInstance> { const payload = await this.requestJson<unknown>(`${this.apiPrefix}/strategies/instances`, { method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'application/json' }, body: JSON.stringify({ strategy_key: request.strategyKey, mode: request.mode, intent: request.intent ?? { params: {} } }) }); return parseStrategyInstance(payload); }
  async startStrategyInstance(instanceId: string): Promise<StrategyInstanceActionResponse> { const payload = await this.requestJson<unknown>(`${this.apiPrefix}/strategies/instances/${encodeURIComponent(instanceId)}/start`, { method: 'POST', headers: { Accept: 'application/json' } }); return parseStrategyInstanceActionResponse(payload); }
  async stopStrategyInstance(instanceId: string): Promise<StrategyInstanceActionResponse> { const payload = await this.requestJson<unknown>(`${this.apiPrefix}/strategies/instances/${encodeURIComponent(instanceId)}/stop`, { method: 'POST', headers: { Accept: 'application/json' } }); return parseStrategyInstanceActionResponse(payload); }
  async cancelJob(jobId: string): Promise<JobStatusResponse> { const payload = await this.requestJson<unknown>(`${this.apiPrefix}/jobs/${encodeURIComponent(jobId)}/cancel`, { method: 'POST', headers: { Accept: 'application/json' } }); return parseJobStatusResponse(payload); }
  async retryJob(jobId: string): Promise<JobStatusResponse> { const payload = await this.requestJson<unknown>(`${this.apiPrefix}/jobs/${encodeURIComponent(jobId)}/retry`, { method: 'POST', headers: { Accept: 'application/json' } }); return parseJobStatusResponse(payload); }

  request<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
    return this.requestJson<T>(path, options);
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

  private async requestJson<T>(path: string, init: ApiRequestOptions): Promise<T> {
    const fullPath = this.resolveRequestPath(path, init.query);
    const requestInit = await this.resolveRequestInit(path, init);
    const response = await this.fetchImpl(`${this.baseHttpUrl}${fullPath}`, requestInit);
    if (!response.ok) throw new Error(`Request failed for ${path} with status ${response.status}`);
    return (await response.json()) as T;
  }

  private resolveRequestPath(path: string, query?: ApiRequestQuery): string {
    if (!query) return path;
    const params = new URLSearchParams();
    Object.entries(query).forEach(([key, value]) => {
      if (value === undefined || value === null) return;
      params.set(key, String(value));
    });
    const serializedQuery = params.toString();
    if (!serializedQuery) return path;
    const separator = path.includes('?') ? '&' : '?';
    return `${path}${separator}${serializedQuery}`;
  }

  private async resolveRequestInit(path: string, init: ApiRequestOptions): Promise<RequestInit> {
    const { includeAuth = true, query: _query, headers, ...requestInit } = init;
    const normalizedHeaders = new Headers(headers);
    const hasAuthorization = normalizedHeaders.has('Authorization');
    if (includeAuth && !hasAuthorization && this.authHeaderProvider) {
      const authHeader = await this.authHeaderProvider(path, init);
      if (authHeader) {
        normalizedHeaders.set('Authorization', authHeader);
      }
    }
    return {
      ...requestInit,
      headers: normalizedHeaders,
    };
  }

  private resolveWebSocketUrl(): string {
    if (this.websocketUrl) return this.websocketUrl;
    return `${this.baseHttpUrl.replace(/^http/, 'ws')}/ws`;
  }

  private withResumeSeq(url: string, lastSeq?: number): string {
    if (lastSeq === undefined) return url;
    const separator = url.includes('?') ? '&' : '?';
    return `${url}${separator}last_seq=${encodeURIComponent(String(lastSeq))}`;
  }
}

export function parseWebSocketEvent(raw: string): WebSocketEventEnvelope | null {
  let payload: unknown;
  try { payload = JSON.parse(raw); } catch { return null; }
  if (!isRecord(payload)) return null;
  if (typeof payload.event_id !== 'string') return null;
  if (typeof payload.seq !== 'number') return null;
  if (typeof payload.topic !== 'string') return null;
  if (typeof payload.timestamp !== 'string') return null;
  if (typeof payload.version !== 'string') return null;
  if (!isRecord(payload.payload)) return null;
  if (typeof payload.envelope_version !== 'string') return null;
  if (typeof payload.contract_name !== 'string') return null;
  if (typeof payload.contract_version !== 'string') return null;

  return {
    event_id: payload.event_id,
    seq: payload.seq,
    topic: payload.topic as WebSocketTopic,
    timestamp: payload.timestamp,
    payload: payload.payload,
    version: payload.version,
    envelope_version: payload.envelope_version,
    contract_name: payload.contract_name,
    contract_version: payload.contract_version,
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

export function parseJobProgressPayload(payload: unknown): JobProgressPayload | null {
  if (!isRecord(payload)) return null;
  if (typeof payload.job_id !== 'string') return null;
  if (payload.run_id !== undefined && payload.run_id !== null && typeof payload.run_id !== 'string') return null;
  if (typeof payload.status !== 'string') return null;
  if (typeof payload.progress_pct !== 'number') return null;
  if (typeof payload.message !== 'string') return null;
  if (typeof payload.timestamp !== 'string') return null;
  if (typeof payload.updated_at !== 'string') return null;
  return {
    job_id: payload.job_id,
    run_id: typeof payload.run_id === 'string' ? payload.run_id : undefined,
    status: payload.status as JobProgressPayload['status'],
    progress_pct: payload.progress_pct,
    message: payload.message,
    timestamp: payload.timestamp,
    updated_at: payload.updated_at,
  };
}

export function parseJobLogPayload(payload: unknown): JobLogPayload | null {
  return parseJobProgressPayload(payload) as JobLogPayload | null;
}

export function parseModelDeploymentPayload(payload: unknown): ModelDeploymentEventPayload | null { if (!isRecord(payload)) return null; if (typeof payload.deployment_id !== 'string') return null; if (typeof payload.model_name !== 'string') return null; if (typeof payload.model_version !== 'string') return null; if (typeof payload.artifact_ref !== 'string') return null; if (!isModelDeploymentStatus(payload.status)) return null; if (payload.previous_status !== undefined && !isModelDeploymentStatus(payload.previous_status)) return null; if (typeof payload.event_type !== 'string') return null; if (typeof payload.detail !== 'string') return null; if (typeof payload.updated_at !== 'string') return null; return { deployment_id: payload.deployment_id, model_name: payload.model_name, model_version: payload.model_version, artifact_ref: payload.artifact_ref, status: payload.status, previous_status: payload.previous_status, event_type: payload.event_type, detail: payload.detail, updated_at: payload.updated_at }; }
export function parseAlertPayload(payload: unknown): AlertEvent | null { try { return parseAlert(payload); } catch { return null; } }
export function parseLogPayload(payload: unknown): LogEvent | null { if (!isRecord(payload)) return null; if (typeof payload.timestamp !== 'string') return null; if (typeof payload.service !== 'string') return null; if (typeof payload.level !== 'string') return null; if (typeof payload.trace_id !== 'string') return null; if (typeof payload.message !== 'string') return null; return { timestamp: payload.timestamp, service: payload.service, level: payload.level as LogEvent['level'], trace_id: payload.trace_id, message: payload.message, category: typeof payload.category === 'string' ? payload.category : undefined, fields: isRecord(payload.fields) ? payload.fields : undefined }; }
function parseAlerts(payload: unknown): AlertEvent[] { if (!Array.isArray(payload)) throw new Error('Alerts payload must be an array.'); return payload.map((item) => parseAlert(item)); }
function parseAlert(payload: unknown): AlertEvent { if (!isRecord(payload)) throw new Error('Alert payload must be an object.'); if (typeof payload.id !== 'string') throw new Error('Alert payload id is malformed.'); if (typeof payload.timestamp !== 'string') throw new Error('Alert payload timestamp is malformed.'); if (typeof payload.service !== 'string') throw new Error('Alert payload service is malformed.'); if (typeof payload.level !== 'string') throw new Error('Alert payload level is malformed.'); if (typeof payload.trace_id !== 'string') throw new Error('Alert payload trace_id is malformed.'); if (typeof payload.message !== 'string') throw new Error('Alert payload message is malformed.'); if (typeof payload.category !== 'string') throw new Error('Alert payload category is malformed.'); if (typeof payload.status !== 'string') throw new Error('Alert payload status is malformed.'); return { id: payload.id, timestamp: payload.timestamp, service: payload.service, level: payload.level as AlertEvent['level'], trace_id: payload.trace_id, message: payload.message, category: payload.category, status: payload.status as AlertEvent['status'], acknowledged_at: typeof payload.acknowledged_at === 'string' ? payload.acknowledged_at : undefined }; }
function parseHealthResponse(payload: unknown): HealthResponse { if (!isRecord(payload)) throw new Error('Health payload must be an object.'); if (typeof payload.service !== 'string') throw new Error('Health payload service is malformed.'); if (typeof payload.status !== 'string') throw new Error('Health payload status is malformed.'); if (typeof payload.version !== 'string') throw new Error('Health payload version is malformed.'); return { service: payload.service, status: payload.status, version: payload.version, postgres: payload.postgres as HealthResponse['postgres'], redis: payload.redis as HealthResponse['redis'] }; }
function parseQueueHealthResponse(payload: unknown): QueueHealthResponse { if (!isRecord(payload)) throw new Error('Queue health payload must be an object.'); if (typeof payload.status !== 'string') throw new Error('Queue health payload status is malformed.'); if (payload.queue_depth !== null && payload.queue_depth !== undefined && typeof payload.queue_depth !== 'number') throw new Error('Queue health payload queue_depth is malformed.'); if (payload.worker_heartbeat_at !== null && payload.worker_heartbeat_at !== undefined && typeof payload.worker_heartbeat_at !== 'string') throw new Error('Queue health payload worker_heartbeat_at is malformed.'); if (payload.worker_heartbeat_age_seconds !== null && payload.worker_heartbeat_age_seconds !== undefined && typeof payload.worker_heartbeat_age_seconds !== 'number') throw new Error('Queue health payload worker_heartbeat_age_seconds is malformed.'); if (typeof payload.detail !== 'string') throw new Error('Queue health payload detail is malformed.'); return { status: payload.status, queueDepth: payload.queue_depth ?? null, workerHeartbeatAt: payload.worker_heartbeat_at ?? null, workerHeartbeatAgeSeconds: payload.worker_heartbeat_age_seconds ?? null, detail: payload.detail }; }
function parsePortfolioSnapshot(payload: unknown): PortfolioSnapshot { if (!isRecord(payload)) throw new Error('Portfolio snapshot payload must be an object.'); if (typeof payload.account_id !== 'string') throw new Error('Portfolio snapshot account_id is malformed.'); if (typeof payload.timestamp !== 'string') throw new Error('Portfolio snapshot timestamp is malformed.'); if (!Array.isArray(payload.positions)) throw new Error('Portfolio snapshot positions is malformed.'); const positions = payload.positions.map((position, index) => { if (!isRecord(position)) throw new Error(`Portfolio position at index ${index} must be an object.`); if (typeof position.symbol !== 'string') throw new Error(`Portfolio position at index ${index} has malformed symbol.`); return { symbol: position.symbol, quantity: Number(position.quantity ?? 0), averagePrice: Number(position.average_price ?? 0), marketPrice: Number(position.market_price ?? 0), marketValue: Number(position.market_value ?? 0), unrealizedPnl: Number(position.unrealized_pnl ?? 0), side: position.side === 'short' ? ('short' as const) : ('long' as const) }; }); return { accountId: payload.account_id, timestampIso: payload.timestamp, equity: Number(payload.equity ?? 0), cash: Number(payload.cash ?? 0), buyingPower: Number(payload.buying_power ?? 0), grossExposure: Number(payload.gross_exposure ?? 0), netExposure: Number(payload.net_exposure ?? 0), unrealizedPnl: Number(payload.unrealized_pnl ?? 0), realizedPnl: Number(payload.realized_pnl ?? 0), positions }; }
function parseCreateJobResponse(payload: unknown): CreateJobResponse { if (!isRecord(payload)) throw new Error('Create job payload must be an object.'); if (typeof payload.id !== 'string') throw new Error('Create job payload id is malformed.'); if (typeof payload.job_type !== 'string') throw new Error('Create job payload job_type is malformed.'); if (typeof payload.status !== 'string') throw new Error('Create job payload status is malformed.'); if (!isRecord(payload.payload)) throw new Error('Create job payload payload is malformed.'); if (typeof payload.accepted_at !== 'string') throw new Error('Create job payload accepted_at is malformed.'); if (typeof payload.trace_id !== 'string') throw new Error('Create job payload trace_id is malformed.'); return { id: payload.id, jobType: payload.job_type, status: payload.status as CreateJobResponse['status'], payload: payload.payload, acceptedAtIso: payload.accepted_at, traceId: payload.trace_id, runId: typeof payload.run_id === 'string' ? payload.run_id : undefined, runType: typeof payload.run_type === 'string' ? payload.run_type as CreateJobResponse['runType'] : undefined }; }
function parseJobStatusResponse(payload: unknown): JobStatusResponse { if (!isRecord(payload)) throw new Error('Job status payload must be an object.'); if (typeof payload.id !== 'string') throw new Error('Job status payload id is malformed.'); if (typeof payload.status !== 'string') throw new Error('Job status payload status is malformed.'); if (typeof payload.detail !== 'string') throw new Error('Job status payload detail is malformed.'); if (typeof payload.trace_id !== 'string') throw new Error('Job status payload trace_id is malformed.'); if (typeof payload.updated_at !== 'string') throw new Error('Job status payload updated_at is malformed.'); return { id: payload.id, status: payload.status as JobStatusResponse['status'], detail: payload.detail, traceId: payload.trace_id, runId: typeof payload.run_id === 'string' ? payload.run_id : undefined, runType: typeof payload.run_type === 'string' ? payload.run_type as JobStatusResponse['runType'] : undefined, progressPct: Number(payload.progress_pct ?? 0), message: typeof payload.message === 'string' ? payload.message : '', resultRef: typeof payload.result_ref === 'string' ? payload.result_ref : undefined, updatedAtIso: payload.updated_at }; }
function isRecord(value: unknown): value is Record<string, unknown> { return typeof value === 'object' && value !== null; }
function parseStrategyInstances(payload: unknown): StrategyInstance[] { if (!Array.isArray(payload)) throw new Error('Strategy instances payload must be an array.'); return payload.map((item, index) => parseStrategyInstance(item, index)); }
function parseStrategyInstance(payload: unknown, index = 0): StrategyInstance { if (!isRecord(payload)) throw new Error(`Strategy instance at index ${index} must be an object.`); if (typeof payload.id !== 'string') throw new Error(`Strategy instance at index ${index} has malformed id.`); if (typeof payload.strategy_key !== 'string') throw new Error(`Strategy instance at index ${index} has malformed strategy_key.`); if ((payload.mode !== 'paper' && payload.mode !== 'live')) throw new Error(`Strategy instance at index ${index} has malformed mode.`); if (!isStrategyStatus(payload.status)) throw new Error(`Strategy instance at index ${index} has malformed status.`); if (!isRecord(payload.intent)) throw new Error(`Strategy instance at index ${index} has malformed intent.`); if (typeof payload.created_at !== 'string') throw new Error(`Strategy instance at index ${index} has malformed created_at.`); if (typeof payload.updated_at !== 'string') throw new Error(`Strategy instance at index ${index} has malformed updated_at.`); return { id: payload.id, strategyKey: payload.strategy_key, mode: payload.mode as StrategyMode, status: payload.status as StrategyInstanceStatus, intent: { notes: typeof payload.intent.notes === 'string' ? payload.intent.notes : undefined, params: isRecord(payload.intent.params) ? payload.intent.params : {} }, createdAtIso: payload.created_at, updatedAtIso: payload.updated_at, startedAtIso: typeof payload.started_at === 'string' ? payload.started_at : undefined, stoppedAtIso: typeof payload.stopped_at === 'string' ? payload.stopped_at : undefined }; }
function parseStrategyInstanceActionResponse(payload: unknown): StrategyInstanceActionResponse { if (!isRecord(payload)) throw new Error('Strategy action payload must be an object.'); if (typeof payload.detail !== 'string') throw new Error('Strategy action payload detail is malformed.'); return { detail: payload.detail, instance: parseStrategyInstance(payload.instance) }; }
function isStrategyStatus(value: unknown): value is StrategyInstanceStatus { return value === 'created' || value === 'running' || value === 'stopped'; }
function parseModelDeployments(payload: unknown): ModelDeployment[] { if (!Array.isArray(payload)) throw new Error('Model deployments payload must be an array.'); return payload.map((item, index) => parseModelDeployment(item, index)); }
function parseModelDeployment(payload: unknown, index = 0): ModelDeployment { if (!isRecord(payload)) throw new Error(`Model deployment at index ${index} must be an object.`); if (typeof payload.id !== 'string') throw new Error(`Model deployment at index ${index} has malformed id.`); if (typeof payload.model_name !== 'string') throw new Error(`Model deployment at index ${index} has malformed model_name.`); if (typeof payload.model_version !== 'string') throw new Error(`Model deployment at index ${index} has malformed model_version.`); if (typeof payload.artifact_ref !== 'string') throw new Error(`Model deployment at index ${index} has malformed artifact_ref.`); if (!isModelDeploymentStatus(payload.status)) throw new Error(`Model deployment at index ${index} has malformed status.`); if (typeof payload.created_at !== 'string') throw new Error(`Model deployment at index ${index} has malformed created_at.`); if (typeof payload.updated_at !== 'string') throw new Error(`Model deployment at index ${index} has malformed updated_at.`); return { id: payload.id, modelName: payload.model_name, modelVersion: payload.model_version, artifactRef: payload.artifact_ref, status: payload.status, createdAtIso: payload.created_at, updatedAtIso: payload.updated_at }; }
function parseModelDeploymentActionResponse(payload: unknown): ModelDeploymentActionResponse { if (!isRecord(payload)) throw new Error('Model deployment action payload must be an object.'); if (typeof payload.detail !== 'string') throw new Error('Model deployment action payload detail is malformed.'); return { detail: payload.detail, deployment: parseModelDeployment(payload.deployment) }; }
function isModelDeploymentStatus(value: unknown): value is ModelDeploymentStatus { return value === 'deploying' || value === 'active' || value === 'inactive'; }
