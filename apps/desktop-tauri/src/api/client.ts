import { GbApiClient, type ApiClientOptions } from '@gb/api-client';

import { createTokenStorage } from '../settings/tokenStorage';

const tokenStorage = createTokenStorage();

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
  });
}
