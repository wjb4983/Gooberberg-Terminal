import { invoke } from '@tauri-apps/api/core';

import type { ApiCredentials } from '../types/api';

export interface TokenStorage {
  save(credentials: ApiCredentials): Promise<void>;
  getToken(): Promise<string>;
}

class TauriTokenStorage implements TokenStorage {
  async save(credentials: ApiCredentials): Promise<void> {
    await invoke('save_api_token', { token: credentials.token });
  }

  async getToken(): Promise<string> {
    return invoke<string>('get_api_token');
  }
}

class InMemoryTokenStorage implements TokenStorage {
  private token = '';

  async save(credentials: ApiCredentials): Promise<void> {
    this.token = credentials.token;
  }

  async getToken(): Promise<string> {
    return this.token;
  }
}

export function createTokenStorage(): TokenStorage {
  if (typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window) {
    return new TauriTokenStorage();
  }

  return new InMemoryTokenStorage();
}
