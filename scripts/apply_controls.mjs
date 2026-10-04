export function isApplyLabel(label) {
  return /^(?:立即)?(?:申请(?:职位|岗位)?|投递(?:简历|岗位)?|简历投递|我要应聘|应聘|apply(?:now|forthisjob)?)$/i.test(String(label||'').replace(/\s+/g,''));
}
export async function inspectApplyControls(page) {
  const controls=await page.locator('a,button,input[type=submit],input[type=button],[role=button],div').evaluateAll(nodes=>nodes.filter(n=>{
    if(n.tagName==='DIV' && n.getAttribute('role')!=='button' && !n.classList.contains('phoenix-button') && !(location.hostname==='careers.oppo.com'&&n.classList.contains('send_btn')) && !(location.hostname==='campus.jd.com' && n.children.length===0 && getComputedStyle(n).cursor==='pointer'))return false;
    const s=getComputedStyle(n);return !n.closest('header,nav,footer,[aria-hidden=true]')&&s.display!=='none'&&s.visibility!=='hidden'&&n.getClientRects().length;
  }).map(n=>({label:n.innerText||n.value||n.getAttribute('aria-label')||'',disabled:!!n.disabled||n.getAttribute('aria-disabled')==='true'||!!n.querySelector('[aria-disabled=true],.phoenix-button__wraper--disabled')})));
  return controls.filter(c=>isApplyLabel(c.label));
}
