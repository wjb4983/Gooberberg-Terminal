import { parseServiceHealth } from '@gb/api-client';
import type { ServiceHealth } from '@gb/schemas';
import { formatHealthLabel } from '@gb/ui-components';

const payload: ServiceHealth = {
  service: 'desktop-shell',
  status: 'healthy',
  checkedAtIso: new Date().toISOString(),
};

const parsed = parseServiceHealth(payload);

export const appHealthLabel = parsed ? formatHealthLabel(parsed) : 'desktop-shell: unknown';
