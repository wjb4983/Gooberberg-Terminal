import type { ModelCatalogItem } from '../api/modelCatalog';

export function recoverSelectedFamily(selectedFamily: string, catalog: ModelCatalogItem[]): { nextFamily: string; invalidFamily: string | null } {
  const firstFamily = catalog[0]?.model_family ?? '';
  if (!selectedFamily) {
    return { nextFamily: firstFamily, invalidFamily: null };
  }
  if (catalog.some((entry) => entry.model_family === selectedFamily)) {
    return { nextFamily: selectedFamily, invalidFamily: null };
  }
  return { nextFamily: firstFamily, invalidFamily: selectedFamily };
}

export function pruneCompareFamilies(compareFamilies: string[], catalog: ModelCatalogItem[]): string[] {
  return compareFamilies.filter((family) => catalog.some((entry) => entry.model_family === family));
}

