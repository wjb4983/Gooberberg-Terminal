import type { ApiCredentials } from '../types/api';

export interface TokenStorage {
  save(credentials: ApiCredentials): Promise<void>;
  getToken(): Promise<string>;
  clear(): Promise<void>;
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
    globalThis.localStorage.setItem(this.key, token);
  }

  async getToken(): Promise<string> {
    return globalThis.localStorage.getItem(this.key) ?? '';
  }

  async clear(): Promise<void> {
    globalThis.localStorage.removeItem(this.key);
  }
}

export function createTokenStorage(): TokenStorage {
  if (typeof globalThis.localStorage !== 'undefined') {
    return new BrowserLocalTokenStorage();
  }

  return new InMemoryTokenStorage();
}
