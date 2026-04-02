import type { HealthResponse } from '@gb/schemas';

export function formatHealthLabel(health: HealthResponse): string {
  return `${health.service}: ${health.status}`;
}
