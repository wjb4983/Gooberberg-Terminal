import assert from 'node:assert/strict';
import test from 'node:test';

import { requestJson } from './requestJson';
import { isModelConfigCreateServerFailure } from './modelConfigRecovery';

const baseUrl = 'http://127.0.0.1:8000';

test('requestJson includes deterministic error correlation fields for 404 catalog family lookups', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () =>
    new Response(
      JSON.stringify({
        request_id: 'req-404-family',
        error_code: 'http_404',
        detail: 'model catalog entry not found',
        status: 404,
      }),
      { status: 404, headers: { 'content-type': 'application/json' } },
    );

  try {
    await assert.rejects(
      () => requestJson(baseUrl, '/api/v1/models/deployments/catalog/unknown-family'),
      (error: unknown) => {
        assert.ok(error instanceof Error);
        assert.match(error.message, /Request failed \(404\)/);
        assert.match(error.message, /request_id=req-404-family/);
        assert.match(error.message, /error_code=http_404/);
        assert.match(error.message, /model catalog entry not found/);
        return true;
      },
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('requestJson includes deterministic error correlation fields for unknown model config id', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () =>
    new Response(
      JSON.stringify({
        request_id: 'req-404-config',
        error_code: 'http_404',
        detail: 'model config not found',
        status: 404,
      }),
      { status: 404, headers: { 'content-type': 'application/json' } },
    );

  try {
    await assert.rejects(
      () => requestJson(baseUrl, '/api/v1/model-configs/00000000-0000-0000-0000-000000000000'),
      (error: unknown) => {
        assert.ok(error instanceof Error);
        assert.match(error.message, /Request failed \(404\)/);
        assert.match(error.message, /request_id=req-404-config/);
        assert.match(error.message, /error_code=http_404/);
        assert.match(error.message, /model config not found/);
        return true;
      },
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('model config recovery no longer depends on generic 500-only failures', () => {
  const regression = new Error('Request failed (422) for POST http://127.0.0.1:8000/api/v1/model-configs [request_id=req-1, error_code=http_422]: invalid config payload');
  assert.equal(isModelConfigCreateServerFailure(regression), false);

  const legacy500 = new Error('Request failed (500) for POST http://127.0.0.1:8000/api/v1/model-configs: Internal server error');
  assert.equal(isModelConfigCreateServerFailure(legacy500), true);
});
