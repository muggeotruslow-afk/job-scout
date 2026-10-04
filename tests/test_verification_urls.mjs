import test from 'node:test';
import assert from 'node:assert/strict';
import { verificationUrl } from '../scripts/verification_urls.mjs';

test('Baidu internship detail disables the observed debugger-triggered blank redirect', () => {
  const input = 'https://talent.baidu.com/jobs/detail/INTERN/example-id';
  assert.equal(verificationUrl(input), input + '?dev=0');
});

test('preserves existing query and fragment and makes the setting idempotent', () => {
  const input = 'https://talent.baidu.com/jobs/detail/INTERN/example-id?source=campus&dev=1#description';
  const result = verificationUrl(input);
  assert.equal(result, 'https://talent.baidu.com/jobs/detail/INTERN/example-id?source=campus&dev=0#description');
  assert.equal(verificationUrl(result), result);
});

test('does not rewrite other hosts, schemes, routes, or invalid URLs', () => {
  for (const input of [
    'https://talent.baidu.com.evil.example/jobs/detail/INTERN/example-id',
    'https://other.example/jobs/detail/INTERN/example-id',
    'http://talent.baidu.com/jobs/detail/INTERN/example-id',
    'https://talent.baidu.com/jobs/list?recruitType=INTERN',
    'https://talent.baidu.com/jobs/detail/GRADUATE/example-id',
    'invalid',
  ]) assert.equal(verificationUrl(input), input);
});
