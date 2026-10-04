import test from 'node:test';import assert from 'node:assert/strict';
import {rejectUnsafeUrl,shouldRetryNavigation,checkUrlLivenessWithFallback} from '../scripts/liveness.mjs';
test('standalone verification rejects non-web and private targets',()=>{
 for(const url of ['file:///resume.md','javascript:alert(1)','http://localhost/a','http://127.0.0.1/a','http://10.1.2.3','http://192.168.1.1','http://[::1]/','https://user:password@example.com'])assert.ok(rejectUnsafeUrl(url),url);
 assert.equal(rejectUnsafeUrl('https://talent.baidu.com/jobs/list'),null);
});
test('only actual navigation failures receive a retry',async()=>{
 let calls=0;const page={goto:async()=>{calls++;throw new Error('connection closed');}};
 const invalid=await checkUrlLivenessWithFallback(page,'http://localhost/a');
 assert.equal(calls,0);assert.equal(invalid.code,'invalid_url');assert.equal(shouldRetryNavigation(invalid),false);
 const network=await checkUrlLivenessWithFallback(page,'https://example.com/job');
 assert.equal(calls,1);assert.equal(network.code,'navigation_error');assert.equal(shouldRetryNavigation(network),true);
 assert.equal(shouldRetryNavigation({code:'expired_body'}),false);
});
