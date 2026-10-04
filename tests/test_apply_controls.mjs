import test from 'node:test';import assert from 'node:assert/strict';
import {isApplyLabel} from '../scripts/apply_controls.mjs';
test('recognizes observed labels without treating prose as a button',()=>{
 for(const s of ['投递','投递岗位','申 请','简历投递','申请职位','投递简历','Apply now'])assert.equal(isApplyLabel(s),true,s);
 for(const s of ['投递记录','如何申请职位','申请已结束','登录','申请条件'])assert.equal(isApplyLabel(s),false,s);
});
