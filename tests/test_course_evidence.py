"""Independent SQL and artifact checks for the course evidence chain."""
from contextlib import closing
import hashlib,json,os,re,sqlite3,unittest
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
class CourseEvidenceTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.d=json.loads((ROOT/'reports/analysis_snapshot.json').read_text())
  cls.source=Path(os.environ.get('OLIST_SOURCE_DB',str(ROOT/'data/olist.sqlite')))
 def conn(self):
  if not self.source.exists():self.skipTest('原始数据未随交付包分发，取得后可运行数据核验')
  return closing(sqlite3.connect(f'file:{self.source}?mode=ro',uri=True))
 def test_independent_order_amount_and_rating(self):
  with self.conn() as c:
   self.assertEqual(c.execute('SELECT COUNT(DISTINCT order_id) FROM orders').fetchone()[0],self.d['summary']['orders'])
   self.assertAlmostEqual(c.execute('SELECT SUM(price) FROM order_items').fetchone()[0],self.d['summary']['sales'],places=2)
   avg,count=c.execute('SELECT AVG(rating),COUNT(*) FROM (SELECT order_id,AVG(review_score) rating FROM reviews WHERE review_score BETWEEN 1 AND 5 GROUP BY order_id)').fetchone()
   self.assertAlmostEqual(avg,self.d['summary']['rating'],places=10);self.assertEqual(count,self.d['summary']['rated_orders'])
 def test_independent_delivery_denominator_and_late(self):
  with self.conn() as c:
   count,late=c.execute("SELECT COUNT(*),SUM(date(order_delivered_customer_date)>date(order_estimated_delivery_date)) FROM orders WHERE order_status='delivered' AND order_delivered_customer_date IS NOT NULL AND julianday(order_delivered_customer_date)>=julianday(order_purchase_timestamp)").fetchone()
   self.assertEqual(count,self.d['summary']['delivery_sample']);self.assertEqual(late,self.d['summary']['late_orders'])
 def test_ledger_and_aggregate_conservation(self):
  for z in self.d['ledger']:self.assertEqual(z['input']-z['removed'],z['output'])
  for key in ['states','categories','months']:self.assertAlmostEqual(sum(z['sales'] for z in self.d[key]),self.d['summary']['sales'],places=2)
 def test_event_grain_matches_independent_sql(self):
  with self.conn() as c:
   for table,key in [('reviews','orders_multi_reviews'),('payments','orders_multi_payments')]:
    k=c.execute(f'SELECT COUNT(*) FROM (SELECT order_id FROM {table} GROUP BY order_id HAVING COUNT(*)>1)').fetchone()[0];self.assertEqual(k,self.d['extras'][key])
 def test_cohort_future_windows_and_weighted_m1(self):
  z=self.d['cohorts'];m1=[x for x in z if x['month']==1 and x['observed']]
  self.assertAlmostEqual(sum(x['returning'] for x in m1)/sum(x['customers'] for x in m1)*100,self.d['repeat']['pct'])
  for x in z:
   if not x['observed']:self.assertIsNone(x['returning']);self.assertIsNone(x['pct'])
   else:self.assertLessEqual(x['returning'],x['customers']);self.assertAlmostEqual(x['returning']/x['customers']*100,x['pct'])
  self.assertTrue(any(not x['observed'] for x in z))
 def test_low_score_denominator_and_atlas_agree(self):
  z=self.d['risk'];rate=sum(x['low'] for x in z[1:])/sum(x['n'] for x in z[1:])*100
  v=next(x for x in self.d['sensitivity'] if x['year']=='all' and x['cutoff']==2);self.assertAlmostEqual(rate,v['late_pct'])
  atlas=json.loads((ROOT/'deliverables/analysis/research_data.json').read_text())['all']
  self.assertAlmostEqual(atlas['summary']['late_low'],rate);self.assertEqual(atlas['summary']['repeat_cohort']['cohort_n'],self.d['repeat']['cohorts'])
 def test_check_ids_and_privacy_of_exports(self):
  ids=[x['id'] for x in self.d['checks']];self.assertEqual(len(ids),len(set(ids)))
  for file in (ROOT/'reports/evidence').glob('*.csv'):
   content=file.read_text(encoding='utf-8-sig');self.assertIsNone(re.search(r'\b[0-9a-f]{32}\b',content),file.name)
  for key in ['states','categories','months','risk','cohorts','sensitivity']:
   for row in self.d[key]:self.assertNotIn('order_id',row);self.assertNotIn('customer_unique_id',row)
 def test_docx_structure_and_caption_ids(self):
  ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
  for file in (ROOT/'reports').glob('Olist*_中蓝版.docx'):
   with ZipFile(file) as z:
    xml=z.read('word/document.xml').decode();root=ET.fromstring(xml)
   self.assertIn('TOC ',xml);self.assertIn('Heading1',xml)
   paragraphs=[''.join(e.itertext()) for e in root.findall('.//w:p',ns)]
   text=''.join(root.itertext())
   if '模板' not in file.name:self.assertNotIn('【',text)
   captions=[m.group(0) for s in paragraphs for m in [re.match(r'(?:表|图) [A-Z0-9]+-\d+',s)] if m]
   self.assertEqual(len(captions),len(set(captions)),file.name)
 def test_source_manifest(self):
  for name,meta in self.d['source_manifest'].items():
   path=ROOT/'data/raw'/name
   if not path.exists():continue
   self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),meta['sha256'])
if __name__=='__main__':unittest.main()
