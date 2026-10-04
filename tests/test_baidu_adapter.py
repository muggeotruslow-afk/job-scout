import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location('baidu_adapter', Path(__file__).resolve().parents[1] / 'scripts/baidu_adapter.py')
adapter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(adapter)

def row(number):
    return {'postId': str(number), 'name': f'示例产品实习生 {number}', 'projectTypeCode': '-1',
            'projectType': '日常实习项目', 'workContent': '示例职责', 'serviceCondition': '本科在读'}

def response(page, total, rows):
    return {'status': 'ok', 'data': {'pageNum': page, 'total': total, 'list': rows}}

class BaiduTests(unittest.TestCase):
    def test_later_page_failure_preserves_obtained_jobs(self):
        def request(params):
            if params['curPage'] == 2:
                raise RuntimeError('connection interrupted')
            return response(1, 20, [row(i) for i in range(10)])
        result = adapter.fetch_baidu('', 50, request_page=request)
        self.assertFalse(result['ok'])
        self.assertEqual(result['fetched'], 10)
        self.assertFalse(result['pagination']['complete'])
        self.assertEqual(result['errors'][0]['page'], 2)

    def test_pagination_filters_dates_and_normalization(self):
        calls = []
        def request(params):
            calls.append(params)
            return response(params['curPage'], 11, [row(i) for i in range(10)] if params['curPage'] == 1 else [row(10)])
        result = adapter.fetch_baidu('AI', 50, 'product', request_page=request)
        self.assertTrue(result['pagination']['complete'])
        self.assertEqual(result['fetched'], 11)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0]['keyWord'], 'AI')
        self.assertEqual(calls[0]['postType[0]'], '2')
        self.assertEqual(calls[0]['projectType'], '-1')
        self.assertEqual(calls[0]['pageSize'], 10)
        self.assertIsNone(result['positions'][0]['posted_date'])
        self.assertIn('/detail/INTERN/', result['positions'][0]['source_url'])

    def test_repeated_page_is_incomplete(self):
        result = adapter.fetch_baidu('', 50, request_page=lambda p: response(p['curPage'], 20, [row(i) for i in range(10)]))
        self.assertFalse(result['pagination']['complete'])
        self.assertEqual(result['pagination']['stop_reason'], 'repeated_page')
        self.assertEqual(result['fetched'], 10)

    def test_max_pages_is_incomplete(self):
        result = adapter.fetch_baidu('', 1, request_page=lambda p: response(1, 20, [row(i) for i in range(10)]))
        self.assertFalse(result['pagination']['complete'])
        self.assertEqual(result['pagination']['stop_reason'], 'max_pages')

    def test_empty_page_before_total_is_incomplete(self):
        result = adapter.fetch_baidu('', 50, request_page=lambda p: response(p['curPage'], 20, [row(1)] if p['curPage'] == 1 else []))
        self.assertFalse(result['pagination']['complete'])

    def test_zero_matches_is_complete(self):
        self.assertTrue(adapter.fetch_baidu('', 50, request_page=lambda p: response(1, 0, []))['pagination']['complete'])

    def test_wrong_page_or_failed_api_is_rejected(self):
        for data in [response(2, 1, [row(1)]), {'status': 'fail', 'message': 'schema changed'}]:
            with self.assertRaises(RuntimeError):
                adapter.fetch_baidu('', 50, request_page=lambda p: data)

    def test_non_daily_row_is_rejected(self):
        item = row(1); item['projectTypeCode'] = '9'; item['projectType'] = '暑期实习项目'
        with self.assertRaises(RuntimeError):
            adapter.fetch_baidu('', 50, request_page=lambda p: response(1, 1, [item]))

if __name__ == '__main__':
    unittest.main()
