import { GbApiClient, type ApiClientOptions } from '@gb/api-client';

import { createTokenStorage } from '../settings/tokenStorage';

const tokenStorage = createTokenStorage();

const runtimeTransportSettings = {
  httpDefaultTimeoutMs: Number(import.meta.env.VITE_GB_HTTP_DEFAULT_TIMEOUT_MS ?? 10_000),
  wsReconnectMinMs: Number(import.meta.env.VITE_GB_WS_RECONNECT_MIN_MS ?? 500),
  wsReconnectMaxMs: Number(import.meta.env.VITE_GB_WS_RECONNECT_MAX_MS ?? 10_000),
};

function shouldAttachAuthHeader(path: string): boolean {
  return !path.includes('/health');
}

async function resolveAuthorizationHeader(path: string): Promise<string | undefined> {
  if (!shouldAttachAuthHeader(path)) {
    return undefined;
  }

  const token = (await tokenStorage.getToken()).trim();
  if (!token) {
    return undefined;
  }

  return `Bearer ${token}`;
}

export function createDesktopApiClient(options: Omit<ApiClientOptions, 'authHeaderProvider'>): GbApiClient {
  return new GbApiClient({
    ...options,
    authHeaderProvider: (path) => resolveAuthorizationHeader(path),
    transportPolicy: {
      defaultTimeoutMs: runtimeTransportSettings.httpDefaultTimeoutMs,
      interactiveTimeoutMs: runtimeTransportSettings.httpDefaultTimeoutMs,
      heavyReadTimeoutMs: Math.max(runtimeTransportSettings.httpDefaultTimeoutMs, 30_000),
    },
  });
}

export function getRuntimeTransportSettings() {
  return runtimeTransportSettings;
}
