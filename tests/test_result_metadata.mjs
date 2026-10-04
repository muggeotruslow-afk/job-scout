import test from 'node:test';import assert from 'node:assert/strict';
import {normalizeSelectionMetadata} from '../scripts/result_metadata.mjs';
test('shortlist count reflects actual rows without losing source scan count',()=>{
 const payload={returned_positions:197,total_reported:197,positions:Array.from({length:15},(_,id)=>({id}))};
 normalizeSelectionMetadata(payload);assert.equal(payload.returned_positions,15);
 assert.equal(payload.source_scan_returned_positions,197);assert.equal(payload.total_reported,197);
 normalizeSelectionMetadata(payload);assert.equal(payload.source_scan_returned_positions,197);
});
test('normal full scan count is preserved',()=>{
 const payload={returned_positions:2,positions:[{},{}]};normalizeSelectionMetadata(payload);
 assert.equal(payload.returned_positions,2);assert.equal(payload.source_scan_returned_positions,undefined);
});
