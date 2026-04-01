import type { ServiceHealth } from '@gb/schemas';

export function formatHealthLabel(health: ServiceHealth): string {
  return `${health.service}: ${health.status}`;
}
