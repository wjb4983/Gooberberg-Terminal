export type HealthStatus = 'healthy' | 'degraded' | 'unhealthy';

export interface ServiceHealth {
  service: string;
  status: HealthStatus;
  checkedAtIso: string;
  message?: string;
}
