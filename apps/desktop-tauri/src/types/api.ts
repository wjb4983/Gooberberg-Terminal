import type { ServiceHealth } from '@gb/schemas';

export interface ApiClient {
  getHealth(): Promise<ServiceHealth>;
}

export interface ApiPreferences {
  baseUrl: string;
}

export interface ApiCredentials {
  token: string;
}
