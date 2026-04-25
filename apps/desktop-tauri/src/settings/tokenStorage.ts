import { invoke } from '@tauri-apps/api/core';

import type { ApiCredentials } from '../types/api';

export interface TokenStorage {
  save(credentials: ApiCredentials): Promise<void>;
  getToken(): Promise<string>;
  clear(): Promise<void>;
}

class TauriTokenStorage implements TokenStorage {
  async save(credentials: ApiCredentials): Promise<void> {
    const token = credentials.token.trim();
    if (!token) {
      await this.clear();
      return;
    }
    await invoke('save_api_token', { token });
  }

  async getToken(): Promise<string> {
    return invoke<string>('get_api_token');
  }

  async clear(): Promise<void> {
    await invoke('delete_api_token');
  }
}

class InMemoryTokenStorage implements TokenStorage {
  private static token = '';

  async save(credentials: ApiCredentials): Promise<void> {
    InMemoryTokenStorage.token = credentials.token.trim();
  }

  async getToken(): Promise<string> {
    return InMemoryTokenStorage.token;
  }

  async clear(): Promise<void> {
    InMemoryTokenStorage.token = '';
  }
}

class BrowserLocalTokenStorage implements TokenStorage {
  private readonly key = 'desktop-tauri.api-token.v1';

  async save(credentials: ApiCredentials): Promise<void> {
    const token = credentials.token.trim();
    if (!token) {
      await this.clear();
      return;
    }
    localStorage.setItem(this.key, token);
  }

  async getToken(): Promise<string> {
    return localStorage.getItem(this.key) ?? '';
  }

  async clear(): Promise<void> {
    localStorage.removeItem(this.key);
  }
}

export function createTokenStorage(): TokenStorage {
  if (typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window) {
    return new TauriTokenStorage();
  }

  if (typeof window !== 'undefined' && window.localStorage) {
    return new BrowserLocalTokenStorage();
  }

  return new InMemoryTokenStorage();
}
