import { invoke } from '@tauri-apps/api/core';

import type { ApiCredentials } from '../types/api';

export interface TokenStorage {
  save(credentials: ApiCredentials): Promise<void>;
}

class TauriTokenStorage implements TokenStorage {
  async save(credentials: ApiCredentials): Promise<void> {
    await invoke('save_api_token', { token: credentials.token });
  }
}

class InMemoryTokenStorage implements TokenStorage {
  private token = '';

  async save(credentials: ApiCredentials): Promise<void> {
    this.token = credentials.token;
  }

  getToken(): string {
    return this.token;
  }
}

export function createTokenStorage(): TokenStorage {
  if (typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window) {
    return new TauriTokenStorage();
  }

  return new InMemoryTokenStorage();
}
