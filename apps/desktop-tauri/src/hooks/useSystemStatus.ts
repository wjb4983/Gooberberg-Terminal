import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import type { HealthResponse } from '@gb/schemas';

import { createDesktopApiClient } from '../api/client';

export function useSystemStatus(baseUrl: string) {
  const client = useMemo(() => createDesktopApiClient({ baseHttpUrl: baseUrl }), [baseUrl]);

  return useQuery<HealthResponse>({
    queryKey: ['system', 'health', baseUrl],
    queryFn: () => client.getHealth(),
  });
}
