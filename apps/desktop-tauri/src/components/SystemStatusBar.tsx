import { useQuery } from '@tanstack/react-query';
import type { HealthResponse, QueueHealthResponse } from '@gb/schemas';

type IndicatorState = 'healthy' | 'degraded' | 'offline';

interface SystemStatusBarProps {
  baseUrl: string;
  wsStatus: string;
}

interface ProbeResult<T> {
  ok: boolean;
  data?: T;
  detail: string;
}

interface StatusSnapshot {
  aggregate: IndicatorState;
  liveness: ProbeResult<{ status: string }>;
  apiHealth: ProbeResult<HealthResponse>;
  queueHealth: ProbeResult<QueueHealthResponse>;
  webSocket: ProbeResult<{ status: string }>;
}

function normalizeBaseUrl(baseUrl: string): string {
  return baseUrl.replace(/\/$/, '');
}

async function probeLiveness(baseUrl: string): Promise<ProbeResult<{ status: string }>> {
  try {
    const response = await fetch(`${normalizeBaseUrl(baseUrl)}/healthz`, { headers: { Accept: 'application/json' } });
    if (!response.ok) {
      return { ok: false, detail: `HTTP ${response.status}` };
    }

    const payload = await response.json() as { status?: string };
    if (payload.status !== 'ok') {
      return { ok: false, detail: `unexpected status: ${String(payload.status ?? 'unknown')}` };
    }

    return { ok: true, data: { status: payload.status }, detail: 'liveness endpoint reachable' };
  } catch (error) {
    return { ok: false, detail: error instanceof Error ? error.message : 'request failed' };
  }
}

async function probeApiHealth(baseUrl: string): Promise<ProbeResult<HealthResponse>> {
  try {
    const response = await fetch(`${normalizeBaseUrl(baseUrl)}/api/v1/health`, { headers: { Accept: 'application/json' } });
    if (!response.ok) {
      return { ok: false, detail: `HTTP ${response.status}` };
    }

    const payload = await response.json() as Partial<HealthResponse>;
    if (payload.status !== 'ok') {
      return { ok: false, detail: `unexpected status: ${String(payload.status ?? 'unknown')}` };
    }

    return { ok: true, data: payload as HealthResponse, detail: `status=${payload.status}` };
  } catch (error) {
    return { ok: false, detail: error instanceof Error ? error.message : 'request failed' };
  }
}

async function probeQueueHealth(baseUrl: string): Promise<ProbeResult<QueueHealthResponse>> {
  try {
    const response = await fetch(`${normalizeBaseUrl(baseUrl)}/api/v1/health/queue`, { headers: { Accept: 'application/json' } });
    if (!response.ok) {
      return { ok: false, detail: `HTTP ${response.status}` };
    }

    const payload = await response.json() as {
      status?: string;
      queue_depth?: number | null;
      worker_heartbeat_at?: string | null;
      worker_heartbeat_age_seconds?: number | null;
      detail?: string;
    };
    if (typeof payload.status !== 'string') {
      return { ok: false, detail: 'queue health payload missing status' };
    }

    return {
      ok: true,
      data: {
        status: payload.status,
        queueDepth: payload.queue_depth ?? null,
        workerHeartbeatAt: payload.worker_heartbeat_at ?? null,
        workerHeartbeatAgeSeconds: payload.worker_heartbeat_age_seconds ?? null,
        detail: payload.detail ?? '',
      },
      detail: payload.detail ?? `status=${payload.status}`,
    };
  } catch (error) {
    return { ok: false, detail: error instanceof Error ? error.message : 'request failed' };
  }
}

async function probeWebSocket(baseUrl: string): Promise<ProbeResult<{ status: string }>> {
  if (typeof WebSocket === 'undefined') {
    return { ok: false, detail: 'WebSocket is unavailable in this runtime' };
  }

  const wsUrl = `${normalizeBaseUrl(baseUrl).replace(/^http/, 'ws')}/ws`;
  return new Promise((resolve) => {
    let settled = false;
    const socket = new WebSocket(wsUrl);
    const timeout = window.setTimeout(() => {
      if (settled) {
        return;
      }
      settled = true;
      socket.close();
      resolve({ ok: false, detail: 'websocket probe timed out' });
    }, 5_000);

    socket.addEventListener('open', () => {
      if (settled) {
        return;
      }
      settled = true;
      window.clearTimeout(timeout);
      socket.close();
      resolve({ ok: true, data: { status: 'connected' }, detail: 'websocket endpoint reachable' });
    });

    socket.addEventListener('error', () => {
      if (settled) {
        return;
      }
      settled = true;
      window.clearTimeout(timeout);
      resolve({ ok: false, detail: 'websocket connection failed' });
    });
  });
}

function toIndicatorFromApiHealth(health?: HealthResponse): IndicatorState {
  if (!health) {
    return 'offline';
  }
  return health.status === 'ok' ? 'healthy' : 'degraded';
}

function toIndicatorFromQueueHealth(health?: QueueHealthResponse): IndicatorState {
  if (!health) {
    return 'offline';
  }
  if (health.status === 'ok') {
    return 'healthy';
  }
  return health.status === 'degraded' ? 'degraded' : 'offline';
}

function computeAggregate(snapshot: Omit<StatusSnapshot, 'aggregate'>): IndicatorState {
  const indicators: IndicatorState[] = [
    snapshot.liveness.ok ? 'healthy' : 'offline',
    snapshot.apiHealth.ok ? toIndicatorFromApiHealth(snapshot.apiHealth.data) : 'offline',
    snapshot.queueHealth.ok ? toIndicatorFromQueueHealth(snapshot.queueHealth.data) : 'offline',
    snapshot.webSocket.ok ? 'healthy' : 'offline',
  ];

  if (indicators.every((item) => item === 'offline')) {
    return 'offline';
  }

  if (indicators.every((item) => item === 'healthy')) {
    return 'healthy';
  }

  return 'degraded';
}

function formatTimestamp(timestamp: number): string {
  if (!timestamp) {
    return 'never';
  }
  return new Date(timestamp).toLocaleString();
}

export function SystemStatusBar({ baseUrl, wsStatus }: SystemStatusBarProps): JSX.Element {
  const { data, isLoading, dataUpdatedAt } = useQuery<StatusSnapshot>({
    queryKey: ['system', 'status-bar', baseUrl],
    queryFn: async () => {
      const [livenessResult, apiResult, queueResult, webSocketResult] = await Promise.allSettled([
        probeLiveness(baseUrl),
        probeApiHealth(baseUrl),
        probeQueueHealth(baseUrl),
        probeWebSocket(baseUrl),
      ]);

      const liveness: ProbeResult<{ status: string }> =
        livenessResult.status === 'fulfilled'
          ? livenessResult.value
          : { ok: false, detail: livenessResult.reason instanceof Error ? livenessResult.reason.message : 'request failed' };

      const apiHealth: ProbeResult<HealthResponse> =
        apiResult.status === 'fulfilled'
          ? apiResult.value
          : { ok: false, detail: apiResult.reason instanceof Error ? apiResult.reason.message : 'request failed' };

      const queueHealth: ProbeResult<QueueHealthResponse> =
        queueResult.status === 'fulfilled'
          ? queueResult.value
          : { ok: false, detail: queueResult.reason instanceof Error ? queueResult.reason.message : 'request failed' };

      const webSocket: ProbeResult<{ status: string }> =
        webSocketResult.status === 'fulfilled'
          ? webSocketResult.value
          : { ok: false, detail: webSocketResult.reason instanceof Error ? webSocketResult.reason.message : 'request failed' };

      const snapshotWithoutAggregate = { liveness, apiHealth, queueHealth, webSocket };
      return {
        ...snapshotWithoutAggregate,
        aggregate: computeAggregate(snapshotWithoutAggregate),
      };
    },
    refetchInterval: 10_000,
    staleTime: 10_000,
  });

  const aggregate = data?.aggregate ?? (isLoading ? 'degraded' : 'offline');

  return (
    <div
      className="system-status-bar"
      title="System health blends liveness, API health, and queue/worker heartbeat checks. Degraded means partial issues; offline means unreachable."
    >
      <span className="status-item">
        <span className={`status-dot status-${aggregate}`} aria-hidden="true" />
        System: <strong>{aggregate}</strong>
      </span>
      <span className="status-item" title={data?.liveness?.detail ?? 'Liveness endpoint not queried yet.'}>
        /healthz: <strong>{data?.liveness?.ok ? 'healthy' : 'offline'}</strong>
      </span>
      <span className="status-item" title={data?.apiHealth?.detail ?? 'Versioned API health not queried yet.'}>
        /api/v1/health: <strong>{data?.apiHealth?.ok ? toIndicatorFromApiHealth(data.apiHealth.data) : 'offline'}</strong>
      </span>
      <span className="status-item" title={data?.queueHealth?.detail ?? 'Queue health not queried yet.'}>
        Queue/worker: <strong>{data?.queueHealth?.ok ? toIndicatorFromQueueHealth(data.queueHealth.data) : 'offline'}</strong>
      </span>
      <span className="status-item" title="The most recent refresh that completed successfully for this status panel.">
        Last refresh: <strong>{formatTimestamp(dataUpdatedAt)}</strong>
      </span>
      <span className="status-item" title={data?.webSocket?.detail ?? 'WebSocket endpoint not queried yet.'}>
        WebSocket: <strong>{data?.webSocket?.ok ? 'healthy' : (wsStatus || 'offline')}</strong>
      </span>
    </div>
  );
}
