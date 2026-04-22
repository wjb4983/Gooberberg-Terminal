import type { JobLifecyclePayload } from '@gb/schemas';
import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { parseJobLifecyclePayload } from '@gb/api-client';

import { createDesktopApiClient } from '../api/client';
import { useResumableTopicStream } from './useResumableTopicStream';

export function useJobLifecycle(baseUrl: string, jobId?: string) {
  const client = useMemo(() => createDesktopApiClient({ baseHttpUrl: baseUrl }), [baseUrl]);

  const statusQuery = useQuery({
    queryKey: ['jobs', 'status', baseUrl, jobId],
    queryFn: () => client.getJob(jobId ?? ''),
    enabled: Boolean(jobId),
  });

  const stream = useResumableTopicStream<JobLifecyclePayload>({
    baseUrl,
    topic: 'jobs',
    parsePayload: parseJobLifecyclePayload,
    pollFallback: jobId
      ? async () => {
          const events = await client.listJobEvents(jobId);
          return events.map((event) => ({
            job_id: event.id,
            trace_id: event.traceId,
            status: event.status,
            detail: event.detail,
            updated_at: event.updatedAtIso,
          }));
        }
      : undefined,
  });

  return {
    ...stream,
    statusQuery,
  };
}
