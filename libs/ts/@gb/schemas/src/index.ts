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

export function parseGraphTopology(payload: unknown): GraphTopology {
  if (!isRecord(payload)) throw new Error('Graph topology payload must be an object.');
  if (!Array.isArray(payload.nodes) || !Array.isArray(payload.edges)) {
    throw new Error('Graph topology payload is missing nodes or edges arrays.');
  }

  const nodes = payload.nodes.map((node, index) => parseGraphNode(node, index));
  const edges = payload.edges.map((edge, index) => parseGraphEdge(edge, index));
  return { nodes, edges };
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
