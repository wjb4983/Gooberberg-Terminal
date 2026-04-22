import { useMemo } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import { createDesktopApiClient } from '../api/client';

export function useJobActions(baseUrl: string, jobId: string) {
  const queryClient = useQueryClient();
  const client = useMemo(() => createDesktopApiClient({ baseHttpUrl: baseUrl }), [baseUrl]);

  const invalidate = async (): Promise<void> => {
    await queryClient.invalidateQueries({ queryKey: ['jobs'] });
  };

  const cancelJob = useMutation({
    mutationKey: ['jobs', 'cancel', baseUrl, jobId],
    mutationFn: () => client.cancelJob(jobId),
    onSuccess: () => invalidate(),
  });

  const retryJob = useMutation({
    mutationKey: ['jobs', 'retry', baseUrl, jobId],
    mutationFn: () => client.retryJob(jobId),
    onSuccess: () => invalidate(),
  });

  return { cancelJob, retryJob };
}
