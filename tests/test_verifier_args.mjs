import test from 'node:test';
import assert from 'node:assert/strict';
import {parseArgs} from '../scripts/verify_jobs.mjs';
test('verification rejects zero, negative and nonnumeric limits',()=>{
 for(const value of ['0','-1','NaN','1.5']) assert.throws(()=>parseArgs(['--input','jobs.json','--output','result.json','--limit',value]),/positive integer/);
 assert.equal(parseArgs(['--input','jobs.json','--output','result.json','--limit','2']).limit,2);
});
