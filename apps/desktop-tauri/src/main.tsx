import React from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';

import { App } from './App';
import { createQueryClient, restorePersistedCache, wireCachePersistence } from './query/queryClient';
import './styles.css';

const queryClient = createQueryClient();
restorePersistedCache(queryClient);

const container = document.getElementById('root');

if (!container) {
  throw new Error('Root container not found. Expected element with id="root".');
}

createRoot(container).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <CachePersistenceBridge />
      <BrowserRouter>
        <App />
      </BrowserRouter>
      {import.meta.env.DEV ? <ReactQueryDevtools initialIsOpen={false} /> : null}
    </QueryClientProvider>
  </React.StrictMode>,
);

function CachePersistenceBridge(): null {
  React.useEffect(() => {
    return wireCachePersistence(queryClient);
  }, []);

  return null;
}
