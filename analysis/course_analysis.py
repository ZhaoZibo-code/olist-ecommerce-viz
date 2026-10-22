"""Course audit and report evidence. Reads raw tables; exports aggregates only."""
from pathlib import Path
import hashlib,json,math,sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
sys.path.insert(0,str(Path(__file__).resolve().parent))
from pipeline import load_data,aggregates,REGION,CONFIG
from advanced_report import NAMES,wilson
from report_contract import cohort_matrix
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports'; FIG=OUT/'figures'; EVID=OUT/'evidence'
GREEN='#317963'; BLUE='#4c7eaa'; GOLD='#be8a43'; RED='#bb6651'
KEYS={'orders':['order_id'],'customers':['customer_id'],'order_items':['order_id','order_item_id'],'payments':['order_id','payment_sequential'],'reviews':['review_id','order_id'],'products':['product_id'],'sellers':['seller_id']}
FIELDS={
'product_name_length':'产品名称字符数，不用于核心业务指标', 'product_description_length':'产品描述字符数，不是描述正文', 'product_photos_qty':'商品图片数量 / 张', 'product_weight_g':'商品重量 / 克', 'product_length_cm':'商品长度 / 厘米', 'product_height_cm':'商品高度 / 厘米', 'product_width_cm':'商品宽度 / 厘米',
'order_id':'订单标识，仅本地关联，不对外展示', 'customer_id':'订单对应客户标识，不能作为稳定客户身份', 'customer_unique_id':'稳定客户标识，用于本地回购队列',
'order_status':'订单状态，保留全部状态用于规模描述','order_purchase_timestamp':'下单时间，按原始记录解释，不转换时区','order_approved_at':'支付批准时间，允许业务性缺失',
'order_delivered_carrier_date':'交承运商时间','order_delivered_customer_date':'实际送达时间，配送时长需非空','order_estimated_delivery_date':'预计送达日期，延迟按日历日判断',
'order_item_id':'订单内商品行序号，与订单标识构成复合键','product_id':'商品标识','seller_id':'卖家标识','price':'商品行金额 BRL，不含运费',
'freight_value':'商品行运费 BRL','payment_sequential':'订单内支付序号','payment_type':'支付方式','payment_installments':'分期期数','payment_value':'支付金额 BRL，可能包含运费',
'review_id':'评价标识，可能跨订单复用，不能单独作唯一键','review_score':'原始星级 1至5，同单先平均','review_comment_title':'评价标题，不用于分析及外部交付','review_comment_message':'评价正文，不用于分析及外部交付',
'review_creation_date':'评价创建时间','review_answer_timestamp':'评价回应时间','product_category_name':'葡语品类，缺失归为未分类',
'customer_state':'客户州，两位代码','seller_state':'卖家州，两位代码','customer_city':'客户城市，分析不用','seller_city':'卖家城市，分析不用',
'customer_zip_code_prefix':'客户邮编前缀，分析不用','seller_zip_code_prefix':'卖家邮编前缀，分析不用','shipping_limit_date':'商品行发货期限'}

def rec(df):return json.loads(df.to_json(orient='records',force_ascii=False,date_format='iso'))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pct(k,n):return 100*k/n if n else 0

def build_evidence():
 t,o,quality=load_data();_,a,s=aggregates(t,o,'all');checks=[];profiles=[]
 def check(id,dim,label,k,n,decision,unit='行'):
  checks.append(dict(id=id,dimension=dim,check=label,affected=int(k),denominator=int(n),pct=pct(k,n),unit=unit,status='通过' if k==0 else '注意',decision=decision))
 for table,df in t.items():
  check('DQ-'+str(len(checks)+1).zfill(2),'唯一性',table+'复合业务键重复',df.duplicated(KEYS[table]).sum(),len(df),'重复会终止合并；本批无需删除')
  for col in df:
   s0=df[col]; non=s0.dropna();r=''
   if col.endswith(('_id','_unique_id')):r='标识字段，仅记录长度与基数'
   elif pd.api.types.is_numeric_dtype(s0):r=f'{non.min():g} 至 {non.max():g}' if len(non) else '无有效值'
   elif len(non) and non.nunique()<=30:r=' / '.join(map(str,sorted(non.unique())))
   else:r='文本或日期；不输出原始取值'
   profiles.append(dict(table=table,field=col,type=str(s0.dtype),missing=int(s0.isna().sum()),missing_pct=pct(s0.isna().sum(),len(df)),distinct=int(s0.nunique()),range=r,meaning=FIELDS.get(col,'商品属性：长度、重量、图文数量；用于质量检查，不参与核心指标')))
 n=len(o); raworders=t['orders'];delivered=o.order_status.eq('delivered')
 for col in ['order_purchase_timestamp','order_estimated_delivery_date','order_approved_at','order_delivered_carrier_date','order_delivered_customer_date']:
  df=raworders; vals=pd.to_datetime(df[col],errors='coerce');bad=df[col].notna()&vals.isna()
  check('DQ-'+str(len(checks)+1).zfill(2),'规范性',col+'解析失败',bad.sum(),len(df),'无效日期转为空，仅从依赖该字段的指标排除')
 check('DQ-13','完整性','订单缺商品明细',quality['missing_item_orders'],n,'订单保留；商品金额填0表示本提取无商品金额记录，不解释成免费订单','订单')
 check('DQ-14','完整性','订单缺有效评分',o.rating.isna().sum(),n,'订单保留，评分指标按有评分订单计算','订单')
 check('DQ-15','完整性','已送达订单缺实际送达时间',(delivered&o.order_delivered_customer_date.isna()).sum(),delivered.sum(),'仅从配送时长与延迟指标排除','订单')
 check('DQ-16','完整性','产品缺品类',t['products'].product_category_name.isna().sum(),len(t['products']),'商品保留，品类填unknown，报告归入未分类')
 links=[('orders','customer_id','customers','customer_id'),('order_items','order_id','orders','order_id'),('order_items','product_id','products','product_id'),('order_items','seller_id','sellers','seller_id'),('payments','order_id','orders','order_id'),('reviews','order_id','orders','order_id')]
 for left,lk,right,rk in links:
  check('DQ-'+str(len(checks)+1).zfill(2),'一致性',left+'关联'+right+'失败',(~t[left][lk].isin(t[right][rk])).sum(),len(t[left]),'关联失败应中止核查，避免静默丢失；本批无需排除')
 for table,cols in [('orders',['order_id','customer_id']),('customers',['customer_id','customer_unique_id']),('products',['product_id']),('sellers',['seller_id'])]:
  bad=pd.concat([~t[table][c].fillna('').str.fullmatch('[0-9a-f]{32}') for c in cols],axis=1).any(axis=1)
  check('DQ-'+str(len(checks)+1).zfill(2),'规范性',table+'标识长度与字符',bad.sum(),len(bad),'用于关联，不对外导出标识值')
 check('DQ-'+str(len(checks)+1).zfill(2),'合理性','评价星级超范围',(~t['reviews'].review_score.between(CONFIG['valid_score_min'],CONFIG['valid_score_max'])).sum(),len(t['reviews']),'排除越界评价，保留订单')
 for table,cols in [('order_items',['price','freight_value']),('payments',['payment_value'])]:
  bad=t[table][cols].lt(0).any(axis=1)
  check('DQ-'+str(len(checks)+1).zfill(2),'合理性',table+'金额为负',bad.sum(),len(bad),'负金额应隔离核查，不盲目取绝对值')
 early=delivered&o.order_delivered_customer_date.notna()&(o.order_delivered_customer_date<o.order_purchase_timestamp)
 check('DQ-'+str(len(checks)+1).zfill(2),'合理性','已送达时间早于下单',early.sum(),delivered.sum(),'仅从配送指标排除','订单')
 carrier_after=delivered&o.order_delivered_carrier_date.notna()&o.order_delivered_customer_date.notna()&(o.order_delivered_carrier_date>o.order_delivered_customer_date)
 check('DQ-'+str(len(checks)+1).zfill(2),'一致性','交承运商晚于客户送达',carrier_after.sum(),delivered.sum(),'不用承运商时间计算配送时长；保留下单至送达指标并披露','订单')
 for table,col in [('customers','customer_state'),('sellers','seller_state')]:
  check('DQ-'+str(len(checks)+1).zfill(2),'规范性',table+'州代码不在27州映射',(~t[table][col].isin(REGION)).sum(),len(t[table]),'异常州代码归未知，禁止猜测地理归属')
 # Distinguish one-to-many events from duplicate data.
 reviews=t['reviews']; multi=reviews.groupby('order_id').size(); paymentseq=t['payments'].groupby('order_id').size()
 extras={'orders_multi_reviews':int(multi.gt(1).sum()),'review_extra_rows':int((multi-1).clip(lower=0).sum()),'review_id_reused':int(reviews.review_id.duplicated().sum()),'orders_multi_payments':int(paymentseq.gt(1).sum()),'missing_payment_orders':int((~o.order_id.isin(t['payments'].order_id)).sum()),'item_category_missing_rows':int(t['order_items'].merge(t['products'][['product_id','product_category_name']],on='product_id').product_category_name.isna().sum()),'carrier_after_delivery':int(carrier_after.sum()),'delivered_missing_date':int((delivered&o.order_delivered_customer_date.isna()).sum()),'products_missing_category':int(t['products'].product_category_name.isna().sum()),'review_title_missing':int(t['reviews'].review_comment_title.isna().sum()),'review_message_missing':int(t['reviews'].review_comment_message.isna().sum()),'delivery_tail_over_70':int(o.delivery_days.gt(CONFIG['display_delivery_max_days']).sum())}
 # An order-level comparison is diagnostic, not an enforced financial identity.
 pay=t['payments'].groupby('order_id').payment_value.sum(); goods=o.set_index('order_id'); common=goods.index.intersection(pay.index)
 diff=(pay.loc[common]-(goods.loc[common,'sales']+goods.loc[common,'freight'])).round(2)
 extras.update(payment_goods_comparable=len(common),payment_goods_mismatch=int(diff.abs().gt(.01).sum()),payment_goods_diff_total=float(diff.sum()),payment_total=float(t['payments'].payment_value.sum()),freight_total=float(t['order_items'].freight_value.sum()))
 ledger=[dict(stage='原始订单',input=n,removed=0,output=n),dict(stage='订单事实表 左连接与订单内聚合',input=n,removed=0,output=len(o)),dict(stage='配送样本 排除未送达状态',input=n,removed=int((~delivered).sum()),output=int(delivered.sum())),dict(stage='配送样本 排除送达时间缺失或逆序',input=int(delivered.sum()),removed=int(delivered.sum()-o.delivery_days.notna().sum()),output=int(o.delivery_days.notna().sum())),dict(stage='评分样本 独立于配送分支',input=n,removed=int(o.rating.isna().sum()),output=int(o.rating.notna().sum()))]
 assert all(r['input']-r['removed']==r['output'] for r in ledger)
 assert not any(c['affected'] for c in checks[:7]),'业务键存在重复，需要先解决'
 risk=o[o.delay_days.notna()&o.rating.notna()].copy();risk['group']=pd.cut(risk.delay_days,[-np.inf,*CONFIG['delay_bins'],np.inf],labels=['准时或提前','延迟1至3天','延迟4至7天','延迟8至14天','延迟15天及以上'])
 risks=[]
 for label,z in risk.groupby('group',observed=False):
  k=int(z.rating.le(CONFIG['low_score_max']).sum());lo,hi=wilson(k,len(z));risks.append(dict(group=str(label),n=len(z),low=k,pct=pct(k,len(z)),lo=lo,hi=hi))
 sensitivity=[]
 for cutoff in sorted(set(CONFIG['research_design']['sensitivity_cutoffs']+[CONFIG['low_score_max']])):
  for y in ['all',*map(str,CONFIG['research_design']['sensitivity_years'])]:
   z=risk if y=='all' else risk[risk.year.eq(int(y))]
   on=z[z.delay_days.le(0)];late=z[z.delay_days.gt(0)]
   p1=pct(on.rating.le(cutoff).sum(),len(on));p2=pct(late.rating.le(cutoff).sum(),len(late))
   sensitivity.append(dict(year=y,cutoff=cutoff,ontime_n=len(on),late_n=len(late),ontime_pct=p1,late_pct=p2,gap_pp=p2-p1))
 # Full observed delivered-order customer cohorts; exclude incomplete last month.
 customer=t['orders'][['order_id','customer_id','order_status','order_purchase_timestamp']].merge(t['customers'][['customer_id','customer_unique_id']],on='customer_id',validate='many_to_one')
 customer=customer[customer.order_status.eq('delivered')].copy();customer['period']=pd.to_datetime(customer.order_purchase_timestamp).dt.to_period('M');customer['cohort']=customer.customer_unique_id.map(customer.groupby('customer_unique_id').period.min());customer['offset']=[p.ordinal-c.ordinal for p,c in zip(customer.period,customer.cohort)]
 lastdate=pd.to_datetime(customer.order_purchase_timestamp).max();last=lastdate.to_period('M')-(1 if lastdate.day<lastdate.days_in_month else 0)
 sizes=customer[customer.offset.eq(0)].groupby('cohort').customer_unique_id.nunique();cohorts=[]
 for co,nc in sizes.items():
  if nc<CONFIG['cohort_min_customers'] or co>=last:continue
  for m in range(1,CONFIG['cohort_horizon_months']+1):
   observed=co+m<=last;k=int(customer.loc[customer.cohort.eq(co)&customer.offset.eq(m),'customer_unique_id'].nunique()) if observed else None
   cohorts.append(dict(cohort=str(co),customers=int(nc),month=m,observed=observed,returning=k,pct=pct(k,nc) if observed else None))
 m1=[x for x in cohorts if x['month']==1 and x['observed']];repeat={'last_complete_month':str(last),'cohorts':len(m1),'customers':sum(x['customers'] for x in m1),'returning':sum(x['returning'] for x in m1)};repeat['pct']=pct(repeat['returning'],repeat['customers'])
 years=o.groupby('year').agg(orders=('order_id','size'),sales=('sales','sum')).reset_index(); months=a['trend'];daily=o.groupby(o.order_purchase_timestamp.dt.normalize()).size()
 states=a['states'].copy();states['delivery_n']=states.customer_state.map(o.groupby('customer_state').delivery_days.count());states['share']=states.sales/states.sales.sum()*100
 cats=a['categories'].copy();cats['name']=cats.category.map(NAMES).fillna(cats.category);cats['cum_pct']=cats.sales.cumsum()/cats.sales.sum()*100
 partial=o[~o.month.between('2017-01','2018-08')]
 scope={'start':quality['date_start'],'end':quality['date_end'],'years':rec(years),'outside_main_months':len(partial),'main_month_orders':int(o.month.between('2017-01','2018-08').sum()),'peak_day':str(daily.idxmax().date()),'peak_day_orders':int(daily.max()),'top3_share':float(states.head(3).share.sum()),'pareto80':int(cats.cum_pct.lt(CONFIG['research_design']['pareto_target_pct']).sum()+1),'freight_pct':float(extras['freight_total']/s['sales']*100)}
 raw=ROOT/'data/raw';manifest={p.name:dict(bytes=p.stat().st_size,sha256=digest(p)) for p in sorted(raw.glob('*.sql'))}
 dictionary=[]
 for table,df in t.items():
  for c in df:
   dictionary.append(dict(table=table,field=c,meaning=FIELDS.get(c,'商品描述属性，按字段单位解释'),privacy='本地保留 外部排除' if c.endswith('_id') or any(w in c for w in ['comment','city','zip']) else '允许汇总使用'))
 return dict(config=CONFIG,quality=quality,checks=checks,profiles=profiles,ledger=ledger,extras=extras,scope=scope,summary=s,states=rec(states),categories=rec(cats),months=rec(months),ratings=rec(a['ratings']),risk=risks,sensitivity=sensitivity,cohorts=cohorts,repeat=repeat,source_manifest=manifest,field_dictionary=dictionary),o

def charts(d,o):
 for bundled in (ROOT/'assets/report-fonts').glob('*.otf'):font_manager.fontManager.addfont(bundled)
 for name in ['Regular','Bold']:
  p=Path('/Users/ZZB/Library/Fonts')/f'NotoSerifCJKsc-{name}.otf'
  if p.exists():font_manager.fontManager.addfont(p)
 fallback=ROOT/'assets/report-font.otf'
 if fallback.exists():font_manager.fontManager.addfont(fallback)
 plt.rcParams.update({'font.family':['Times New Roman','Noto Serif CJK SC'],'font.size':11,'axes.spines.top':False,'axes.spines.right':False,'axes.unicode_minus':False,'axes.labelcolor':'#334b44','text.color':'#203c34','xtick.color':'#53645e','ytick.color':'#53645e','savefig.facecolor':'white'})
 def start():return plt.subplots(figsize=(8.6,3.75),layout='constrained')
 def save(fig,name):
  fig.savefig(FIG/(name+'.png'),dpi=200);fig.savefig(FIG/(name+'.svg'));plt.close(fig)
 fig,ax=start(); z=d['quality']['table_rows'];ax.barh(list(z)[::-1],list(z.values())[::-1],color=GREEN);ax.set_xlabel('原始表行数 / 行');ax.bar_label(ax.containers[0],fmt='{:,.0f}',padding=4,fontsize=10);ax.set_xlim(0,max(z.values())*1.2);save(fig,'q01_tables')
 fig,ax=start();z=[p for p in d['profiles'] if p['missing'] and p['field'] not in ['review_comment_title','review_comment_message']]; labels=[p['table']+'.'+p['field'].replace('order_','') for p in z];ax.barh(labels[::-1],[p['missing_pct'] for p in z][::-1],color=GOLD);ax.set_xlabel('字段缺失率 / %（分母为该字段所在表行数）');ax.tick_params(axis='y',labelsize=9);save(fig,'q02_missing')
 fig,ax=start();z=d['ledger'];ax.barh(['订单事实表','已送达状态','有效配送','有效评分'],[z[1]['output'],z[2]['output'],z[3]['output'],z[4]['output']],color=[GREEN,BLUE,BLUE,GOLD]);ax.invert_yaxis();ax.bar_label(ax.containers[0],fmt='{:,.0f}',padding=4);ax.set_xlim(0,len(o)*1.18);ax.set_xlabel('订单数 / 笔（配送与评分为独立分支）');save(fig,'q03_ledger')
 fig,ax=start();z=pd.DataFrame(d['months']);ax.bar(range(len(z)),z.orders,color=GREEN);ax.set_xticks(range(0,len(z),3),z.month.iloc[::3],rotation=30);ax.set_ylabel('订单数 / 笔');save(fig,'q04_months')
 fig,ax=start();z=pd.DataFrame(d['months']);ax.plot(range(len(z)),z.orders,color=GREEN,marker='o',ms=3);ax.set_xticks(range(0,len(z),3),z.month.iloc[::3],rotation=30);ax.set_ylabel('订单数 / 笔');ax2=ax.twinx();ax2.plot(range(len(z)),z.sales/1e6,color=GOLD,ls='--',label='商品金额');ax2.set_ylabel('商品金额 / 百万BRL');ax.text(.02,.94,'实线 订单量    虚线 商品金额',transform=ax.transAxes,fontsize=10);save(fig,'a01_trend')
 fig,ax=start();z=pd.DataFrame(d['states']).head(10).iloc[::-1];ax.barh(z.customer_state,z.share,color=GREEN);ax.bar_label(ax.containers[0],fmt='{:.1f}%',padding=4);ax.set_xlim(0,z.share.max()*1.2);ax.set_xlabel('商品金额占全样本比例 / %');save(fig,'a02_states')
 fig,ax=start();z=o.groupby('customer_state').agg(n=('delivery_days','count'),median=('delivery_days','median'),late=('late','mean'));z=z.loc[pd.DataFrame(d['states']).head(10).customer_state];ax.scatter(z['median'],z.late*100,s=z.n/110+25,color=BLUE,alpha=.7,edgecolor='white');
 for state,r in z.iterrows():ax.annotate(state,(r['median'],r.late*100),xytext=(4,3),textcoords='offset points')
 ax.set_xlabel('配送时长中位数 / 自然日');ax.set_ylabel('延迟订单比例 / %');save(fig,'a03_delivery_states')
 fig,ax=start();z=pd.DataFrame(d['categories']).head(10).iloc[::-1];ax.barh(z.name,z.sales/1e6,color=GREEN);ax.set_xlabel('商品金额 / 百万BRL');save(fig,'a04_categories')
 fig,ax=start();z=pd.DataFrame(d['categories']);ax.plot(range(1,len(z)+1),z.cum_pct,color=GREEN);ax.axhline(80,color=RED,ls=':');ax.axvline(d['scope']['pareto80'],color=GOLD,ls=':');ax.set_xlabel('按商品金额降序累计的品类数 / 类');ax.set_ylabel('累计商品金额占比 / %');ax.set_ylim(0,105);save(fig,'a05_pareto')
 fig,ax=start();v=o.delivery_days.dropna();ax.hist(v,bins=np.arange(0,72,2),color=BLUE,edgecolor='white');ax.axvline(v.median(),color=RED,ls='--',label=f'中位数 {v.median():.2f}天');ax.set_xlim(0,70);ax.set_xlabel('配送时长 / 自然日（图示0至70天）');ax.set_ylabel('有效配送订单数 / 笔');ax.legend(frameon=False);save(fig,'a06_delivery')
 fig,ax=start();z=pd.DataFrame(d['risk']);ax.errorbar(z.pct,range(len(z)),xerr=[z.pct-z.lo,z.hi-z.pct],fmt='o',color=GREEN,capsize=4);ax.set_yticks(range(len(z)),z.group);ax.invert_yaxis();ax.set_xlim(0,100);ax.set_xlabel('订单均分≤2的比例 / %（Wilson 95%区间）');
 for i,r in z.iterrows():ax.text(99,i,f'n={r.n:,}',ha='right',va='center',fontsize=10)
 save(fig,'a07_risk')
 fig,ax=start();z=pd.DataFrame(d['sensitivity']);z=z[z.year.eq('all')];x=np.arange(len(z));ax.bar(x-.16,z.ontime_pct,width=.32,color=GREEN,label='准时或提前');ax.bar(x+.16,z.late_pct,width=.32,color=RED,label='延迟');ax.set_xticks(x,[f'订单均分≤{c}' for c in z.cutoff]);ax.set_ylabel('对应组别内占比 / %');ax.legend(frameon=False);save(fig,'a08_sensitivity')
 fig,ax=start();z=cohort_matrix(d['cohorts'],CONFIG);im=ax.imshow(z.to_numpy(),aspect='auto',cmap='Blues',vmin=0,vmax=max(1,np.nanmax(z)));ax.set_xticks(range(len(z.columns)),['M+'+str(i) for i in z.columns]);ax.set_yticks(range(len(z)),z.index,fontsize=8);ax.set_xlabel('距首次观察到已送达购买的月数');fig.colorbar(im,ax=ax,label='当月回购客户 / 队列客户 · %');save(fig,'a09_cohort')
 fig,ax=start(); z=o[o.sales.gt(0)].copy();ratio=z.freight/z.sales*100;ax.hist(ratio[ratio.le(100)],bins=40,color=GOLD,edgecolor='white');ax.set_xlabel('订单运费 / 订单商品金额 · %（图示0至100%）');ax.set_ylabel('订单数 / 笔');save(fig,'a10_freight')

def main():
 OUT.mkdir(exist_ok=True);FIG.mkdir(exist_ok=True);EVID.mkdir(exist_ok=True)
 d,o=build_evidence()
 (OUT/'analysis_snapshot.json').write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False))
 for key in ['checks','profiles','ledger','states','categories','months','risk','sensitivity','cohorts','field_dictionary']:
  pd.DataFrame(d[key]).to_csv(EVID/(key+'.csv'),index=False,encoding='utf-8-sig')
 from editorial_analysis import main as editorial
 editorial(d,o)
 print(json.dumps({k:d[k] for k in ['summary','extras','scope','repeat']},ensure_ascii=False,indent=2))
 print('Audit checks:',len(d['checks']),'Fields:',len(d['profiles']),'Figures:',len(list(FIG.glob('*.png'))))
if __name__=='__main__':main()
