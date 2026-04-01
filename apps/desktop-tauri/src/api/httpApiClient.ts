import { parseServiceHealth } from '@gb/api-client';
import type { ServiceHealth } from '@gb/schemas';

import type { ApiClient } from '../types/api';

export class HttpApiClient implements ApiClient {
  constructor(private readonly baseUrl: string) {}

  async getHealth(): Promise<ServiceHealth> {
    const response = await fetch(`${this.baseUrl}/health`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    });

    if (!response.ok) {
      throw new Error(`Health endpoint failed with status ${response.status}`);
    }

    const payload = (await response.json()) as unknown;
    const parsed = parseServiceHealth(payload);

    if (!parsed) {
      throw new Error('Health payload is malformed.');
    }

    return parsed;
  }
}
