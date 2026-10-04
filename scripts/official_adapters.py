"""Public recruitment APIs; no resume, login, or application submission."""
from datetime import datetime, timezone
from html import unescape
import hashlib
import hmac
import http.cookiejar
import json
import re
import time
import urllib.parse
import urllib.request

HTTP_COMPANIES = {'tencent', 'netease', 'xiaohongshu', 'kuaishou', 'jd', 'pdd','huawei'}
NAMES = {'tencent':'腾讯', 'netease':'网易', 'xiaohongshu':'小红书', 'kuaishou':'快手', 'jd':'京东', 'pdd':'拼多多','huawei':'华为'}
SEARCH = {'tencent':'https://join.qq.com/post.html', 'netease':'https://hr.163.com/job-list.html',
 'xiaohongshu':'https://job.xiaohongshu.com/campus/intern',
 'kuaishou':'https://zhaopin.kuaishou.cn/recruit/e/#/official/trainee/',
 'jd':'https://campus.jd.com/#/jobs', 'pdd':'https://careers.pddglobalhr.com/campus/intern',
 'huawei':'https://career.huawei.com/cn/campus-recruitment-job-list?recruitmentType=INTERN'}

def text(value):
    return unescape(re.sub('<[^>]*>', ' ', str(value or ''))).strip()

def date(value):
    if value in (None, ''): return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000 if value > 100000000000 else value, timezone.utc).isoformat()
    return str(value)

class Client:
    def __init__(self, proxy=None):
        handlers=[urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())]
        if proxy == 'direct': handlers.append(urllib.request.ProxyHandler({}))
        elif proxy: handlers.append(urllib.request.ProxyHandler({'http':proxy,'https':proxy}))
        self.opener=urllib.request.build_opener(*handlers)

    def request(self, url, body=None, params=None, headers=None, raw=False):
        if params: url += ('&' if '?' in url else '?') + urllib.parse.urlencode(params)
        options={'User-Agent':'Mozilla/5.0', 'Accept':'application/json', **(headers or {})}
        data=None
        if body is not None:
            data=json.dumps(body).encode(); options['Content-Type']='application/json'
        req=urllib.request.Request(url,data=data,headers=options)
        with self.opener.open(req,timeout=25) as response:
            content=response.read().decode('utf-8')
        return content if raw else json.loads(content)

def require(value, message):
    if not value: raise RuntimeError(message)

def collect(search_page, normalize, *, company, keyword, max_pages, size=10):
    """Stop conservatively; retain earlier pages and explicit errors on failure."""
    bucket=[]; seen=set(); total=None; pages=0; stop='max_pages'; errors=[]; received=0
    for page in range(1,max(1,max_pages)+1):
        try:
            rows, reported = search_page(page, size)
            require(isinstance(rows,list) and isinstance(reported,int) and reported>=0,'Invalid list/total schema')
            total=max(total or 0,reported)
            before=len(bucket)
            received+=len(rows)
            for row in rows:
                item=normalize(row)
                require(item.get('post_id') and item.get('title') and item.get('source_url'), 'Missing job ID/title/link')
                key=str(item['post_id'])
                if key in seen: continue
                seen.add(key)
                item['crawled_at']=datetime.now(timezone.utc).isoformat(timespec='seconds')
                item['official_search_url']=SEARCH[company]
                item['jd_status']='complete' if item.get('description') and item.get('requirements') else 'incomplete'
                bucket.append(item)
            pages=page
            if rows and len(bucket)==before: stop='repeated_page'; break
            if received>=total: stop='authoritative_total_reached'; break
            if not rows: stop='empty_page_before_total'; break
            if len(rows)<size: stop='short_page_before_total'; break
        except Exception as error:
            errors.append({'stage':'fetch_or_detail','page':page,'reason':str(error)[:500]})
            stop='upstream_error'; break
    return {'ok':not errors,'source':company+'_official_api','total':total,'fetched':len(bucket),'positions':bucket,
      'errors':errors,'pagination':{'complete':stop=='authoritative_total_reached','stop_reason':stop,
       'page_size':size,'pages_fetched':pages,'max_pages':max_pages,'authoritative_total':total,
       'rows_received':received,'duplicate_rows':received-len(bucket),'completion_basis':'raw_rows'},
      'scope':{'company':company,'keyword':keyword,'recruit_type':'official_internship_entry'}}

def position(company, id, title, url, description, requirements, location='', recruit_type='实习（批次待确认）', posted=None, updated=None):
    return {'company':NAMES[company], 'post_id':str(id),'title':text(title),'source_url':url,
      'description':text(description),'requirements':text(requirements),'location':text(location),
      'recruit_type':recruit_type,'posted_date':date(posted),'updated_date':date(updated)}

def fetch_official(company, keyword, max_pages, proxy=None, client=None):
    c=client or Client(proxy)
    if company=='tencent':
        base='https://join.qq.com'
        mappings=c.request(base+'/api/v1/position/getProjectMapping')
        require(mappings.get('status')==0,'Tencent project discovery failed')
        projects=[p for group in mappings['data'] for p in group.get('subProjectList',[]) if p.get('projectName')=='日常实习']
        require(projects,'Tencent daily internship project is unavailable')
        def search(page,size):
            body={'projectIdList':[],'projectMappingIdList':[p['mappingId'] for p in projects], 'keyword':keyword,
              'bgList':[],'workCountryType':0,'workCityList':[],'recruitCityList':[],'positionFidList':[],
              'pageIndex':page,'pageSize':size}
            d=c.request(base+'/api/v1/position/searchPosition',body)
            require(d.get('status')==0,'Tencent search failed')
            return d['data']['positionList'],int(d['data']['count'])
        def normalize(row):
            d=c.request(base+'/api/v1/jobDetails/getJobDetailsByPostId',params={'postId':row['postId']})
            require(d.get('status')==0,'Tencent detail failed')
            r=d['data']
            identity=str(r.get('postId'))==str(row['postId']) or (str(row['postId']).startswith('-') and str(r.get('id'))==str(row['postId']) and r.get('title')==row.get('positionTitle'))
            require(identity,'Tencent detail ID mismatch')
            require('日常实习' in str(row.get('projectName')) or '日常实习' in str(row.get('recruitLabelName')),'Tencent campaign mismatch')
            return position(company,row['postId'],r['title'],base+'/post_detail.html?postid='+str(row['postId']),r.get('desc'),r.get('request'),row.get('workCities'),'日常实习')
    elif company=='netease':
        base='https://hr.163.com/api/hr163/position'
        def search(page,size):
            d=c.request(base+'/queryPage',{'currentPage':page,'pageSize':size,'workType':'1'})
            require(d.get('code')==200,'NetEase search failed')
            return d['data']['list'],int(d['data']['total'])
        def normalize(r):
            require(str(r.get('workType'))=='1','NetEase internship filter changed')
            return position(company,r['id'],r['name'],'https://hr.163.com/job-detail.html?id='+str(r['id']),r.get('description'),r.get('requirement'),', '.join(r.get('workPlaceNameList') or []),updated=r.get('updateTime'))
    elif company=='xiaohongshu':
        base='https://job.xiaohongshu.com'
        def search(page,size):
            d=c.request(base+'/websiterecruit/position/pageQueryPosition',{'positionName':keyword,'pageNum':page,
              'pageSize':size,'recruitType':'campus','jobProjects':['madang_trainee','other_project']})
            require(d.get('statusCode')==200,'Xiaohongshu search failed')
            require(int(d['data']['pageNum'])==page,'Xiaohongshu page mismatch')
            return d['data']['list'],int(d['data']['total'])
        def normalize(r):
            require(r.get('recruitStatus')=='in_recruitment','Xiaohongshu returned a non-recruiting job')
            return position(company,r['positionId'],r['positionName'],base+'/campus/intern/position/'+str(r['positionId']),r.get('duty'),r.get('qualification'),r.get('workplace'),'实习（'+str(r.get('jobProjectName') or '批次待确认')+'）',posted=r.get('publishTime'))
    elif company=='kuaishou':
        base='https://zhaopin.kuaishou.cn/recruit/e/'
        html=c.request(base,raw=True)
        scripts=re.findall(r'<script[^>]+src=["\']([^"\']+)',html)
        main=next((s for s in scripts if '/main.' in s),None)
        require(main,'Kuaishou public main bundle missing')
        bundle=c.request(urllib.parse.urljoin(base,main),raw=True)
        match=re.search(r'generateSign\)\([^;]{0,400}?"([0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12})"',bundle,re.I)
        require(match,'Kuaishou public signing contract changed')
        key=match.group(1)
        def signed(params):
            params={k:v for k,v in params.items() if v not in ('',None)}
            query='&'.join(k+'='+urllib.parse.quote_plus(str(params[k]),safe='') for k in sorted(params) if params[k] not in ('',None))
            stamp=str(int(time.time()*1000))
            sign=hmac.new(key.encode(),(stamp+query+key).encode(),hashlib.sha256).hexdigest()
            return c.request(base+'api/v1/open/positions/simple',params=params,headers={'sign':sign,'signTimestamp':stamp,'Referer':base})
        def search(page,size):
            d=signed({'pageNum':page,'pageSize':size,'positionNatureCode':'C002','workLocationCode':'domestic','name':keyword})
            require(d.get('code')==0,'Kuaishou search failed')
            require(int(d['result']['pageNum'])==page,'Kuaishou page mismatch')
            return d['result']['list'],int(d['result']['total'])
        def normalize(r):
            require(r.get('positionNatureCode')=='C002','Kuaishou internship filter changed')
            return position(company,r['id'],r['name'],base+'#/official/trainee/job-info/'+str(r['id']),r.get('description'),r.get('positionDemand'),r.get('workLocationCode'),'日常实习',updated=r.get('updateTime'))
    elif company=='jd':
        base='https://campus.jd.com'
        projects=c.request(base+'/api/wx/position/getProjectList')
        require(projects.get('success') is True,'JD project discovery failed')
        groups=[g for g in projects['body']['projectList'] if g.get('code')=='internship' and g.get('release')]
        plans=[plan['id'] for g in groups for sub in g.get('groupList',[]) for plan in sub.get('planMapList',[])]
        require(plans,'JD internship projects not available')
        def search(page,size):
            d=c.request(base+'/api/wx/position/page?type=internship',{'pageSize':size,'pageIndex':page-1,
              'parameter':{'positionName':keyword,'planIdList':plans,'jobDirectionCodeList':[],'workCityCodeList':[],'positionDeptList':[]}})
            require(d.get('success') is True,'JD campus API failed')
            return d['body']['items'],int(d['body']['totalNumber'])
        def normalize(r):
            cities=sorted({x.get('workCity','') for x in r.get('requirementVoList') or []})
            return position(company,r['publishId'],r['positionName'],base+'/#/details?id='+str(r['publishId'])+'&type=internship',r.get('workContent'),r.get('qualification'),', '.join(cities),'实习生计划（批次待确认）',posted=r.get('publishTime'))
    elif company=='pdd':
        base='https://careers.pddglobalhr.com'
        def search(page,size):
            d=c.request(base+'/api/careers/api/recruit/position/train/list',{'page':page,'pageSize':size,'t':None})
            require(d.get('success') is True,'PDD internship API failed')
            return d['result']['list'],int(d['result']['total'])
        def normalize(r):
            d=c.request(base+'/api/careers/api/recruit/position/detail',{'id':r['id'],'t':None})
            require(d.get('success') is True,'PDD detail failed')
            detail=d['result'];require(detail.get('id')==r['id'],'PDD detail ID mismatch')
            return position(company,r['id'],r['name'],base+'/campus/intern/detail?positionId='+r['id'],detail.get('jobDuty'),detail.get('serveRequirement'),detail.get('workLocationName'),'实习入口（具体批次待确认）',posted=r.get('releaseTime'))
    elif company=='huawei':
        endpoint='https://apigw-dgg-b0.huawei.com/api/apig/channelhw/recruitmentPosition/pub/getJobPage?X-HW-ID=app_000000035886'
        # Public frontend routing metadata, not login/session credentials.
        headers={'x-jalor-tenantalias':'hcm','x-language':'zh_CN','x-hw-id':'app_000000035886',
                 'x-referer':'https://career.huawei.com/cn','x-alb-gray':'prod','Referer':'https://career.huawei.com/'}
        def search(page,size):
            d=c.request(endpoint,{'curPage':page,'pageSize':size,'jobType':'CR','recruitmentType':['INTERN']},headers=headers)
            require(d.get('status')=='SUCCESS' and isinstance(d.get('data'),dict),'Huawei new API failed')
            data=d['data'];require(data.get('pageVO') and data.get('result') is not None,'Huawei returned no page payload')
            require(int(data['pageVO']['curPage'])==page,'Huawei page mismatch')
            return data['result'],int(data['pageVO']['totalRows'])
        def normalize(r):
            require(r.get('scenarioName')=='实习生','Huawei internship filter mismatch')
            return position(company,r['advertisementId'],r['jobName'],'https://career.huawei.com/cn/job-details?advertisementId='+str(r['advertisementId']),r.get('mainBusiness'),r.get('jobRequire'),r.get('workPlace'),'实习生（具体批次待确认）',updated=r.get('lastUpdateDate'))
    else: raise RuntimeError('No built-in HTTP adapter: '+company)
    result=collect(search,normalize,company=company,keyword=keyword,max_pages=max_pages)
    # Some APIs do not consistently enforce keyword filters (notably PDD).
    # Keep pagination coverage separate from the local keyword selection.
    if keyword:
        rows=result['positions']; result['source_fetched']=len(rows)
        result['positions']=[r for r in rows if keyword.casefold() in (r['title']+' '+r['description']+' '+r['requirements']).casefold()]
        result['scope']['keyword_filter']='server_and_local'
    return result
