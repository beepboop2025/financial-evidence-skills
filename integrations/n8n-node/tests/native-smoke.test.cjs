const {test} = require('node:test');
const assert = require('node:assert/strict');
const {spawnSync} = require('node:child_process');
const path = require('node:path');

test('immutable native-smoke candidate contract', () => {
  const result = spawnSync('python3', ['-B', path.join(__dirname, 'test_native_smoke.py')], {
    encoding: 'utf8', env: {...process.env, PYTHONDONTWRITEBYTECODE: '1'},
  });
  assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
});
