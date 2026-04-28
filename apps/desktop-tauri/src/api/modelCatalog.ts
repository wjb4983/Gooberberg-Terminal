import { requestJson } from './requestJson';

export interface ModelCatalogItem {
  model_family: string;
  model_name: string;
  description: string;
  tags: string[];
  validator_adapter: string;
}

export async function fetchModelCatalogList(baseUrl: string): Promise<ModelCatalogItem[]> {
  return requestJson<ModelCatalogItem[]>(baseUrl, '/api/v1/models/deployments/catalog');
}

export async function fetchModelCatalogItem(baseUrl: string, family: string): Promise<ModelCatalogItem> {
  return requestJson<ModelCatalogItem>(baseUrl, `/api/v1/models/deployments/catalog/${encodeURIComponent(family)}`);
}
