import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import http from 'node:http';
import https from 'node:https';
import type { IncomingHttpHeaders } from 'node:http';
import type { AddressInfo } from 'node:net';

const DEV_API_PROXY_PATH = '/__gb_api_proxy';
const VITE_HOST = process.env.GB_VITE_HOST;

function toRequestHeaders(headers: IncomingHttpHeaders, targetUrl: URL): Record<string, string | string[]> {
  const forwardedHeaders: Record<string, string | string[]> = {};

  Object.entries(headers).forEach(([name, value]) => {
    if (typeof value === 'undefined') {
      return;
    }
    if (['connection', 'content-length', 'host', 'origin', 'referer'].includes(name.toLowerCase())) {
      return;
    }
    forwardedHeaders[name] = value;
  });

  forwardedHeaders.host = targetUrl.host;
  return forwardedHeaders;
}

function devApiProxyPlugin() {
  return {
    name: 'gb-dev-api-proxy',
    configureServer(server) {
      server.middlewares.use(DEV_API_PROXY_PATH, (request, response) => {
        const requestUrl = new URL(request.url ?? '', 'http://localhost');
        const rawTarget = requestUrl.searchParams.get('url');
        if (!rawTarget) {
          response.statusCode = 400;
          response.end('Missing url query parameter.');
          return;
        }

        let targetUrl: URL;
        try {
          targetUrl = new URL(rawTarget);
        } catch {
          response.statusCode = 400;
          response.end('Invalid proxy target URL.');
          return;
        }

        if (targetUrl.protocol !== 'http:' && targetUrl.protocol !== 'https:') {
          response.statusCode = 400;
          response.end('Proxy target URL must use http or https.');
          return;
        }

        const client = targetUrl.protocol === 'https:' ? https : http;
        const proxyRequest = client.request(
          targetUrl,
          {
            method: request.method,
            headers: toRequestHeaders(request.headers, targetUrl),
          },
          (proxyResponse) => {
            response.statusCode = proxyResponse.statusCode ?? 502;
            Object.entries(proxyResponse.headers).forEach(([name, value]) => {
              if (typeof value !== 'undefined') {
                response.setHeader(name, value);
              }
            });
            proxyResponse.pipe(response);
          },
        );

        proxyRequest.on('error', (error: NodeJS.ErrnoException) => {
          response.statusCode = 502;
          response.setHeader('content-type', 'application/json');
          response.end(JSON.stringify({
            error: 'dev_api_proxy_failed',
            message: error.message,
            code: error.code,
            address: error.address,
            port: error.port,
          }));
        });

        request.pipe(proxyRequest);
      });

      server.httpServer?.once('listening', () => {
        const address = server.httpServer?.address() as AddressInfo | null;
        if (address) {
          server.config.logger.info(`  API proxy: http://localhost:${address.port}${DEV_API_PROXY_PATH}?url=<encoded-api-url>`);
        }
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), devApiProxyPlugin()],
  clearScreen: false,
  server: {
    host: VITE_HOST || undefined,
    port: 1420,
    strictPort: true,
  },
});
