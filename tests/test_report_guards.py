"""Failure-mode checks for the actual report fixes."""
from pathlib import Path
import importlib.util,sys,unittest,tempfile,subprocess,json,shutil
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'analysis'))
from report_contract import validate_sources,checked_item_merge,state_comparisons,cohort_matrix,KEYS,require_files,validate_config
class ReportGuardTests(unittest.TestCase):
 def sources(self):
  return {'orders':pd.DataFrame({'order_id':['o'],'customer_id':['c']}),'customers':pd.DataFrame({'customer_id':['c']}),'order_items':pd.DataFrame({'order_id':['o'],'order_item_id':[1],'product_id':['p'],'seller_id':['s']}),'products':pd.DataFrame({'product_id':['p']}),'sellers':pd.DataFrame({'seller_id':['s']}),'payments':pd.DataFrame({'order_id':['o'],'payment_sequential':[1]}),'reviews':pd.DataFrame({'review_id':['r'],'order_id':['o']})}
 def test_foreign_key_failure_stops_before_join(self):
  data=self.sources();validate_sources(data);data['order_items'].loc[0,'product_id']='missing'
  with self.assertRaisesRegex(ValueError,'unmatched=1'):validate_sources(data)
 def test_duplicate_and_null_business_keys_stop(self):
  data=self.sources();data['products']=pd.concat([data['products']]*2)
  with self.assertRaisesRegex(ValueError,'duplicate keys=1'):validate_sources(data)
  data=self.sources();data['orders'].loc[0,'order_id']=None
  with self.assertRaisesRegex(ValueError,'null keys=1'):validate_sources(data)
 def test_item_dimension_does_not_silently_drop(self):
  items=pd.DataFrame({'product_id':['p','q'],'price':[10.,20.]});dimension=pd.DataFrame({'product_id':['p'],'category':['x']})
  with self.assertRaisesRegex(ValueError,'未匹配'):checked_item_merge(items,dimension,'product_id')
  dimension=pd.DataFrame({'product_id':['p','q'],'category':['x','y']});self.assertEqual(checked_item_merge(items,dimension,'product_id').price.sum(),30)
 def test_low_score_and_sample_config_control_state_analysis(self):
  orders=pd.DataFrame({'customer_state':['SP']*4,'delay_days':[0,0,1,1],'rating':[1,2,2,3]});config={'low_score_max':1,'state_min_delivery_sample':2}
  one=state_comparisons(orders,config,lambda k,n:(0,100));self.assertEqual((one[0]['on_low'],one[0]['late_low']),(1,0))
  config['low_score_max']=2;two=state_comparisons(orders,config,lambda k,n:(0,100));self.assertEqual((two[0]['on_low'],two[0]['late_low']),(2,1))
  config['state_min_delivery_sample']=3;self.assertEqual(state_comparisons(orders,config,lambda k,n:(0,100)),[])
 def test_cohort_columns_follow_short_and_long_horizons(self):
  rows=[{'cohort':'2020-01','month':i,'pct':.1*i} for i in range(1,9)]
  for horizon in [3,8]:self.assertEqual(list(cohort_matrix(rows,{'cohort_horizon_months':horizon}).columns),list(range(1,horizon+1)))
 def test_absent_or_single_pdf_cannot_pass(self):
  runtime=Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3'
  with tempfile.TemporaryDirectory() as temp:
   work=Path(temp);(work/'scripts').mkdir();(work/'reports').mkdir();script=work/'scripts/verify_pdf_output.py';shutil.copy2(ROOT/'scripts/verify_pdf_output.py',script)
   for single in [False,True]:
    if single:(work/'reports/Olist数据质量分析报告_中蓝版.pdf').write_bytes(b'placeholder')
    p=subprocess.run([str(runtime if runtime.exists() else sys.executable),str(script)],capture_output=True,text=True)
    self.assertNotEqual(p.returncode,0)
    self.assertEqual(json.loads((work/'reports/pdf_verification.json').read_text())['result'],'failed')
 def test_missing_evidence_or_figure_fails(self):
  with tempfile.TemporaryDirectory() as temp:
   with self.assertRaisesRegex(ValueError,'产物缺失'):require_files([Path(temp)/'q01.png'])
 def test_fixed_research_design_is_not_silently_ignored(self):
  c=json.loads((ROOT/'configs/analysis.json').read_text());validate_config(c);c['research_design']['calendar_year']=2020
  with self.assertRaisesRegex(ValueError,'固定研究设计'):validate_config(c)
if __name__=='__main__':unittest.main()
