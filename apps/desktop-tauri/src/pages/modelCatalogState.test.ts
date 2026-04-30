import assert from 'node:assert/strict';
import test from 'node:test';
import { pruneCompareFamilies, recoverSelectedFamily } from './modelCatalogState';

const catalog = [
  { model_family: 'alpha', model_name: 'Alpha', description: '', tags: [], validator_adapter: 'a' },
  { model_family: 'beta', model_name: 'Beta', description: '', tags: [], validator_adapter: 'b' },
];

test('invalid family in URL is automatically recovered', () => {
  const recovered = recoverSelectedFamily('missing', catalog);
  assert.equal(recovered.nextFamily, 'alpha');
  assert.equal(recovered.invalidFamily, 'missing');
});

test('compare set is cleaned when families are removed', () => {
  const nextCompare = pruneCompareFamilies(['alpha', 'missing'], catalog);
  assert.deepEqual(nextCompare, ['alpha']);
});

test('direct load with empty catalog clears selected family', () => {
  const recovered = recoverSelectedFamily('alpha', []);
  assert.equal(recovered.nextFamily, '');
  assert.equal(recovered.invalidFamily, 'alpha');
});
