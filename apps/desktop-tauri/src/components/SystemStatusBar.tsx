import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import type { HealthResponse, QueueHealthResponse } from '@gb/schemas';

import { createDesktopApiClient } from '../api/client';

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
  const client = useMemo(() => createDesktopApiClient({ baseHttpUrl: baseUrl }), [baseUrl]);

  const { data, isLoading, dataUpdatedAt } = useQuery<StatusSnapshot>({
    queryKey: ['system', 'status-bar', baseUrl],
    queryFn: async () => {
      const [livenessResult, apiResult, queueResult] = await Promise.allSettled([
        probeLiveness(baseUrl),
        client.getHealth(),
        client.getQueueHealth(),
      ]);

      const liveness: ProbeResult<{ status: string }> =
        livenessResult.status === 'fulfilled'
          ? livenessResult.value
          : { ok: false, detail: livenessResult.reason instanceof Error ? livenessResult.reason.message : 'request failed' };

      const apiHealth: ProbeResult<HealthResponse> =
        apiResult.status === 'fulfilled'
          ? { ok: true, data: apiResult.value, detail: `status=${apiResult.value.status}` }
          : { ok: false, detail: apiResult.reason instanceof Error ? apiResult.reason.message : 'request failed' };

      const queueHealth: ProbeResult<QueueHealthResponse> =
        queueResult.status === 'fulfilled'
          ? {
            ok: true,
            data: queueResult.value,
            detail: queueResult.value.detail,
          }
          : { ok: false, detail: queueResult.reason instanceof Error ? queueResult.reason.message : 'request failed' };

      const snapshotWithoutAggregate = { liveness, apiHealth, queueHealth };
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
      <span className="status-item" title={data?.liveness.detail ?? 'Liveness endpoint not queried yet.'}>
        /healthz: <strong>{data?.liveness.ok ? 'healthy' : 'offline'}</strong>
      </span>
      <span className="status-item" title={data?.apiHealth.detail ?? 'Versioned API health not queried yet.'}>
        /api/v1/health: <strong>{data?.apiHealth.ok ? toIndicatorFromApiHealth(data.apiHealth.data) : 'offline'}</strong>
      </span>
      <span className="status-item" title={data?.queueHealth.detail ?? 'Queue health not queried yet.'}>
        Queue/worker: <strong>{data?.queueHealth.ok ? toIndicatorFromQueueHealth(data.queueHealth.data) : 'offline'}</strong>
      </span>
      <span className="status-item" title="The most recent refresh that completed successfully for this status panel.">
        Last refresh: <strong>{formatTimestamp(dataUpdatedAt)}</strong>
      </span>
      <span className="status-item">WebSocket: <strong>{wsStatus}</strong></span>
    </div>
  );
}
