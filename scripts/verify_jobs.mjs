#!/usr/bin/env node

import { readFile, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { verificationUrl } from './verification_urls.mjs';
import {inspectApplyControls} from './apply_controls.mjs';
import {launchBrowser} from './browser_runtime.mjs';
import {rejectUnsafeUrl,shouldRetryNavigation} from './liveness.mjs';
import {normalizeSelectionMetadata} from './result_metadata.mjs';

export function parseArgs(argv) {
  const result = {
    limit: 30,
    careerOpsRoot: process.env.CAREER_OPS_ROOT || undefined,
    browserProxy: process.env.JOB_SCOUT_BROWSER_PROXY || undefined,
  };
  for (let i = 0; i < argv.length; i += 1) {
    const value = argv[i];
    if (value === '--input') result.input = argv[++i];
    else if (value === '--output') result.output = argv[++i];
    else if (value === '--career-ops-root') result.careerOpsRoot = argv[++i];
    else if (value === '--browser-proxy') result.browserProxy = argv[++i];
    else if (value === '--limit') result.limit = Number(argv[++i]);
  }
  if (!result.input || !result.output) {
    throw new Error('Usage: verify_jobs.mjs --input jobs.json --output verified.json [--career-ops-root <path>] [--limit 30] [--browser-proxy <server|direct>]');
  }
  if (!Number.isSafeInteger(result.limit) || result.limit < 1) throw new Error('--limit must be a positive integer');
  return result;
}

function normalize(value) {
  return String(value || '').toLowerCase().replace(/[^0-9a-z\u4e00-\u9fff]+/g, '');
}

function titleMatches(body, title) {
  const bodyText = normalize(body);
  const titleText = normalize(title);
  if (!titleText) return false;
  if (bodyText.includes(titleText)) return true;
  const tokens = String(title || '').split(/[\s【】()[\]（）·｜|\-_/]+/).map(normalize).filter((x) => x.length >= 2);
  return tokens.length > 0 && tokens.filter((token) => bodyText.includes(token)).length >= Math.ceil(tokens.length * 0.6);
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const root = args.careerOpsRoot ? path.resolve(args.careerOpsRoot) : null;
  let liveness;
  if(root){
  for (const name of ['package.json', 'liveness-browser.mjs']) {
    if (!existsSync(path.join(root, name))) {
      throw new Error(`Career Ops directory is missing ${name}: ${root}`);
    }
  }
  liveness = await import(pathToFileURL(path.join(root, 'liveness-browser.mjs')).href);
  }else{liveness=await import('./liveness.mjs');}
  const payload = normalizeSelectionMetadata(JSON.parse(await readFile(args.input, 'utf8')));

  const browser = await launchBrowser(root,args.browserProxy);
  let page = await liveness.newLivenessPage(browser);
  const max = Math.min(args.limit, payload.positions.length);
  let active = 0;
  let expired = 0;
  let uncertain = 0;

  for (let i = 0; i < max; i += 1) {
    const item = payload.positions[i];
    const targetUrl = verificationUrl(item.source_url);
    // NetEase redirects the upstream module's fixed macOS/Chrome120 UA to
    // its homepage. Use the installed browser's native UA for this portal.
    if (URL.canParse(targetUrl) && new URL(targetUrl).hostname === 'hr.163.com') {
      await page.context().close();
      page=await browser.newPage({locale:'zh-CN'});
    }
    const verifiedAt = new Date().toISOString();
    try {
      const unsafe=rejectUnsafeUrl(targetUrl);
      if(unsafe)throw Object.assign(new Error(unsafe),{code:'invalid_url'});
      let base = await liveness.checkUrlLivenessWithFallback(page, targetUrl, {});
      if (shouldRetryNavigation(base)) {
        try {
          await page.goto(targetUrl, { waitUntil: 'commit', timeout: 45000 });
          await page.waitForTimeout(8000);
          base = { result: 'uncertain', code:'navigation_retry_loaded', reason: '首轮导航失败；45 秒宽限重试已加载页面' };
        } catch (retryError) {
          base = {
            result: 'uncertain',
            code: 'navigation_error',
            reason: `宽限重试仍失败：${retryError instanceof Error ? retryError.message.split('\n')[0] : String(retryError)}`,
          };
        }
      }
      // Wait for late-hydrated native controls without depending on body wording.
      await page.locator('button,a,[role=button],div').filter({hasText:/^\s*(?:立即)?(?:申\s*请(?:职位)?|投递(?:简历|岗位)?|简历投递|Apply(?: now)?)\s*$/i}).first().waitFor({state:'visible',timeout:6000}).catch(()=>{});
      const body = await page.locator('body').innerText({ timeout: 5000 }).catch(() => '');
      const titleMatch = titleMatches(body, item.title);
      const controls=await inspectApplyControls(page);
      const applyControl = controls.some(c=>!c.disabled);
      let status = base.result;
      let reason = base.reason;
      if (titleMatch && controls.length && !applyControl) {
        status='uncertain';reason='岗位标题匹配，但申请控件禁用；可能需用户登录或确认平台条款，未执行这些操作';
      }
      if ((base.result !== 'expired'||['insufficient_content','listing_page'].includes(base.code)) && titleMatch && applyControl) {
        status = 'active';
        reason = '详情页岗位标题匹配且存在申请/投递控件';
      } else if (base.result === 'active' && (!titleMatch || !applyControl) && !(titleMatch && controls.length && !applyControl)) {
        status = 'uncertain';
        reason = `基础页面可访问，但${!titleMatch ? '岗位标题未匹配' : '未找到申请/投递控件'}`;
      } else if (
        base.result === 'expired' &&
        item.source_active_signal?.active &&
        ['insufficient_content', 'listing_page'].includes(base.code)
      ) {
        status = 'uncertain';
        reason = page.url() === 'about:blank'
          ? '官网 ATS 当前仍返回该岗位，但浏览器跳到空白页，链接不可确认'
          : `官网 ATS 当前仍返回该岗位，但详情页${base.code === 'listing_page' ? '跳到列表页' : '只加载出页面壳'}，链接不可确认`;
      }
      item.liveness_status = status;
      item.verification = {
        verified_at: verifiedAt,
        method: 'playwright_detail_page',
        requested_url: targetUrl,
        final_url: page.url(),
        title_match: titleMatch,
        apply_control: applyControl,
        apply_controls: controls,
        code: base.code,
        reason,
      };
      if (status === 'active') active += 1;
      else if (status === 'expired') expired += 1;
      else uncertain += 1;
    } catch (error) {
      item.liveness_status = 'uncertain';
      item.verification = {
        verified_at: verifiedAt,
        method: 'playwright_detail_page',
        requested_url: targetUrl,
        final_url: page.url(),
        title_match: false,
        apply_control: false,
        code: error.code || 'verification_error',
        reason: error instanceof Error ? error.message : String(error),
      };
      uncertain += 1;
    }
  }

  payload.verification_summary = {
    requested: max,
    active,
    expired,
    uncertain,
    skipped: payload.positions.length - max,
  };
  await browser.close();
  await writeFile(args.output, JSON.stringify(payload, null, 2), 'utf8');
}

if (process.argv[1] && pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url) main().catch((error) => {
  console.error(error instanceof Error ? error.stack : String(error));
  process.exit(1);
});
