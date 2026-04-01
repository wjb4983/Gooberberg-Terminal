import type { ServiceHealth } from '@gb/schemas';

export function parseServiceHealth(payload: unknown): ServiceHealth | null {
  if (typeof payload !== 'object' || payload === null) return null;

  const candidate = payload as Partial<ServiceHealth>;
  if (typeof candidate.service !== 'string') return null;
  if (candidate.status !== 'healthy' && candidate.status !== 'degraded' && candidate.status !== 'unhealthy') return null;
  if (typeof candidate.checkedAtIso !== 'string') return null;

  return candidate as ServiceHealth;
}
