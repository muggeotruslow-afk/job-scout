import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('official',ROOT/'scripts/official_adapters.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def normalize(r):
    return {'post_id':r,'title':'示例岗位','source_url':'https://example.com/'+r,
            'description':'职责','requirements':'要求'}

class PaginationTests(unittest.TestCase):
    def test_huawei_new_public_contract(self):
        class FakeClient:
            def request(self,url,body,headers):
                assert '/getJobPage?' in url
                assert body['recruitmentType']==['INTERN']
                assert headers['x-alb-gray']=='prod'
                return {'status':'SUCCESS','data':{'pageVO':{'curPage':1,'totalRows':1},'result':[{'advertisementId':7,'jobName':'示例实习','scenarioName':'实习生','mainBusiness':'职责','jobRequire':'要求'}]}}
        r=m.fetch_official('huawei','',3,client=FakeClient())
        self.assertTrue(r['pagination']['complete'])
        self.assertEqual(r['positions'][0]['source_url'],'https://career.huawei.com/cn/job-details?advertisementId=7')

    def test_netease_uses_current_page(self):
        class FakeClient:
            def request(self,url,body):
                page=body['currentPage']
                return {'code':200,'data':{'total':20,'list':[{'id':(page-1)*10+i,'name':'示例实习','workType':'1','description':'职责','requirement':'要求'}for i in range(1,11)]}}
        r=m.fetch_official('netease','',3,client=FakeClient())
        self.assertTrue(r['pagination']['complete']);self.assertEqual(r['fetched'],20)

    def test_tencent_synthetic_project_identity(self):
        class FakeClient:
            def request(self,url,body=None,params=None):
                if 'getProjectMapping' in url:return {'status':0,'data':[{'subProjectList':[{'projectName':'日常实习','mappingId':104}]}]}
                if 'searchPosition' in url:return {'status':0,'data':{'count':1,'positionList':[{'postId':'-5','positionTitle':'项目实习生-市场','projectName':'项目实习生','recruitLabelName':'日常实习'}]}}
                return {'status':0,'data':{'postId':None,'id':-5,'title':'项目实习生-市场','desc':'职责','request':'要求'}}
        r=m.fetch_official('tencent','',3,client=FakeClient())
        self.assertTrue(r['ok']);self.assertEqual(r['positions'][0]['post_id'],'-5')

    def test_partial_failure_preserves_first_page(self):
        def search(page,size):
            if page==2:raise RuntimeError('connection failed')
            return [str(i) for i in range(10)],20
        result=m.collect(search,normalize,company='netease',keyword='',max_pages=3)
        self.assertFalse(result['ok']);self.assertEqual(result['fetched'],10)
        self.assertFalse(result['pagination']['complete'])
        self.assertEqual(result['errors'][0]['page'],2)

    def test_repeated_page_never_claims_complete(self):
        r=m.collect(lambda p,s:([str(i) for i in range(10)],20),normalize,company='netease',keyword='',max_pages=3)
        self.assertEqual(r['pagination']['stop_reason'],'repeated_page')
        self.assertFalse(r['pagination']['complete'])

    def test_reaching_total_and_empty_query(self):
        r=m.collect(lambda p,s:([str((p-1)*10+i) for i in range(10)],20),normalize,company='netease',keyword='',max_pages=3)
        self.assertTrue(r['pagination']['complete']);self.assertEqual(r['fetched'],20)
        r=m.collect(lambda p,s:([],0),normalize,company='netease',keyword='不存在',max_pages=3)
        self.assertTrue(r['pagination']['complete']);self.assertEqual(r['fetched'],0)

    def test_missing_detail_is_explicit(self):
        def partial(row):return {**normalize(row),'requirements':''}
        r=m.collect(lambda p,s:(['1'],1),partial,company='pdd',keyword='',max_pages=1)
        self.assertEqual(r['positions'][0]['jd_status'],'incomplete')

    def test_cross_page_duplicates_do_not_break_raw_total_accounting(self):
        def page(number,size):
            return ([str(i) for i in range(10)] if number==1 else [str(i) for i in range(9,19)]),20
        r=m.collect(page,normalize,company='kuaishou',keyword='',max_pages=3)
        self.assertTrue(r['pagination']['complete']);self.assertEqual(r['fetched'],19)
        self.assertEqual(r['pagination']['rows_received'],20)
        self.assertEqual(r['pagination']['duplicate_rows'],1)
        self.assertEqual(r['pagination']['completion_basis'],'raw_rows')

if __name__=='__main__':unittest.main()
