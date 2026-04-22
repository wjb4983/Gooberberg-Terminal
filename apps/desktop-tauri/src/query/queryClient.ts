import { QueryClient, dehydrate, hydrate } from '@tanstack/react-query';

const CACHE_KEY = 'gb.desktop.query-cache.v1';

function shouldRetry(failureCount: number, error: unknown): boolean {
  if (failureCount >= 2) {
    return false;
  }

  if (error instanceof Error) {
    if (error.message.includes('status 401') || error.message.includes('status 403')) {
      return false;
    }
  }

  return true;
}

export function createQueryClient(): QueryClient {
  const client = new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60_000,
        gcTime: 30 * 60_000,
        refetchOnWindowFocus: false,
        retry: shouldRetry,
      },
      mutations: {
        retry: (failureCount, error) => shouldRetry(failureCount, error),
      },
    },
  });

  client.setQueryDefaults(['system', 'health'], {
    staleTime: 10_000,
    refetchInterval: 10_000,
  });

  client.setQueryDefaults(['jobs', 'status'], {
    staleTime: 2_000,
    refetchInterval: 2_000,
  });

  return client;
}

export function restorePersistedCache(queryClient: QueryClient): void {
  if (typeof window === 'undefined') {
    return;
  }

  const raw = window.localStorage.getItem(CACHE_KEY);
  if (!raw) {
    return;
  }

  try {
    hydrate(queryClient, JSON.parse(raw));
  } catch {
    window.localStorage.removeItem(CACHE_KEY);
  }
}

export function wireCachePersistence(queryClient: QueryClient): () => void {
  if (typeof window === 'undefined') {
    return () => {
      // no-op.
    };
  }

  let timeoutHandle: ReturnType<typeof setTimeout> | undefined;

  const unsubscribe = queryClient.getQueryCache().subscribe(() => {
    if (timeoutHandle) {
      window.clearTimeout(timeoutHandle);
    }

    timeoutHandle = window.setTimeout(() => {
      const state = dehydrate(queryClient, {
        shouldDehydrateQuery: (query) => query.state.status === 'success',
      });
      window.localStorage.setItem(CACHE_KEY, JSON.stringify(state));
    }, 250);
  });

  return () => {
    if (timeoutHandle) {
      window.clearTimeout(timeoutHandle);
    }
    unsubscribe();
  };
}
