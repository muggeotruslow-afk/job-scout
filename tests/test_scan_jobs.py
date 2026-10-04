import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "scan_jobs.py"
SPEC = importlib.util.spec_from_file_location("scan_jobs", SCRIPT)
scan_jobs = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scan_jobs)


class ScanJobsTests(unittest.TestCase):
    def test_known_beisen_page_cap_does_not_truncate_at_first_page(self):
        sizes=[]
        class BeisenAdapter:
            _parse_row=lambda self,row:row
            def search(self,keyword,page,page_size):
                sizes.append(page_size)
                rows=[{'post_id':str(i),'title':'Intern','source_url':'https://example.com/'+str(i)} for i in range((page-1)*page_size,min(page*page_size,88))]
                return SimpleNamespace(ok=True,source='official',total=88,positions=[SimpleNamespace(to_dict=lambda row=row:row) for row in rows])
        module=SimpleNamespace(ADAPTERS={'sample':BeisenAdapter})
        with patch.dict(sys.modules,{'intern_scout.crawler':module}):
            result=scan_jobs.fetch_complete('sample','',100,3)
        self.assertEqual(sizes,[50,50])
        self.assertEqual(result['fetched'],88)
        self.assertTrue(result['pagination']['complete'])

    def test_verifier_missing_or_invalid_result_preserves_scan(self):
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'jobs.json'
            raw={'ok':True,'total':1,'fetched':1,'pagination':{'complete':True},'positions':[{'post_id':'1','title':'Product intern','source_url':'https://example.com/1','description':'Tasks','requirements':'Student'}]}
            def invalid_result(source,target,*args):target.write_text('{broken json',encoding='utf-8')
            for verifier in (lambda *args:None, invalid_result):
                with patch.dict(os.environ,{},clear=True),patch.object(sys,'argv',['scan_jobs.py','--company','baidu','--verify','--output',str(output)]),patch.object(scan_jobs,'fetch_complete',return_value=raw),patch.object(scan_jobs,'run_verifier',side_effect=verifier):
                    self.assertEqual(scan_jobs.main(),2)
                result=scan_jobs.json.loads(output.read_text(encoding='utf-8'))
                self.assertEqual(len(result['positions']),1)
                self.assertEqual(result['status'],'partial')
                self.assertEqual(result['errors'][0]['stage'],'verification')

    def test_browser_dependency_directory_does_not_implicitly_read_history(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'data').mkdir()
            (root/'data/applications.md').write_text('| Company | Role | Status |\n|---|---|---|\n| 示例公司 | 产品实习生 | Applied |\n',encoding='utf-8')
            raw={'positions':[],'total':0,'fetched':0,'pagination':{'complete':True}}
            for extra,expected in [([],0),(['--use-career-ops-history'],1)]:
                output=root/'result.json'
                with patch.dict(os.environ,{},clear=True),patch.object(sys,'argv',['scan_jobs.py','--company','百度','--career-ops-root',str(root),'--output',str(output),*extra]),patch.object(scan_jobs,'fetch_complete',return_value=raw):
                    self.assertEqual(scan_jobs.main(),0)
                self.assertEqual(scan_jobs.json.loads(output.read_text(encoding='utf-8'))['history_entries_loaded'],expected)

    def test_chinese_company_names_resolve(self):
        for name,slug in [('腾讯','tencent'),('阿里','alibaba'),('网易','netease'),('字节','bytedance'),('快手','kuaishou'),('小红书','xiaohongshu'),('京东','jd'),('拼多多','pdd')]:
            self.assertEqual(scan_jobs.company_slug(name),slug)

    def test_failed_fetch_writes_explicit_result(self):
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'failure.json'
            with patch.dict(os.environ,{},clear=True),patch.object(sys,'argv',['scan_jobs.py','--company','百度','--output',str(output)]),patch.object(scan_jobs,'fetch_complete',side_effect=RuntimeError('API rejected')):
                self.assertEqual(scan_jobs.main(),2)
            result=scan_jobs.json.loads(output.read_text(encoding='utf-8'))
            self.assertEqual(result['status'],'failed');self.assertFalse(result['complete'])
            self.assertIsNone(result['total_reported']);self.assertEqual(result['errors'][0]['reason'],'API rejected')

    def test_verifier_failure_preserves_fetched_jobs(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for name in ('package.json','liveness-browser.mjs'):(root/name).write_text('',encoding='utf-8')
            output=root/'result.json'
            raw={'ok':True,'total':1,'fetched':1,'pagination':{'complete':True},'positions':[{'title':'产品实习生','company':'百度','post_id':'1','source_url':'https://talent.baidu.com/jobs/detail/INTERN/1','description':'职责','requirements':'本科'}]}
            with patch.dict(os.environ,{},clear=True),patch.object(sys,'argv',['scan_jobs.py','--company','百度','--verify','--career-ops-root',str(root),'--output',str(output)]),patch.object(scan_jobs,'fetch_complete',return_value=raw),patch.object(scan_jobs,'run_verifier',side_effect=SystemExit('Browser failed')):
                self.assertEqual(scan_jobs.main(),2)
            d=scan_jobs.json.loads(output.read_text(encoding='utf-8'))
            self.assertEqual(len(d['positions']),1);self.assertEqual(d['status'],'partial')
            self.assertEqual(d['errors'][0]['stage'],'verification')

    def test_scan_without_career_ops_or_history(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "jobs.json"
            raw = {"positions": [], "total": 0, "fetched": 0, "pagination": {"complete": True}}
            with patch.dict(os.environ, {}, clear=True), patch.object(
                sys, "argv", ["scan_jobs.py", "--company", "example", "--_direct", "--output", str(output)]
            ), patch.object(scan_jobs, "fetch_complete", return_value=raw):
                self.assertEqual(scan_jobs.main(), 0)
            payload = scan_jobs.json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["history_sources"], [])
            self.assertEqual(payload["history_entries_loaded"], 0)

    def test_career_ops_environment_and_cli_precedence(self):
        with tempfile.TemporaryDirectory() as env_root, tempfile.TemporaryDirectory() as cli_root:
            with patch.dict(os.environ, {"CAREER_OPS_ROOT": env_root}), patch.object(
                sys, "argv", ["scan_jobs.py", "--company", "example"]
            ):
                self.assertEqual(scan_jobs.parse_args().career_ops_root, Path(env_root).resolve())
            with patch.dict(os.environ, {"CAREER_OPS_ROOT": env_root}), patch.object(
                sys, "argv", ["scan_jobs.py", "--company", "example", "--career-ops-root", cli_root]
            ):
                self.assertEqual(scan_jobs.parse_args().career_ops_root, Path(cli_root).resolve())

    def test_standalone_verification_does_not_require_career_ops(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(
            sys, "argv", ["scan_jobs.py", "--company", "example", "--verify"]
        ):
            args=scan_jobs.parse_args()
            self.assertTrue(args.verify)
            self.assertIsNone(args.career_ops_root)

    def test_verification_requires_career_ops_modules(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True), patch.object(
            sys, "argv", ["scan_jobs.py", "--company", "example", "--verify", "--career-ops-root", directory]
        ), patch("sys.stderr"):
            with self.assertRaises(SystemExit) as error:
                scan_jobs.parse_args()
            self.assertEqual(error.exception.code, 2)
            for name in ("package.json", "liveness-browser.mjs"):
                (Path(directory) / name).write_text("", encoding="utf-8")
            self.assertEqual(scan_jobs.parse_args().career_ops_root, Path(directory).resolve())

    def test_nio_link_is_corrected_by_config(self):
        raw = "https://nio.jobs.feishu.cn/saas-career/position/123/detail"
        self.assertEqual(
            scan_jobs.normalize_url("nio", raw),
            "https://nio.jobs.feishu.cn/campus/position/123/detail",
        )

    def test_campaigns_are_separated(self):
        self.assertEqual(scan_jobs.campaign_classification({"title": "产品日常实习生"})["code"], "daily")
        self.assertEqual(scan_jobs.campaign_classification({"title": "2027届秋招产品经理"})["code"], "autumn")
        self.assertEqual(scan_jobs.campaign_classification({"title": "暑期实习生"})["code"], "summer")
        self.assertEqual(scan_jobs.campaign_classification({"title": "销售顾问实习生"})["code"], "sales_service")
        self.assertEqual(scan_jobs.campaign_classification({"title": "蔚来AGI超星计划-AI原生产品研究员"})["code"], "campus")
        self.assertEqual(scan_jobs.campaign_classification({"title": "提前批-产品经理"})["code"], "campus")

    def test_generic_intern_is_honestly_medium_confidence(self):
        result = scan_jobs.campaign_classification({"title": "AI产品实习生"})
        self.assertEqual(result["code"], "daily")
        self.assertEqual(result["confidence"], "medium")

    def test_optional_conversion_sentence_does_not_change_campaign(self):
        result = scan_jobs.campaign_classification(
            {"title": "产品实习生", "requirements": "表现优秀者有转正机会"}
        )
        self.assertEqual(result["code"], "daily")

    def test_application_history_is_matched(self):
        path = Path(__file__).parent / "fixtures" / "applications.md"
        entries = scan_jobs.load_history([path])
        match = scan_jobs.history_match(
            {"company": "示例科技（虚构）", "title": "产品实习生-示例平台"}, entries
        )
        self.assertIsNotNone(match)
        self.assertEqual(scan_jobs.recommendation_state(match), "already_in_pipeline")

    def test_dedupe_key_prefers_post_id(self):
        self.assertEqual(
            scan_jobs.stable_key({"post_id": "ABC-123", "source_url": "https://x/a"}),
            "id:abc123",
        )

    def test_new_daily_role_sorts_before_campus_and_history(self):
        daily = {"title": "产品实习生", "campaign": {"code": "daily"}, "recommendation_state": "new"}
        campus = {"title": "产品经理", "campaign": {"code": "campus"}, "recommendation_state": "new"}
        applied = {"title": "内容实习生", "campaign": {"code": "daily"}, "recommendation_state": "already_in_pipeline"}
        self.assertEqual(sorted([campus, applied, daily], key=scan_jobs.ranking_key)[0], daily)

    def test_jd_style_page_total_is_not_authoritative(self):
        self.assertFalse(scan_jobs.is_authoritative_total(100, 100, 100))
        self.assertFalse(scan_jobs.is_authoritative_total(37, 37, 100))
        self.assertTrue(scan_jobs.is_authoritative_total(388, 100, 100))


if __name__ == "__main__":
    unittest.main()
