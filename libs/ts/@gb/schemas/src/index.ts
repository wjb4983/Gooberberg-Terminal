export type HealthStatus = 'healthy' | 'degraded' | 'unhealthy';

export type JobStatus = 'queued' | 'running' | 'success' | 'failed' | 'accepted' | 'pending' | 'succeeded' | 'cancelled';
export type RunType = 'training' | 'parameter_sweep' | 'backtest';
export type RunStatus = 'queued' | 'running' | 'success' | 'failed' | 'cancelled';
export type ModelFamily = 'hmm_regime_switching';

export interface Job {
  id: string;
  jobType: string;
  status: JobStatus;
  payload: Record<string, unknown>;
  acceptedAtIso: string;
}

export type StrategyMode = 'paper' | 'live';

export type StrategyInstanceStatus = 'created' | 'running' | 'stopped';
export type ModelDeploymentStatus = 'deploying' | 'active' | 'inactive';

export interface StrategyIntent {
  notes?: string;
  params: Record<string, unknown>;
}

export interface StrategyInstance {
  id: string;
  strategyKey: string;
  mode: StrategyMode;
  status: StrategyInstanceStatus;
  intent: StrategyIntent;
  createdAtIso: string;
  updatedAtIso: string;
  startedAtIso?: string;
  stoppedAtIso?: string;
}

export interface ModelDeployment {
  id: string;
  modelName: string;
  modelVersion: string;
  artifactRef: string;
  status: ModelDeploymentStatus;
  createdAtIso: string;
  updatedAtIso: string;
}

export interface CreateModelDeploymentRequest {
  modelName: string;
  modelVersion: string;
  artifactRef: string;
}

export interface ModelDeploymentActionResponse {
  deployment: ModelDeployment;
  detail: string;
}

export interface Position {
  symbol: string;
  quantity: number;
  averagePrice: number;
  marketPrice: number;
  marketValue: number;
  unrealizedPnl: number;
  side: 'long' | 'short';
}

export interface PortfolioSnapshot {
  accountId: string;
  timestampIso: string;
  equity: number;
  cash: number;
  buyingPower: number;
  grossExposure: number;
  netExposure: number;
  unrealizedPnl: number;
  realizedPnl: number;
  positions: Position[];
}

export interface ContractEnvelopeBase {
  version: string;
  emittedAtIso: string;
}

export type AlertSeverity = 'info' | 'warning' | 'critical';
export type AlertStatus = 'active' | 'acknowledged';

export interface AlertEvent {
  id: string;
  timestamp: string;
  service: string;
  level: AlertSeverity;
  trace_id: string;
  message: string;
  category: string;
  status: AlertStatus;
  acknowledged_at?: string;
}

export type LogLevel = 'debug' | 'info' | 'warning' | 'error';

export interface LogEvent {
  timestamp: string;
  service: string;
  level: LogLevel;
  trace_id: string;
  message: string;
  category?: string;
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

export interface QueueHealthResponse {
  status: string;
  queueDepth: number | null;
  workerHeartbeatAt: string | null;
  workerHeartbeatAgeSeconds: number | null;
  detail: string;
}

export interface CreateJobRequest {
  jobType: string;
  payload: Record<string, unknown>;
  runId?: string;
  runType?: RunType;
}

export interface CreateJobResponse {
  id: string;
  jobType: string;
  status: JobStatus;
  payload: Record<string, unknown>;
  acceptedAtIso: string;
  traceId: string;
  runId?: string;
  runType?: RunType;
}

export interface JobStatusResponse {
  id: string;
  status: JobStatus;
  detail: string;
  traceId: string;
  runId?: string;
  runType?: RunType;
  progressPct: number;
  message: string;
  resultRef?: string;
  updatedAtIso: string;
}

export interface JobProgressPayload {
  job_id: string;
  run_id?: string;
  status: JobStatus;
  progress_pct: number;
  message: string;
  timestamp: string;
  updated_at: string;
}

export interface JobLogPayload extends JobProgressPayload {}

export interface ArtifactSummary {
  runId: string;
  runType: RunType;
  jobId: string;
  artifactRef: string;
  metrics: Record<string, unknown>;
  notes?: string;
  createdAtIso: string;
}

export interface CreateStrategyInstanceRequest {
  strategyKey: string;
  mode: StrategyMode;
  intent?: StrategyIntent;
}

export interface StrategyInstanceActionResponse {
  instance: StrategyInstance;
  detail: string;
}

export type WebSocketTopic = 'jobs' | 'alerts' | 'logs' | 'portfolio' | 'risk' | 'strategy' | 'models' | 'backtests';

export interface WebSocketEventEnvelope<TPayload = Record<string, unknown>> {
  event_id: string;
  seq: number;
  topic: WebSocketTopic;
  timestamp: string;
  payload: TPayload;
  version: string;
  envelope_version: string;
  contract_name: string;
  contract_version: string;
}

export interface JobLifecyclePayload {
  job_id: string;
  trace_id: string;
  status: JobStatus;
  detail: string;
  updated_at: string;
}

export interface ModelDeploymentEventPayload {
  deployment_id: string;
  model_name: string;
  model_version: string;
  artifact_ref: string;
  status: ModelDeploymentStatus;
  previous_status?: ModelDeploymentStatus;
  event_type: string;
  detail: string;
  updated_at: string;
}

export interface ModelConfig {
  id: string;
  modelFamily: ModelFamily;
  config: Record<string, unknown>;
  createdAtIso: string;
  updatedAtIso: string;
}

export interface CreateModelConfigRequest {
  modelFamily: ModelFamily;
  config: Record<string, unknown>;
}

export interface UpdateModelConfigRequest {
  config: Record<string, unknown>;
}

export interface TrainingRun {
  id: string;
  modelConfigId: string;
  datasetId: string;
  jobId: string;
  status: RunStatus;
  parameters: Record<string, unknown>;
  createdAtIso: string;
}

export interface CreateTrainingRunRequest {
  modelConfigId: string;
  datasetId: string;
  parameters?: Record<string, unknown>;
}

export interface ParameterSweepRun {
  id: string;
  modelConfigId: string;
  objective: string;
  searchSpace: Record<string, unknown>;
  jobId: string;
  status: RunStatus;
  createdAtIso: string;
}

export interface CreateParameterSweepRequest {
  modelConfigId: string;
  objective: string;
  searchSpace?: Record<string, unknown>;
}

export interface BacktestRun {
  id: string;
  strategyKey: string;
  modelConfigId?: string;
  windowStartIso: string;
  windowEndIso: string;
  parameters: Record<string, unknown>;
  jobId: string;
  status: RunStatus;
  createdAtIso: string;
}

export interface CreateBacktestRunRequest {
  strategyKey: string;
  modelConfigId?: string;
  windowStartIso: string;
  windowEndIso: string;
  parameters?: Record<string, unknown>;
}

export interface MarketDataIngestionRequest {
  source: string;
  symbols: string[];
  timeframe: string;
  startDate: string;
  endDate: string;
}

export interface MarketDataIngestionResponse {
  requestId: string;
  status: string;
  source: string;
  symbols: string[];
  timeframe: string;
}

export interface MarketDataCacheCoverageResponse {
  symbol: string;
  timeframe: string;
  availableStart?: string;
  availableEnd?: string;
  coveragePct: number;
}

export type GraphNodeType = 'strategy' | 'model' | 'data_source' | 'risk_rule' | 'execution_adapter' | 'job';

export interface GraphNode {
  id: string;
  type: GraphNodeType;
  label: string;
  group?: string;
  metadata: Record<string, unknown>;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
}

export interface GraphTopology {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

const graphNodeTypes: ReadonlySet<GraphNodeType> = new Set([
  'strategy',
  'model',
  'data_source',
  'risk_rule',
  'execution_adapter',
  'job',
]);

const modelFamilies: ReadonlySet<ModelFamily> = new Set(['hmm_regime_switching']);
const runStatuses: ReadonlySet<RunStatus> = new Set(['queued', 'running', 'success', 'failed', 'cancelled']);

export function parseGraphTopology(payload: unknown): GraphTopology {
  if (!isRecord(payload)) throw new Error('Graph topology payload must be an object.');
  if (!Array.isArray(payload.nodes) || !Array.isArray(payload.edges)) {
    throw new Error('Graph topology payload is missing nodes or edges arrays.');
  }

  const nodes = payload.nodes.map((node, index) => parseGraphNode(node, index));
  const edges = payload.edges.map((edge, index) => parseGraphEdge(edge, index));
  return { nodes, edges };
}

export function parseModelConfig(payload: unknown): ModelConfig {
  if (!isRecord(payload)) throw new Error('Model config payload must be an object.');
  if (typeof payload.id !== 'string') throw new Error('Model config payload id is malformed.');
  if (typeof payload.model_family !== 'string' || !modelFamilies.has(payload.model_family as ModelFamily)) {
    throw new Error('Model config payload model_family is malformed.');
  }
  if (!isRecord(payload.config)) throw new Error('Model config payload config is malformed.');
  if (typeof payload.created_at !== 'string') throw new Error('Model config payload created_at is malformed.');
  if (typeof payload.updated_at !== 'string') throw new Error('Model config payload updated_at is malformed.');

  return {
    id: payload.id,
    modelFamily: payload.model_family as ModelFamily,
    config: payload.config,
    createdAtIso: payload.created_at,
    updatedAtIso: payload.updated_at,
  };
}

export function parseTrainingRun(payload: unknown): TrainingRun {
  if (!isRecord(payload)) throw new Error('Training run payload must be an object.');
  if (typeof payload.id !== 'string') throw new Error('Training run id is malformed.');
  if (typeof payload.model_config_id !== 'string') throw new Error('Training run model_config_id is malformed.');
  if (typeof payload.dataset_id !== 'string') throw new Error('Training run dataset_id is malformed.');
  if (typeof payload.job_id !== 'string') throw new Error('Training run job_id is malformed.');
  if (typeof payload.status !== 'string' || !runStatuses.has(payload.status as RunStatus)) throw new Error('Training run status is malformed.');
  if (!isRecord(payload.parameters)) throw new Error('Training run parameters is malformed.');
  if (typeof payload.created_at !== 'string') throw new Error('Training run created_at is malformed.');
  return {
    id: payload.id,
    modelConfigId: payload.model_config_id,
    datasetId: payload.dataset_id,
    jobId: payload.job_id,
    status: payload.status as RunStatus,
    parameters: payload.parameters,
    createdAtIso: payload.created_at,
  };
}

export function parseParameterSweepRun(payload: unknown): ParameterSweepRun {
  if (!isRecord(payload)) throw new Error('Parameter sweep payload must be an object.');
  if (typeof payload.id !== 'string') throw new Error('Parameter sweep id is malformed.');
  if (typeof payload.model_config_id !== 'string') throw new Error('Parameter sweep model_config_id is malformed.');
  if (typeof payload.objective !== 'string') throw new Error('Parameter sweep objective is malformed.');
  if (!isRecord(payload.search_space)) throw new Error('Parameter sweep search_space is malformed.');
  if (typeof payload.job_id !== 'string') throw new Error('Parameter sweep job_id is malformed.');
  if (typeof payload.status !== 'string' || !runStatuses.has(payload.status as RunStatus)) throw new Error('Parameter sweep status is malformed.');
  if (typeof payload.created_at !== 'string') throw new Error('Parameter sweep created_at is malformed.');
  return {
    id: payload.id,
    modelConfigId: payload.model_config_id,
    objective: payload.objective,
    searchSpace: payload.search_space,
    jobId: payload.job_id,
    status: payload.status as RunStatus,
    createdAtIso: payload.created_at,
  };
}

export function parseBacktestRun(payload: unknown): BacktestRun {
  if (!isRecord(payload)) throw new Error('Backtest payload must be an object.');
  if (typeof payload.id !== 'string') throw new Error('Backtest id is malformed.');
  if (typeof payload.strategy_key !== 'string') throw new Error('Backtest strategy_key is malformed.');
  if (payload.model_config_id !== null && payload.model_config_id !== undefined && typeof payload.model_config_id !== 'string') throw new Error('Backtest model_config_id is malformed.');
  if (typeof payload.window_start !== 'string' || typeof payload.window_end !== 'string') throw new Error('Backtest window range is malformed.');
  if (!isRecord(payload.parameters)) throw new Error('Backtest parameters is malformed.');
  if (typeof payload.job_id !== 'string') throw new Error('Backtest job_id is malformed.');
  if (typeof payload.status !== 'string' || !runStatuses.has(payload.status as RunStatus)) throw new Error('Backtest status is malformed.');
  if (typeof payload.created_at !== 'string') throw new Error('Backtest created_at is malformed.');
  return {
    id: payload.id,
    strategyKey: payload.strategy_key,
    modelConfigId: typeof payload.model_config_id === 'string' ? payload.model_config_id : undefined,
    windowStartIso: payload.window_start,
    windowEndIso: payload.window_end,
    parameters: payload.parameters,
    jobId: payload.job_id,
    status: payload.status as RunStatus,
    createdAtIso: payload.created_at,
  };
}

export function parseMarketDataIngestionResponse(payload: unknown): MarketDataIngestionResponse {
  if (!isRecord(payload)) throw new Error('Market data ingestion response must be an object.');
  if (typeof payload.request_id !== 'string') throw new Error('Market data ingestion response request_id is malformed.');
  if (typeof payload.status !== 'string') throw new Error('Market data ingestion response status is malformed.');
  if (typeof payload.source !== 'string') throw new Error('Market data ingestion response source is malformed.');
  if (!Array.isArray(payload.symbols) || payload.symbols.some((item) => typeof item !== 'string')) {
    throw new Error('Market data ingestion response symbols is malformed.');
  }
  if (typeof payload.timeframe !== 'string') throw new Error('Market data ingestion response timeframe is malformed.');

  return {
    requestId: payload.request_id,
    status: payload.status,
    source: payload.source,
    symbols: payload.symbols,
    timeframe: payload.timeframe,
  };
}

export function parseMarketDataCacheCoverageResponse(payload: unknown): MarketDataCacheCoverageResponse {
  if (!isRecord(payload)) throw new Error('Market data cache coverage payload must be an object.');
  if (typeof payload.symbol !== 'string') throw new Error('Market data cache coverage symbol is malformed.');
  if (typeof payload.timeframe !== 'string') throw new Error('Market data cache coverage timeframe is malformed.');
  if (payload.available_start !== null && payload.available_start !== undefined && typeof payload.available_start !== 'string') {
    throw new Error('Market data cache coverage available_start is malformed.');
  }
  if (payload.available_end !== null && payload.available_end !== undefined && typeof payload.available_end !== 'string') {
    throw new Error('Market data cache coverage available_end is malformed.');
  }
  return {
    symbol: payload.symbol,
    timeframe: payload.timeframe,
    availableStart: typeof payload.available_start === 'string' ? payload.available_start : undefined,
    availableEnd: typeof payload.available_end === 'string' ? payload.available_end : undefined,
    coveragePct: Number(payload.coverage_pct ?? 0),
  };
}

export function parseArtifactSummary(payload: unknown): ArtifactSummary {
  if (!isRecord(payload)) throw new Error('Artifact summary payload must be an object.');
  if (typeof payload.run_id !== 'string') throw new Error('Artifact summary run_id is malformed.');
  if (payload.run_type !== 'training' && payload.run_type !== 'parameter_sweep' && payload.run_type !== 'backtest') {
    throw new Error('Artifact summary run_type is malformed.');
  }
  if (typeof payload.job_id !== 'string') throw new Error('Artifact summary job_id is malformed.');
  if (typeof payload.artifact_ref !== 'string') throw new Error('Artifact summary artifact_ref is malformed.');
  if (!isRecord(payload.metrics)) throw new Error('Artifact summary metrics is malformed.');
  if (payload.notes !== undefined && payload.notes !== null && typeof payload.notes !== 'string') throw new Error('Artifact summary notes is malformed.');
  if (typeof payload.created_at !== 'string') throw new Error('Artifact summary created_at is malformed.');

  return {
    runId: payload.run_id,
    runType: payload.run_type,
    jobId: payload.job_id,
    artifactRef: payload.artifact_ref,
    metrics: payload.metrics,
    notes: typeof payload.notes === 'string' ? payload.notes : undefined,
    createdAtIso: payload.created_at,
  };
}

function parseGraphNode(payload: unknown, index: number): GraphNode {
  if (!isRecord(payload)) throw new Error(`Graph node at index ${index} must be an object.`);
  if (typeof payload.id !== 'string') throw new Error(`Graph node at index ${index} has malformed id.`);
  if (typeof payload.label !== 'string') throw new Error(`Graph node at index ${index} has malformed label.`);
  if (typeof payload.type !== 'string' || !graphNodeTypes.has(payload.type as GraphNodeType)) {
    throw new Error(`Graph node at index ${index} has unsupported type.`);
  }

  return {
    id: payload.id,
    label: payload.label,
    type: payload.type as GraphNodeType,
    group: typeof payload.group === 'string' ? payload.group : undefined,
    metadata: isRecord(payload.metadata) ? payload.metadata : {},
  };
}

function parseGraphEdge(payload: unknown, index: number): GraphEdge {
  if (!isRecord(payload)) throw new Error(`Graph edge at index ${index} must be an object.`);
  if (typeof payload.id !== 'string') throw new Error(`Graph edge at index ${index} has malformed id.`);
  if (typeof payload.source !== 'string') throw new Error(`Graph edge at index ${index} has malformed source.`);
  if (typeof payload.target !== 'string') throw new Error(`Graph edge at index ${index} has malformed target.`);

  return {
    id: payload.id,
    source: payload.source,
    target: payload.target,
    label: typeof payload.label === 'string' ? payload.label : undefined,
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}
