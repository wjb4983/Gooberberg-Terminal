import type { WebSocketTopic } from '@gb/schemas';
import { useEffect, useMemo, useRef, useState } from 'react';

import { createDesktopApiClient, getRuntimeTransportSettings } from '../api/client';
import { useOperatorConsole } from '../context/OperatorConsoleContext';
import { ConnectionSupervisor, type CircuitState } from '../connectivity/connectionSupervisor';

interface UseResumableTopicStreamOptions<TPayload> {
  baseUrl: string;
  topic: WebSocketTopic;
  parsePayload: (payload: unknown) => TPayload | null;
  maxItems?: number;
  pollIntervalMs?: number;
  pollFallback?: () => Promise<TPayload[]>;
}

export function useResumableTopicStream<TPayload>(
  options: UseResumableTopicStreamOptions<TPayload>,
) {
  const {
    baseUrl,
    topic,
    parsePayload,
    maxItems = 100,
    pollIntervalMs = 5_000,
    pollFallback,
  } = options;
  const client = useMemo(() => createDesktopApiClient({ baseHttpUrl: baseUrl }), [baseUrl]);
  const runtimeTransportSettings = useMemo(() => getRuntimeTransportSettings(), []);
  const supervisor = useMemo(() => new ConnectionSupervisor(), []);
  const { reportWebSocketStatus, pushToast } = useOperatorConsole();
  const [items, setItems] = useState<TPayload[]>([]);
  const [connectionState, setConnectionState] = useState<
    'connecting' | 'connected' | 'reconnecting' | 'closed'
  >('connecting');
  const [circuitState, setCircuitState] = useState<CircuitState>('closed');
  const lastSeqRef = useRef<number | undefined>(undefined);

  useEffect(() => {
    return supervisor.subscribe((snapshot) => {
      setCircuitState(snapshot.circuitState);
      reportWebSocketStatus(`${connectionState}/${snapshot.circuitState}`);
    });
  }, [connectionState, reportWebSocketStatus, supervisor]);

  useEffect(() => {
    const connection = client.connectTopicWebSocket({
      topics: [topic],
      minBackoffMs: runtimeTransportSettings.wsReconnectMinMs,
      maxBackoffMs: runtimeTransportSettings.wsReconnectMaxMs,
      maxReconnectsPerWindow: runtimeTransportSettings.wsMaxReconnectsPerWindow,
      reconnectWindowMs: runtimeTransportSettings.wsReconnectWindowMs,
      getResumeSeq: () => lastSeqRef.current,
      onStatus: (nextStatus) => {
        setConnectionState(nextStatus);
        if (nextStatus === 'connected') {
          supervisor.recordSuccess();
          return;
        }
        if (nextStatus === 'reconnecting') {
          supervisor.markRetrying();
        }
      },
      onControlMessage: (message) => {
        if (message.type === 'replay_required') {
          supervisor.recordFailure('Replay cursor outside server window');
          pushToast({
            message: 'Realtime stream exceeded replay window. Running fallback resync.',
            tone: 'warning',
          });
        }
      },
      onReplayMiss: () => {
        lastSeqRef.current = undefined;
        if (pollFallback) {
          void pollFallback()
            .then((nextItems) => setItems(nextItems.slice(0, maxItems)))
            .catch(() => undefined);
        }
      },
      onEvent: (event) => {
        if (event.topic !== topic) {
          return;
        }

        if (lastSeqRef.current !== undefined && event.seq > lastSeqRef.current + 1) {
          supervisor.recordFailure(
            `Sequence gap detected: expected ${lastSeqRef.current + 1}, got ${event.seq}`,
          );
          pushToast({
            message: `Realtime gap detected for ${topic}; running resync fallback.`,
            tone: 'warning',
          });
          if (pollFallback) {
            void pollFallback()
              .then((nextItems) => setItems(nextItems.slice(0, maxItems)))
              .catch(() => undefined);
          }
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
  }, [
    client,
    topic,
    parsePayload,
    maxItems,
    pollFallback,
    pushToast,
    runtimeTransportSettings.wsReconnectMaxMs,
    runtimeTransportSettings.wsReconnectMinMs,
    runtimeTransportSettings.wsMaxReconnectsPerWindow,
    runtimeTransportSettings.wsReconnectWindowMs,
    supervisor,
  ]);

  useEffect(() => {
    if (!pollFallback || connectionState === 'connected') {
      return;
    }

    const interval = window.setInterval(() => {
      void pollFallback()
        .then((nextItems) => {
          if (!Array.isArray(nextItems) || nextItems.length === 0) {
            return;
          }
          setItems(nextItems.slice(0, maxItems));
        })
        .catch(() => {
          // Best effort fallback polling.
        });
    }, pollIntervalMs);

    return () => {
      window.clearInterval(interval);
    };
  }, [connectionState, maxItems, pollFallback, pollIntervalMs]);

  return { items, connectionState, circuitState, lastSeq: lastSeqRef.current };
}
