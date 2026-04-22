import type { WebSocketTopic } from '@gb/schemas';
import { useEffect, useMemo, useRef, useState } from 'react';

import { createDesktopApiClient } from '../api/client';

interface UseResumableTopicStreamOptions<TPayload> {
  baseUrl: string;
  topic: WebSocketTopic;
  parsePayload: (payload: unknown) => TPayload | null;
  maxItems?: number;
  pollIntervalMs?: number;
  pollFallback?: () => Promise<TPayload[]>;
}

export function useResumableTopicStream<TPayload>(options: UseResumableTopicStreamOptions<TPayload>) {
  const {
    baseUrl,
    topic,
    parsePayload,
    maxItems = 100,
    pollIntervalMs = 5_000,
    pollFallback,
  } = options;
  const client = useMemo(() => createDesktopApiClient({ baseHttpUrl: baseUrl }), [baseUrl]);
  const [items, setItems] = useState<TPayload[]>([]);
  const [connectionState, setConnectionState] = useState<'connecting' | 'connected' | 'reconnecting' | 'closed'>('connecting');
  const lastSeqRef = useRef<number | undefined>(undefined);

  useEffect(() => {
    const connection = client.connectTopicWebSocket({
      topics: [topic],
      getResumeSeq: () => lastSeqRef.current,
      onStatus: setConnectionState,
      onEvent: (event) => {
        if (event.topic !== topic) {
          return;
        }

        lastSeqRef.current = event.seq;
        const parsed = parsePayload(event.payload);
        if (!parsed) {
          return;
        }

        setItems((previous) => [parsed, ...previous].slice(0, maxItems));
      },
    });

    return () => {
      connection.close();
    };
  }, [client, topic, parsePayload, maxItems]);

  useEffect(() => {
    if (!pollFallback || connectionState === 'connected') {
      return;
    }

    const interval = window.setInterval(() => {
      void pollFallback().then((nextItems) => {
        if (!Array.isArray(nextItems) || nextItems.length === 0) {
          return;
        }
        setItems(nextItems.slice(0, maxItems));
      }).catch(() => {
        // Best effort fallback polling.
      });
    }, pollIntervalMs);

    return () => {
      window.clearInterval(interval);
    };
  }, [connectionState, maxItems, pollFallback, pollIntervalMs]);

  return { items, connectionState, lastSeq: lastSeqRef.current };
}
