interface ModelConfigDescriptor {
  model_family: string;
  config: Record<string, unknown>;
}

interface ModelConfigWithId extends ModelConfigDescriptor {
  id: string;
  updated_at?: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function stableSerialize(value: unknown): string {
  if (value === null) {
    return 'null';
  }
  const valueType = typeof value;
  if (valueType === 'string' || valueType === 'number' || valueType === 'boolean') {
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) {
    return `[${value.map((item) => stableSerialize(item)).join(',')}]`;
  }
  if (isRecord(value)) {
    const keys = Object.keys(value).sort((left, right) => left.localeCompare(right));
    return `{${keys.map((key) => `${JSON.stringify(key)}:${stableSerialize(value[key])}`).join(',')}}`;
  }
  return JSON.stringify(String(value));
}

function normalizeIdentityValue(value: unknown): string {
  return typeof value === 'string' ? value.trim().toLowerCase() : '';
}

function configIdentity(modelFamily: string, config: Record<string, unknown>): string {
  return [
    modelFamily.trim().toLowerCase(),
    normalizeIdentityValue(config.name),
    normalizeIdentityValue(config.version),
    normalizeIdentityValue(config.task_type),
    normalizeIdentityValue(config.subtask_type),
    normalizeIdentityValue(config.data_profile),
    normalizeIdentityValue(config.data_type),
  ].join('|');
}

function isValidDateString(value: string | undefined): boolean {
  if (!value) {
    return false;
  }
  return Number.isFinite(Date.parse(value));
}

function compareByUpdatedAtDescending(left: ModelConfigWithId, right: ModelConfigWithId): number {
  if (!isValidDateString(left.updated_at) && !isValidDateString(right.updated_at)) {
    return 0;
  }
  if (!isValidDateString(left.updated_at)) {
    return 1;
  }
  if (!isValidDateString(right.updated_at)) {
    return -1;
  }
  return Date.parse(right.updated_at as string) - Date.parse(left.updated_at as string);
}

export function isModelConfigCreateServerFailure(error: unknown): boolean {
  if (!(error instanceof Error)) {
    return false;
  }
  return error.message.includes('Request failed (500)') && error.message.includes('POST') && error.message.includes('/api/v1/model-configs');
}

export function findEquivalentModelConfig<T extends ModelConfigWithId>(
  existingConfigs: T[],
  desired: ModelConfigDescriptor,
): T | null {
  const desiredFamily = desired.model_family.trim().toLowerCase();
  const desiredConfigKey = stableSerialize(desired.config);
  const exact = existingConfigs.find(
    (item) => item.model_family.trim().toLowerCase() === desiredFamily && stableSerialize(item.config) === desiredConfigKey,
  );
  if (exact) {
    return exact;
  }

  const desiredIdentity = configIdentity(desired.model_family, desired.config);
  const identityMatches = existingConfigs
    .filter((item) => configIdentity(item.model_family, item.config) === desiredIdentity)
    .sort(compareByUpdatedAtDescending);
  return identityMatches[0] ?? null;
}
