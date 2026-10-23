"""Independent checks for the detailed report comparisons and requested font/team rules."""
from contextlib import closing
import json,os,sqlite3,unittest
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
class ExtendedEvidenceTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.x=json.loads((ROOT/'reports/extended_snapshot.json').read_text());cls.d=json.loads((ROOT/'reports/analysis_snapshot.json').read_text());cls.cfg=json.loads((ROOT/'configs/analysis.json').read_text())
 def conn(self):
  source=Path(os.environ.get('OLIST_SOURCE_DB',str(ROOT/'data/olist.sqlite')))
  if not source.exists():self.skipTest('取得原始SQL后验证独立来源计算')
  return closing(sqlite3.connect(f'file:{source}?mode=ro',uri=True))
 def test_each_team_member_has_25_percent(self):
  for config in [self.cfg,self.d['config']]:self.assertEqual([p['share'] for p in config['team']],[25]*4)
 def test_month_windows_match_independent_sql(self):
  with self.conn() as c:
   for year in [2017,2018]:
    got=c.execute('SELECT COUNT(*) FROM orders WHERE order_purchase_timestamp>=? AND order_purchase_timestamp<?',(f'{year}-01-01',f'{year}-09-01')).fetchone()[0]
    self.assertEqual(got,self.x['comparable_period'][str(year)+'_orders'])
 def test_state_risk_against_independent_sql(self):
  with self.conn() as c:
   rows=c.execute("""WITH r AS (SELECT order_id,AVG(review_score) rating FROM reviews WHERE review_score BETWEEN 1 AND 5 GROUP BY order_id)
   SELECT customer_state,(date(order_delivered_customer_date)>date(order_estimated_delivery_date)) late,COUNT(*),SUM(rating<=2)
   FROM orders JOIN customers USING(customer_id) JOIN r USING(order_id)
   WHERE order_status='delivered' AND order_delivered_customer_date IS NOT NULL AND order_estimated_delivery_date IS NOT NULL
   AND julianday(order_delivered_customer_date)>=julianday(order_purchase_timestamp)
   GROUP BY customer_state,late""").fetchall()
  lookup={(s,int(l)):(nn,k) for s,l,nn,k in rows}
  for z in self.x['state_risk']:
   self.assertEqual(lookup[(z['state'],0)],(z['on_n'],z['on_low']));self.assertEqual(lookup[(z['state'],1)],(z['late_n'],z['late_low']))
   self.assertGreaterEqual(z['on_n'],30);self.assertGreaterEqual(z['late_n'],30)
 def test_transaction_and_category_conservation(self):
  for key in ['states','categories','sectors','flows']:self.assertAlmostEqual(sum(r['sales'] for r in self.x[key]),self.d['summary']['sales'],places=2)
  self.assertEqual(sum(z['n'] for z in self.x['missing_by_status']),self.d['summary']['orders'])
  self.assertEqual(sum(z['item_missing'] for z in self.x['missing_by_status']),self.d['quality']['missing_item_orders'])
 def test_payment_difference_buckets_reconcile(self):
  x=self.x['payment_reconciliation'];b=self.x['payment_diff_bins'];self.assertEqual(sum(z['orders'] for z in b),x['n']);self.assertEqual(b[3]['orders'],x['equal'])
  self.assertEqual(x['positive']+x['negative']+x['equal'],x['n'])
 def test_freight_band_denominators_and_quantile_order(self):
  self.assertEqual(sum(z['n'] for z in self.x['freight_bands']),self.x['freight_ratio']['n'])
  for z in self.x['freight_bands']:self.assertLessEqual(z['p25'],z['median_ratio']);self.assertLessEqual(z['median_ratio'],z['p75'])
  vals=[self.x['delivery_quantiles'][str(q)] for q in [.05,.25,.5,.75,.9,.95,.99]];self.assertEqual(vals,sorted(vals))
 def test_used_word_styles_have_explicit_fonts_without_theme(self):
  ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'};prefix='{'+ns['w']+'}'
  for p in (ROOT/'reports').glob('Olist*_中蓝版.docx'):
   with ZipFile(p) as z:root=ET.fromstring(z.read('word/styles.xml'))
   for styleid in ['Normal','Title','Subtitle','Heading1','Heading2','Caption','Header','Footer']:
    style=next(s for s in root.findall('w:style',ns) if s.attrib[prefix+'styleId']==styleid);rf=style.find('w:rPr/w:rFonts',ns)
    self.assertEqual(rf.attrib.get(prefix+'ascii'),'Times New Roman',p.name+' '+styleid);self.assertEqual(rf.attrib.get(prefix+'eastAsia'),'Noto Serif CJK SC',p.name+' '+styleid)
    self.assertFalse(any('theme' in k.lower() for k in rf.attrib))
 def test_editorial_svgs_do_not_use_default_sans_fonts(self):
  files=list((ROOT/'reports/figures/editorial').glob('*.svg'));self.assertGreaterEqual(len(files),20)
  for p in files:
   text=p.read_text();self.assertNotIn('DejaVu',text,p.name);self.assertNotIn('Calibri',text,p.name)
if __name__=='__main__':unittest.main()
