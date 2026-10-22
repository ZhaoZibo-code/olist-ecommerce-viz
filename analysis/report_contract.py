"""Shared integrity checks and configurable report comparisons."""
from pathlib import Path
import math
import pandas as pd
KEYS={'orders':['order_id'],'customers':['customer_id'],'order_items':['order_id','order_item_id'],'payments':['order_id','payment_sequential'],'reviews':['review_id','order_id'],'products':['product_id'],'sellers':['seller_id']}
LINKS=[('orders','customer_id','customers','customer_id'),('order_items','order_id','orders','order_id'),('order_items','product_id','products','product_id'),('order_items','seller_id','sellers','seller_id'),('payments','order_id','orders','order_id'),('reviews','order_id','orders','order_id')]
FIGURES=['01_calendar','02_week_hour','03_comparable','04_geography','05_opportunity','06_treemap','07_category_risk','08_pareto','09_sankey','10_ridges','11_ecdf','12_risk','13_state_risk','14_sensitivity','15_cohort','16_freight','17_payment','q01_status_missing','q02_denominators','q03_stages','q04_money','q05_field_profile']

def validate_sources(tables):
 problems=[]
 for name,keys in KEYS.items():
  df=tables[name];null=int(df[keys].isna().any(axis=1).sum());dup=int(df.duplicated(keys).sum())
  if null or dup:problems.append(f'{name}: null keys={null}, duplicate keys={dup}')
 for left,lk,right,rk in LINKS:
  missing=int((~tables[left][lk].isin(tables[right][rk])).sum())
  if missing:problems.append(f'{left}.{lk} -> {right}.{rk}: unmatched={missing}')
 if problems:raise ValueError('源表关联校验失败；已中止，未删除异常行：'+'; '.join(problems))

def checked_item_merge(items,dimension,key):
 result=items.merge(dimension,on=key,how='left',validate='many_to_one',indicator=True)
 if not result['_merge'].eq('both').all():raise ValueError(f'{key}: 商品维表有未匹配记录，已中止')
 if len(result)!=len(items) or not math.isclose(float(result.price.sum()),float(items.price.sum()),abs_tol=.005,rel_tol=0):raise ValueError('商品连接行数或金额不守恒')
 return result.drop(columns='_merge')

def state_comparisons(o,config,wilson):
 z=o[o.delay_days.notna()&o.rating.notna()];rows=[]
 for state,g in z.groupby('customer_state'):
  a=g[g.delay_days.le(0)];b=g[g.delay_days.gt(0)]
  if min(len(a),len(b))<config['state_min_delivery_sample']:continue
  k=int(a.rating.le(config['low_score_max']).sum());m=int(b.rating.le(config['low_score_max']).sum());lo,hi=wilson(m,len(b))
  rows.append(dict(state=state,on_n=len(a),late_n=len(b),on_low=k,late_low=m,on_pct=k/len(a)*100,late_pct=m/len(b)*100,gap_pp=(m/len(b)-k/len(a))*100,lo=lo,hi=hi))
 return sorted(rows,key=lambda r:r['on_n']+r['late_n'],reverse=True)

def cohort_matrix(rows,config):
 return pd.DataFrame(rows).pivot(index='cohort',columns='month',values='pct').reindex(columns=range(1,config['cohort_horizon_months']+1))

def require_files(paths):
 missing=[str(p) for p in paths if not p.is_file() or p.stat().st_size==0]
 if missing:raise ValueError('产物缺失或为空：'+', '.join(missing))

def verify_aggregates(root):
 import json
 report=Path(root)/'reports';d=json.loads((report/'analysis_snapshot.json').read_text());x=json.loads((report/'extended_snapshot.json').read_text())
 if d['summary']['orders']!=d['quality']['table_rows']['orders']:raise ValueError('订单行数不守恒')
 if any(v['input']-v['removed']!=v['output'] for v in d['ledger']):raise ValueError('样本清洗对账失败')
 if any(v['affected'] for v in d['checks'] if v['dimension'] in ['唯一性','一致性'] and '交承运商' not in v['check']):raise ValueError('关键键或外键检查失败')
 if not math.isclose(sum(v['sales'] for v in x['categories']),d['summary']['sales'],abs_tol=.005,rel_tol=0):raise ValueError('品类金额不守恒')
 require_files([report/'figures/editorial'/(f+'.'+ext) for f in FIGURES for ext in ['png','svg']])
 require_files([report/'evidence'/(f+'.csv') for f in ['checks','profiles','ledger','risk','sensitivity','cohorts','field_dictionary']])
 return {'orders':d['summary']['orders'],'goods_total':d['summary']['sales'],'checks':len(d['checks']),'fields':len(d['profiles']),'figures':len(FIGURES),'delivery_sample':d['summary']['delivery_sample'],'rated_orders':d['summary']['rated_orders']}

def validate_config(config):
 # These dates/bins define this particular historical study, not tuning knobs.
 design=config['research_design']
 fixed={'calendar_year':2017,'comparison_years':[2017,2018],'comparison_month_end':8,'sensitivity_cutoffs':[1,2,3],'sensitivity_years':[2017,2018],'pareto_target_pct':80}
 if design!=fixed or config['delay_bins']!=[0,3,7,14]:raise ValueError('历史日期窗口、敏感性设计及延期分段为固定研究设计；改变研究设计需同步修改报告结构')
 if config['display_delivery_max_days']!=70:raise ValueError('当前研究固定展示0至70天；改变此窗口需同步修改报告解释')
 for key in ['state_min_delivery_sample','category_min_orders','cohort_min_customers','cohort_horizon_months']:
  if not isinstance(config[key],int) or config[key]<1:raise ValueError(key+'必须为正整数')
 if not config['valid_score_min']<=config['low_score_max']<=config['valid_score_max']:raise ValueError('低评分阈值超出星级范围')
