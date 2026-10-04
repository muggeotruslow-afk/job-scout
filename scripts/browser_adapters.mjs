import {writeFile} from 'node:fs/promises';
import {launchBrowser} from './browser_runtime.mjs';

function args(argv) {const r={maxPages:50,pageSize:10,keyword:''};for(let i=0;i<argv.length;i++){
 const k=argv[i];if(k==='--company')r.company=argv[++i];else if(k==='--keyword')r.keyword=argv[++i];
 else if(k==='--max-pages')r.maxPages=Number(argv[++i]);else if(k==='--page-size')r.pageSize=Number(argv[++i]);
 else if(k==='--output')r.output=argv[++i];else if(k==='--career-ops-root')r.root=argv[++i];else if(k==='--browser-proxy')r.proxy=argv[++i];
 }return r;}
const options=args(process.argv.slice(2));
const urls={alibaba:'https://campus-talent.alibaba.com/campus/position',bytedance:'https://jobs.bytedance.com/campus/position',xiaomi:'https://xiaomi.jobs.f.mioffice.cn/internship/position'};
const payload={ok:false,source:options.company+'_official_browser_api',total:null,fetched:0,positions:[],errors:[],
 scope:{company:options.company,keyword:options.keyword,recruit_type:options.company==='xiaomi'?'campus_internship':'daily_internship'},
 pagination:{complete:false,stop_reason:'upstream_error',page_size:10,max_pages:options.maxPages,pages_fetched:0,authoritative_total:null}};
const seen=new Set();let browser;
function ensure(value,msg){if(!value)throw new Error(msg);}
function titleName(v){return typeof v==='string'?v:v?.zh_cn||v?.i18n||'';}
function findDaily(v){if(Array.isArray(v)){for(const a of v){const r=findDaily(a);if(r)return r;}}else if(v&&typeof v==='object'){
 if(titleName(v.name)==='日常实习'&&v.id)return v;for(const a of Object.values(v)){const r=findDaily(a);if(r)return r;}}return null;}
function text(v){return String(v||'').replace(/<[^>]*>/g,' ').trim();}
function iso(v){return typeof v==='number'?new Date(v).toISOString():v||null;}
try {
 ensure(urls[options.company], 'No browser adapter for company');
 browser=await launchBrowser(options.root,options.proxy);const context=await browser.newContext();const page=await context.newPage();
 let aliSearchURL,aliHeaders,batch;
 if(options.company==='alibaba'){
  const batchWait=page.waitForResponse(r=>r.url().includes('/searchCondition/listBatch')&&r.status()===200,{timeout:35000});
  const searchWait=page.waitForResponse(r=>r.url().includes('/position/search')&&r.status()===200,{timeout:35000});
  await page.goto(urls.alibaba,{waitUntil:'domcontentloaded',timeout:35000});
  const [batchResponse,searchResponse]=await Promise.all([batchWait,searchWait]);
  const batches=await batchResponse.json();ensure(batches.success,'Alibaba project discovery failed');
  batch=batches.content.internship.find(b=>b.name.includes('日常实习'));ensure(batch,'Alibaba daily internship batch missing');
  aliSearchURL=searchResponse.url();aliHeaders=searchResponse.request().headers();
  // Reuse only this anonymous browser context's live CSRF state, never a saved token.
 }else{
  const filtersWait=page.waitForResponse(r=>r.url().includes('/config/job/filters/'+(options.company==='xiaomi'?'6':'3'))&&r.status()===200,{timeout:35000});
  await page.goto(urls[options.company],{waitUntil:'domcontentloaded',timeout:35000});
  const response=await filtersWait;const filters=await response.json();ensure(filters.code===0,'ByteDance filters failed');
  batch=options.company==='xiaomi'?{id:'internship'}:findDaily(filters.data);ensure(batch,'Daily internship project missing');
 }
 const size=options.company!=='alibaba'?Math.max(1,Math.min(50,options.pageSize)):10;
 payload.pagination.page_size=size;payload.scope.project_id=String(batch.id);
 for(let number=1;number<=Math.max(1,options.maxPages);number++){
  let rows,total;
  if(options.company==='alibaba'){
   const response=await context.request.post(aliSearchURL,{headers:aliHeaders,data:{batchId:batch.id,pageIndex:number,pageSize:size,
     customDeptCode:'',channel:'campus_group_official_site',language:'zh'},timeout:30000});
   const data=await response.json();ensure(response.ok()&&data.success,'Alibaba search rejected');
   ensure(Number(data.content.currentPage)===number,'Alibaba returned wrong page');
   rows=data.content.datas;total=Number(data.content.totalCount);
  }else{
   const expected=(number-1)*size;
   const responseWait=page.waitForResponse(r=>{
    if(!r.url().includes('/api/v1/search/job/posts')||r.status()!==200)return false;
    try{const body=r.request().postDataJSON();return body.offset===expected&&body.limit===size&&body.keyword===options.keyword&&(options.company==='xiaomi'||body.subject_id_list?.includes(String(batch.id)));}catch{return false;}
   },{timeout:35000});
   const url=new URL(urls[options.company]);if(options.company==='bytedance')url.searchParams.set('project',String(batch.id));url.searchParams.set('current',String(number));
   url.searchParams.set('limit',String(size));url.searchParams.set('keywords',options.keyword);
   await page.goto(url.href,{waitUntil:'domcontentloaded',timeout:35000});
   const response=await responseWait;const data=await response.json();ensure(data.code===0,'ByteDance search rejected');rows=data.data.job_post_list;total=Number(data.data.count);
  }
  ensure(Array.isArray(rows)&&Number.isSafeInteger(total)&&total>=0,'List schema/total changed');
  payload.total=Math.max(payload.total||0,total);payload.pagination.authoritative_total=payload.total;
  const before=payload.positions.length;
  for(const r of rows){
   ensure(r.id&&r.title||r.id&&r.name,'Missing job ID/title');
   if(seen.has(String(r.id)))continue;seen.add(String(r.id));
   const ali=options.company==='alibaba';
   if(ali)ensure(String(r.batchId)===String(batch.id),'Alibaba campaign mismatch');
   const item={company:ali?'阿里巴巴':options.company==='xiaomi'?'小米':'字节跳动',post_id:String(r.id),title:text(ali?r.name:r.title),
    source_url:ali?`https://campus-talent.alibaba.com/campus/position/${r.id}`:urls[options.company]+`/${r.id}/detail`,
    official_search_url:urls[options.company],description:text(r.description),requirements:text(ali?r.requirement:r.requirement),
    location:ali?(r.workLocations||[]).join('、'):(r.city_list||[]).map(c=>c.name).join('、')||r.city_info?.name||'',
    recruit_type:options.company==='xiaomi'?'校招实习（具体批次待确认）':'日常实习',posted_date:iso(ali?r.publishTime:r.create_time),updated_date:iso(ali?r.modifyTime:r.update_time),
    crawled_at:new Date().toISOString()};
   item.jd_status=item.description&&item.requirements?'complete':'incomplete';payload.positions.push(item);
  }
  payload.pagination.pages_fetched=number;
  if(payload.positions.length>=payload.total){payload.pagination.complete=true;payload.pagination.stop_reason='authoritative_total_reached';break;}
  if(!rows.length){payload.pagination.stop_reason='empty_page_before_total';break;}
  if(payload.positions.length===before){payload.pagination.stop_reason='repeated_page';break;}
  payload.pagination.stop_reason='max_pages';
 }
 payload.ok=true;
 if(options.company==='alibaba'&&options.keyword){payload.source_fetched=payload.positions.length;const k=options.keyword.toLowerCase();
  payload.positions=payload.positions.filter(p=>(p.title+' '+p.description+' '+p.requirements).toLowerCase().includes(k));payload.scope.keyword_filter='local_after_source_scan';}
}catch(error){payload.errors.push({stage:'browser_fetch',reason:error.message.split('\n')[0]});payload.pagination.complete=false;payload.pagination.stop_reason='upstream_error';}
finally{if(browser)await browser.close();payload.fetched=payload.source_fetched??payload.positions.length;
 await writeFile(options.output,JSON.stringify(payload,null,2),'utf8');if(!payload.ok)process.exitCode=2;}
