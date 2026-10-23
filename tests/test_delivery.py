from contextlib import closing
import json,sqlite3,unittest,os
from pathlib import Path
from fastapi.testclient import TestClient
from backend.app import app
ROOT=Path(__file__).resolve().parents[1]
class DeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.client=TestClient(app)
    def test_analysis_reconciliation(self):
        source=Path(os.environ.get('OLIST_SOURCE_DB',str(ROOT/'data/olist.sqlite')))
        if not source.exists():self.skipTest('原始数据未随交付包分发')
        d=self.client.get('/api/dashboard').json()
        self.assertEqual(d['summary']['orders'],99441)
        with closing(sqlite3.connect(f'file:{source}?mode=ro',uri=True)) as c:
            total=c.execute('SELECT SUM(price) FROM order_items').fetchone()[0]
        self.assertAlmostEqual(d['summary']['sales'],total,places=2)
        self.assertEqual(len(d['charts']),9)
        years=[self.client.get('/api/dashboard',params={'year':y}).json()['summary']['orders'] for y in ['2016','2017','2018']]
        self.assertEqual(sum(years),99441)
    def test_order_filters_and_pagination(self):
        if not (ROOT/'data/analysis.sqlite').exists():self.skipTest('取得原始数据并重跑后验证本地查询')
        p={'year':'2017','state':'SP','status':'delivered','size':3}
        first=self.client.get('/api/orders',params=p).json()
        second=self.client.get('/api/orders',params={**p,'page':2}).json()
        self.assertGreater(first['total'],6)
        self.assertFalse({r['order_id'] for r in first['rows']}&{r['order_id'] for r in second['rows']})
        for r in first['rows']:
            self.assertEqual(r['customer_state'],'SP');self.assertEqual(r['order_status'],'delivered');self.assertTrue(r['order_purchase_timestamp'].startswith('2017'))
        prefix=first['rows'][0]['order_id']
        got=self.client.get('/api/orders',params={'q':prefix}).json()
        self.assertEqual(got['total'],1)
    def test_validation_and_static_delivery(self):
        if not (ROOT/'data/analysis.sqlite').exists():
            self.assertEqual(self.client.get('/api/health').status_code,503)
        else:
            self.assertEqual(self.client.get('/api/health').status_code,200)
            self.assertEqual(self.client.get('/api/meta').status_code,200)
        for path in ['/api/dashboard?year=2026','/api/orders?page=0','/api/orders?size=101','/api/orders?q=%27%20OR%201=1--']:
            self.assertEqual(self.client.get(path).status_code,422)
        for path in ['/','/static/vendor/vue.global.prod.js','/static/vendor/plotly.min.js','/reports/analysis/analysis_report.html']:
            self.assertEqual(self.client.get(path).status_code,200,path)
    def test_exports_exist_and_are_offline(self):
        for suffix in ['png','svg']:
            self.assertGreater((ROOT/f'deliverables/analysis/matplotlib_overview.{suffix}').stat().st_size,10000)
        h=(ROOT/'deliverables/analysis/analysis_report.html').read_text()
        self.assertNotIn('__RESULTS__',h);self.assertNotIn('src="https://',h)
        self.assertIn('plotly.js',h)
if __name__=='__main__':unittest.main()
