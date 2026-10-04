// Standalone page-access classification; never submits or accepts terms.
import {isIP} from 'node:net';
export function rejectUnsafeUrl(value) {
  let u;try{u=new URL(value);}catch{return 'Invalid URL';}
  if(!['http:','https:'].includes(u.protocol)||u.username||u.password)return 'Unsupported URL or embedded credentials';
  const h=u.hostname.replace(/^\[|\]$/g,'').toLowerCase();
  if(h==='localhost'||h.endsWith('.localhost')||h.endsWith('.local'))return 'Local host is not a recruitment portal';
  if(isIP(h)===4){const [a,b]=h.split('.').map(Number);if(a===0||a===10||a===127||a===169&&b===254||a===172&&b>=16&&b<=31||a===192&&b===168||a>=224)return 'Private/reserved address';}
  if(isIP(h)===6&&(h==='::'||h==='::1'||h.startsWith('fc')||h.startsWith('fd')||h.startsWith('fe8')||h.startsWith('::ffff:')))return 'Private/reserved address';
  return null;
}
export async function newLivenessPage(browser){return browser.newPage({locale:'zh-CN'});}
export function shouldRetryNavigation(result){return result?.code==='navigation_error';}
export async function checkUrlLivenessWithFallback(page,url){
  const invalid=rejectUnsafeUrl(url);if(invalid)return {result:'uncertain',code:'invalid_url',reason:invalid};
  try{
    const response=await page.goto(url,{waitUntil:'domcontentloaded',timeout:15000});
    await page.waitForTimeout(1500);
    const status=response?.status()||0;const body=await page.locator('body').innerText().catch(()=> '');
    if(status===404||status===410)return {result:'expired',code:'http_gone',reason:'HTTP '+status};
    if(status>=400)return {result:'uncertain',code:'access_blocked',reason:'HTTP '+status};
    if(/职位已下线|该岗位已关闭|职位已过期|job (?:is closed|has expired)/i.test(body))return {result:'expired',code:'expired_body',reason:'Page explicitly says this position closed'};
    return {result:'uncertain',code:body.trim().length<100?'insufficient_content':'content_present',reason:'Page access alone does not prove an active application control'};
  }catch(error){return {result:'uncertain',code:'navigation_error',reason:error.message.split('\n')[0]};}
}
