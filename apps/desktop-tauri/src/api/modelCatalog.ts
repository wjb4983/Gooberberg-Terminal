import { requestJson } from './requestJson';

export interface ModelCatalogItem {
  model_family: string;
  model_name: string;
  description: string;
  tags: string[];
  validator_adapter: string;
}

const CATALOG_LIST_PATHS = [
  '/api/v1/models/deployments/catalog',
  '/api/v1/models/catalog',
] as const;

const MODEL_FAMILY_LIST_PATHS = [
  '/api/v1/models/deployments/families',
  '/api/v1/models/families',
] as const;

function isNotFoundError(error: unknown): boolean {
  return error instanceof Error && /\(404\)/.test(error.message);
}

async function requestFromPaths<T>(baseUrl: string, paths: readonly string[]): Promise<T> {
  let lastNotFoundError: Error | null = null;

  for (const path of paths) {
    try {
      return await requestJson<T>(baseUrl, path);
    } catch (error) {
      if (isNotFoundError(error)) {
        lastNotFoundError = error instanceof Error ? error : new Error('Request failed (404).');
        continue;
      }
      throw error;
    }
  }

  if (lastNotFoundError) {
    throw lastNotFoundError;
  }
  throw new Error(`Request failed for all candidate paths: ${paths.join(', ')}`);
}

export async function fetchModelCatalogList(baseUrl: string): Promise<ModelCatalogItem[]> {
  try {
    return await requestFromPaths<ModelCatalogItem[]>(baseUrl, CATALOG_LIST_PATHS);
  } catch (error) {
    if (!isNotFoundError(error)) {
      throw error;
    }

    const families = await requestFromPaths<string[]>(baseUrl, MODEL_FAMILY_LIST_PATHS);
    return families.map((family) => ({
      model_family: family,
      model_name: family,
      description: 'Catalog metadata endpoint unavailable. Showing registered model family only.',
      tags: [],
      validator_adapter: family,
    }));
  }
}

export async function fetchModelCatalogItem(baseUrl: string, family: string): Promise<ModelCatalogItem> {
  const encodedFamily = encodeURIComponent(family);
  try {
    return await requestFromPaths<ModelCatalogItem>(baseUrl, [
      `/api/v1/models/deployments/catalog/${encodedFamily}`,
      `/api/v1/models/catalog/${encodedFamily}`,
    ]);
  } catch (error) {
    if (!isNotFoundError(error)) {
      throw error;
    }

    const catalog = await fetchModelCatalogList(baseUrl);
    const fallback = catalog.find((item) => item.model_family === family);
    if (fallback) {
      return fallback;
    }
    throw error;
  }
}
