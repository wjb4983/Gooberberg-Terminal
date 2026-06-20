import { GbApiClient, type ApiClientOptions } from '@gb/api-client';

import { resolveAuthorizationHeader } from './authHeaders';
import { normalizeApiBaseUrl } from '../settings/preferences';

export function desktopFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  return fetch(input, init);
}

const runtimeTransportSettings = {
  httpDefaultTimeoutMs: Number(import.meta.env.VITE_GB_HTTP_DEFAULT_TIMEOUT_MS ?? 10_000),
  httpRetryEnabled: (import.meta.env.VITE_GB_HTTP_RETRY_ENABLED ?? 'true') !== 'false',
  httpCircuitEnabled: (import.meta.env.VITE_GB_HTTP_CIRCUIT_ENABLED ?? 'true') !== 'false',
  wsReconnectMinMs: Number(import.meta.env.VITE_GB_WS_RECONNECT_MIN_MS ?? 500),
  wsReconnectMaxMs: Number(import.meta.env.VITE_GB_WS_RECONNECT_MAX_MS ?? 10_000),
  wsMaxReconnectsPerWindow: Number(import.meta.env.VITE_GB_WS_MAX_RECONNECTS_PER_WINDOW ?? 8),
  wsReconnectWindowMs: Number(import.meta.env.VITE_GB_WS_RECONNECT_WINDOW_MS ?? 30_000),
};

export function createDesktopApiClient(
  options: Omit<ApiClientOptions, 'authHeaderProvider'>,
): GbApiClient {
  return new GbApiClient({
    ...options,
    baseHttpUrl: normalizeApiBaseUrl(options.baseHttpUrl),
    fetchImpl: options.fetchImpl ?? desktopFetch,
    authHeaderProvider: (path) => resolveAuthorizationHeader(path),
    onTelemetry: ({ counter, value, tags }) => {
      console.debug(`[transport-telemetry] ${counter}=${value}`, tags ?? {});
    },
    transportPolicy: {
      defaultTimeoutMs: runtimeTransportSettings.httpDefaultTimeoutMs,
      interactiveTimeoutMs: runtimeTransportSettings.httpDefaultTimeoutMs,
      heavyReadTimeoutMs: Math.max(runtimeTransportSettings.httpDefaultTimeoutMs, 30_000),
      retry: {
        maxRetries: runtimeTransportSettings.httpRetryEnabled ? 2 : 0,
      },
      circuitBreaker: {
        enabled: runtimeTransportSettings.httpCircuitEnabled,
      },
    },
  });
}

export function getRuntimeTransportSettings() {
  return runtimeTransportSettings;
}
