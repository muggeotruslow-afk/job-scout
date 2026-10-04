import {createRequire} from 'node:module';
import {existsSync} from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';

export function browserPath() {
  return [process.env.LOCALAPPDATA && path.join(process.env.LOCALAPPDATA,'Google/Chrome/Application/chrome.exe'),
    process.env.PROGRAMFILES && path.join(process.env.PROGRAMFILES,'Google/Chrome/Application/chrome.exe'),
    process.env['PROGRAMFILES(X86)'] && path.join(process.env['PROGRAMFILES(X86)'],'Microsoft/Edge/Application/msedge.exe'),
    process.env.PROGRAMFILES && path.join(process.env.PROGRAMFILES,'Microsoft/Edge/Application/msedge.exe')].filter(Boolean).find(p=>existsSync(p));
}
export async function launchBrowser(root, proxy) {
  const require=createRequire(root?pathToFileURL(path.join(path.resolve(root),'package.json')):new URL('../package.json',import.meta.url));
  let chromium;
  try { ({chromium}=require('playwright')); }
  catch { throw new Error('Playwright missing. Run npm install in Job Scout, or configure --career-ops-root with installed dependencies.'); }
  const executablePath=browserPath();
  return chromium.launch({headless:true,...(executablePath?{executablePath}:{}),
    ...(proxy==='direct'?{args:['--no-proxy-server']}:proxy?{proxy:{server:proxy}}:{})});
}
