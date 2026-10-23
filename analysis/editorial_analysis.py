"""Detailed aggregate evidence and publication charts inspired by ECharts examples."""
from pathlib import Path
import json,calendar,math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager,colors,patches
from matplotlib.path import Path as MPath
from matplotlib.ticker import FuncFormatter,PercentFormatter
from pipeline import load_data,REGION,CONFIG
from report_contract import checked_item_merge,state_comparisons,cohort_matrix
from advanced_report import NAMES,sector,wilson,CODES
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports';FIG=OUT/'figures/editorial'
T=CONFIG['theme'];NAVY=T['navy'];BLUE=T['blue'];ACCENT=T['accent'];MID=T['mid_blue'];LIGHT=T['light_blue'];INK=T['ink'];MUTED=T['muted'];PALE=T['pale']
COLORS=[NAVY,BLUE,MID,ACCENT,LIGHT]
REGION_COLOR={'东南部':NAVY,'南部':BLUE,'东北部':MID,'中西部':ACCENT,'北部':LIGHT}
def rec(df):return json.loads(df.to_json(orient='records',force_ascii=False,date_format='iso'))
def pct(k,n):return float(k/n*100) if n else None

def compute(d,o):
 t,_,_=load_data();x={};n=len(o)
 x['statuses']=rec(o.groupby('order_status',as_index=False).agg(orders=('order_id','size'),sales=('sales','sum'),rating=('rating','mean')))
 rows=[]
 for status,z in o.groupby('order_status'):
  rows.append(dict(status=status,n=len(z),approved_missing=int(z.order_approved_at.isna().sum()),carrier_missing=int(z.order_delivered_carrier_date.isna().sum()),delivery_missing=int(z.order_delivered_customer_date.isna().sum()),item_missing=int((~z.order_id.isin(t['order_items'].order_id)).sum()),rating_missing=int(z.rating.isna().sum())))
 x['missing_by_status']=rows
 daily=o.groupby(o.order_purchase_timestamp.dt.normalize()).agg(orders=('order_id','size'),sales=('sales','sum')).reindex(pd.date_range(o.order_purchase_timestamp.min().normalize(),o.order_purchase_timestamp.max().normalize()),fill_value=0);daily['rolling7']=daily.orders.rolling(7,min_periods=1).mean();x['daily']=rec(daily.reset_index(names='date'))
 x['time_heatmap']=rec(o.groupby([o.order_purchase_timestamp.dt.dayofweek.rename('weekday'),o.order_purchase_timestamp.dt.hour.rename('hour')]).size().rename('orders').reset_index())
 month=o.groupby(['year',o.order_purchase_timestamp.dt.month.rename('m')]).agg(orders=('order_id','size'),sales=('sales','sum')).reset_index();x['year_months']=rec(month)
 a=month[month.year.eq(CONFIG['research_design']['comparison_years'][0])&month.m.le(CONFIG['research_design']['comparison_month_end'])];b=month[month.year.eq(CONFIG['research_design']['comparison_years'][1])&month.m.le(CONFIG['research_design']['comparison_month_end'])];x['comparable_period']={'2017_orders':int(a.orders.sum()),'2018_orders':int(b.orders.sum()),'orders_change_pct':float((b.orders.sum()/a.orders.sum()-1)*100),'2017_sales':float(a.sales.sum()),'2018_sales':float(b.sales.sum()),'sales_change_pct':float((b.sales.sum()/a.sales.sum()-1)*100)}
 st=o.groupby('customer_state',as_index=False).agg(orders=('order_id','size'),sales=('sales','sum'),freight=('freight','sum'),delivery_n=('delivery_days','count'),delivery_median=('delivery_days','median'),delivery_p90=('delivery_days',lambda z:z.quantile(.9)),late_n=('late','sum'),late_valid=('late','count'),rating=('rating','mean'),rating_n=('rating','count'))
 st['late_pct']=st.late_n/st.late_valid*100;st['aov']=st.sales/st.orders;st['share']=st.sales/st.sales.sum()*100;st['region']=st.customer_state.map(REGION);x['states']=rec(st.sort_values('sales',ascending=False))
 items=t['order_items'].merge(o[['order_id','customer_state','region','month','rating','late','delivery_days']],on='order_id',validate='many_to_one')
 items=checked_item_merge(items,t['products'][['product_id','product_category_name']],'product_id')
 items=checked_item_merge(items,t['sellers'][['seller_id','seller_state']],'seller_id')
 items['category']=items.product_category_name.fillna('unknown');items['name']=items.category.map(NAMES).fillna(items.category);items['sector']=items.category.map(sector);items['seller_region']=items.seller_state.map(REGION)
 cat=items.groupby(['category','name','sector'],as_index=False).agg(sales=('price','sum'),freight=('freight_value','sum'),items=('order_id','size'),orders=('order_id','nunique'))
 rr=items.drop_duplicates(['order_id','category']).groupby('category',as_index=False).agg(rating=('rating','mean'),rated=('rating','count'),late_pct=('late',lambda s:s.mean()*100),delivery=('delivery_days','median'))
 cat=cat.merge(rr,on='category');cat['freight_pct']=cat.freight/cat.sales*100;cat=cat.sort_values('sales',ascending=False);cat['cum_pct']=cat.sales.cumsum()/cat.sales.sum()*100;x['categories']=rec(cat)
 secs=items.groupby('sector',as_index=False).agg(sales=('price','sum'),items=('order_id','size'));secs['share']=secs.sales/secs.sales.sum()*100;x['sectors']=rec(secs.sort_values('sales',ascending=False));x['sector_months']=rec(items.groupby(['month','sector'],as_index=False).price.sum())
 flow=items.groupby(['seller_region','region'],as_index=False).price.sum().rename(columns={'price':'sales'});x['flows']=rec(flow);x['cross_region_share']=float(flow.loc[flow.seller_region.ne(flow.region),'sales'].sum()/flow.sales.sum()*100)
 payments=t['payments'].groupby('payment_type',as_index=False).agg(records=('order_id','size'),orders=('order_id','nunique'),amount=('payment_value','sum'));payments['share']=payments.amount/payments.amount.sum()*100;x['payments']=rec(payments.sort_values('amount',ascending=False))
 p=t['payments'].groupby('order_id').payment_value.sum();base=o.set_index('order_id');common=base.index.intersection(p.index);diff=(p.loc[common]-base.loc[common,'sales']-base.loc[common,'freight']).round(2)
 x['payment_reconciliation']={'n':len(diff),'equal':int(diff.abs().le(.01).sum()),'positive':int(diff.gt(.01).sum()),'negative':int(diff.lt(-.01).sum()),'sum_diff':float(diff.sum()),'abs_max':float(diff.abs().max()),'abs_p99':float(diff.abs().quantile(.99))}
 bins=[-np.inf,-100,-1,-.01,.01,1,100,np.inf];labs=['低于100以上','低于1至100','低于0.01至1','误差不超过0.01','高于0.01至1','高于1至100','高于100以上'];bucket=pd.Series(np.select([diff.abs().le(.01),diff.lt(-100),diff.lt(-1),diff.lt(-.01),diff.gt(100),diff.gt(1),diff.gt(.01)],[labs[3],labs[0],labs[1],labs[2],labs[6],labs[5],labs[4]],default=labs[3]),index=diff.index);x['payment_diff_bins']=rec(bucket.value_counts().reindex(labs,fill_value=0).rename_axis('range').reset_index(name='orders'))
 valid=o[o.delivery_days.notna()];x['delivery_quantiles']={str(q):float(valid.delivery_days.quantile(q)) for q in [.05,.25,.5,.75,.9,.95,.99]}
 x['delivery_tails']={str(k):int(valid.delivery_days.gt(k).sum()) for k in [7,14,21,30,60,70]}
 # Stratification tests describe association in the same broad locations.
 rr=o[o.delay_days.notna()&o.rating.notna()];pairs=state_comparisons(o,CONFIG,wilson)
 x['state_risk']=pairs
 x['state_risk_summary']={'states':len(pairs),'same_direction':sum(z['gap_pp']>0 for z in pairs),'covered_orders':sum(z['on_n']+z['late_n'] for z in pairs),'joint_sample':len(rr)}
 # Missingness selection comparison; all rates remain descriptive.
 x['rating_selection']=rec(o.assign(has_rating=o.rating.notna()).groupby('order_status',as_index=False).agg(orders=('order_id','size'),rated=('has_rating','sum')))
 z=o[o.sales.gt(0)].copy();z['ratio']=z.freight/z.sales*100;x['freight_ratio']={'n':len(z),'median':float(z.ratio.median()),'p90':float(z.ratio.quantile(.9)),'over100':int(z.ratio.gt(100).sum()),'under10':int(z.sales.lt(10).sum())}
 fb=[0,20,50,100,200,500,1000,np.inf];z['band']=pd.cut(z.sales,fb,labels=['0至20','20至50','50至100','100至200','200至500','500至1000','1000以上'],right=False)
 x['freight_bands']=rec(z.groupby('band',observed=False).agg(n=('order_id','size'),median_ratio=('ratio','median'),p25=('ratio',lambda s:s.quantile(.25)),p75=('ratio',lambda s:s.quantile(.75))).reset_index())
 x['missing_category']={'products':int(t['products'].product_category_name.isna().sum()),'items':int(items.category.eq('unknown').sum()),'sales':float(items.loc[items.category.eq('unknown'),'price'].sum())}
 # Timelines for delivered only. Carrier fields are not used to change the core denominator.
 stages=[]
 for label,delta in [('下单至批准',o.order_approved_at-o.order_purchase_timestamp),('批准至交承运商',o.order_delivered_carrier_date-o.order_approved_at),('交承运商至客户',o.order_delivered_customer_date-o.order_delivered_carrier_date)]:
  days=delta.dt.total_seconds()/86400;eligible=o.order_status.eq('delivered')&days.notna();v=days[eligible&days.ge(0)];stages.append(dict(stage=label,n=len(v),negative=int((eligible&days.lt(0)).sum()),p25=float(v.quantile(.25)),median=float(v.median()),p75=float(v.quantile(.75)),p90=float(v.quantile(.9))))
 x['delivery_stages']=stages
 # Numbers describing the zero/long-tail records, not individual transactions.
 x['amount_profile']={'item_price_min':float(items.price.min()),'item_price_max':float(items.price.max()),'zero_freight_items':int(items.freight_value.eq(0).sum()),'zero_payment_rows':int(t['payments'].payment_value.eq(0).sum()),'zero_installments':int(t['payments'].payment_installments.eq(0).sum())}
 return x,items

def setup():
 for directory in [ROOT/'assets/report-fonts',Path.home()/'Library/Fonts']:
  for file in directory.glob('NotoSerifCJKsc-*.otf'):font_manager.fontManager.addfont(file)
 plt.rcParams.update({'font.family':['Times New Roman','Noto Serif CJK SC'],'font.size':12.5,'axes.titlesize':14,'axes.labelsize':12.5,'axes.labelcolor':INK,'text.color':INK,'xtick.color':MUTED,'ytick.color':MUTED,'axes.edgecolor':'#C9D5DC','axes.spines.top':False,'axes.spines.right':False,'axes.unicode_minus':False,'savefig.facecolor':'white','figure.facecolor':'white','axes.facecolor':'white','grid.color':'#DFE7ED','grid.linewidth':.6,'svg.fonttype':'none','mathtext.fontset':'custom','mathtext.rm':'Times New Roman','mathtext.it':'Times New Roman:italic','mathtext.bf':'Times New Roman:bold'})

def new(w=8.8,h=5.6):return plt.subplots(figsize=(w,h),layout='constrained')
def save(fig,name):
 # Keep labels readable on white even when the data marks use pale blue.
 for artist in fig.findobj(match=plt.Text):
  try:
   h,s,v=colors.rgb_to_hsv(colors.to_rgb(artist.get_color()))
   if s>.1 and .52<=h<=.65:artist.set_color(NAVY)
  except (ValueError,TypeError):pass
 FIG.mkdir(parents=True,exist_ok=True);fig.savefig(FIG/(name+'.png'),dpi=250,bbox_inches='tight');fig.savefig(FIG/(name+'.svg'),bbox_inches='tight');plt.close(fig)
def subtitle(ax,text):ax.set_title(text,loc='left',color=INK,pad=16,fontsize=12)
def subtle(ax,axis='x'):ax.set_axisbelow(True);ax.grid(axis=axis,alpha=.7)
def label(ax,x,y,txt,color=NAVY,align='left',size=11):ax.text(x,y,txt,color=color,ha=align,va='center',fontsize=size)

def plot_all(d,o,x,items):
 setup();calendar_year=CONFIG['research_design']['calendar_year'];cmap=colors.LinearSegmentedColormap.from_list('deepsea',['#F2F6F8','#A6C5D7',BLUE,NAVY]);warm=colors.LinearSegmentedColormap.from_list('missingness_blue',['#F2F6F8','#A6C5D7',BLUE,NAVY])
 # Calendar, not a flattened month-count bar.
 fig=plt.figure(figsize=(8.8,5.4),layout='constrained');gs=fig.add_gridspec(2,1,height_ratios=[1,.8]);ax=fig.add_subplot(gs[0]);daily=pd.DataFrame(x['daily']);daily['date']=pd.to_datetime(daily.date);first=pd.Timestamp(calendar_year,1,1);start=first-pd.Timedelta(days=first.dayofweek);weeks=((pd.Timestamp(calendar_year,12,31)-start).days//7)+1;g=np.full((7,weeks),np.nan);peak=daily[daily.date.dt.year.eq(calendar_year)].loc[lambda q:q.orders.eq(q.orders.max())].iloc[0]
 for _,r in daily[daily.date.dt.year.eq(calendar_year)].iterrows():g[r.date.dayofweek,(r.date-start).days//7]=r.orders
 im=ax.pcolormesh(np.arange(weeks+1)-.5,np.arange(8)-.5,g,cmap=cmap,edgecolors='white',linewidth=1,vmin=0,vmax=np.nanpercentile(g,98));ax.invert_yaxis();ax.set_yticks(range(7),['周一','周二','周三','周四','周五','周六','周日']);ax.set_xticks([(pd.Timestamp(calendar_year,m,1)-start).days//7 for m in range(1,13)],[str(m)+'月' for m in range(1,13)]);ax.tick_params(length=0);ax.spines[['left','bottom']].set_visible(False);subtitle(ax,f'{calendar_year}年每日订单分布  色阶在P98封顶，实际峰值单独标记');fig.colorbar(im,ax=ax,orientation='horizontal',fraction=.07,pad=.15,label='订单 / 笔',shrink=.6)
 ax2=fig.add_subplot(gs[1]);z=daily[daily.date.dt.to_period('M').eq(peak.date.to_period('M'))];ax2.bar(z.date.dt.day,z.orders,color=[ACCENT if day==peak.date.day else '#9DBBCC' for day in z.date.dt.day]);ax2.set_xlabel(f'{peak.date.year}年{peak.date.month}月 / 日');ax2.set_ylabel('订单 / 笔');ax2.annotate(f'{peak.date.month}月{peak.date.day}日  {peak.orders:,.0f}笔',xy=(peak.date.day,peak.orders),xytext=(max(1,peak.date.day-12),peak.orders*.91),arrowprops=dict(arrowstyle='-',color=ACCENT),color=ACCENT);subtle(ax2,'y');save(fig,'01_calendar')
 # Time matrix.
 fig,ax=new(h=4.4);h=pd.DataFrame(x['time_heatmap']).pivot(index='weekday',columns='hour',values='orders').reindex(index=range(7),columns=range(24),fill_value=0);im=ax.imshow(h,aspect='auto',cmap=cmap);ax.set_yticks(range(7),['周一','周二','周三','周四','周五','周六','周日']);ax.set_xticks(range(0,24,2),[str(v).zfill(2)+':00' for v in range(0,24,2)]);ax.set_xlabel('原始记录小时  未做时区转换');fig.colorbar(im,ax=ax,shrink=.8,label='订单 / 笔');save(fig,'02_week_hour')
 # Growth two panels, aligned periods.
 fig,axs=plt.subplots(1,2,figsize=(8.8,4.8),layout='constrained');mo=pd.DataFrame(x['year_months'])
 for ax,key,unit in [(axs[0],'orders','订单 / 笔'),(axs[1],'sales','商品金额 / 百万BRL')]:
  for year,col in [(2017,BLUE),(2018,ACCENT)]:
   z=mo[mo.year.eq(year)&mo.m.le(8)];v=z[key]/(1e6 if key=='sales' else 1);ax.plot(z.m,v,lw=2.5,marker='o',ms=4,color=col,label=str(year));ax.fill_between(z.m,v,color=col,alpha=.06)
  ax.set_xticks(range(1,9),[str(v)+'月' for v in range(1,9)]);ax.set_ylabel(unit);ax.legend(frameon=False,loc='upper left');subtle(ax,'y')
 save(fig,'03_comparable')
 # True geography plus ranked lollipops.
 fig,axs=plt.subplots(1,2,figsize=(8.8,6.2),layout='constrained',gridspec_kw={'width_ratios':[1.25,1]});st=pd.DataFrame(x['states']);lookup=st.set_index('customer_state');geo=json.loads((ROOT/'assets/brazil_states.geojson').read_text());norm=colors.PowerNorm(.45,vmin=0,vmax=st.sales.max())
 for ft in geo['features']:
  code=CODES[str(ft['properties']['codarea'])];polys=ft['geometry']['coordinates'];polys=[polys] if ft['geometry']['type']=='Polygon' else polys
  for poly in polys:axs[0].add_patch(patches.Polygon(poly[0],facecolor=cmap(norm(lookup.loc[code,'sales'])),edgecolor='white',lw=.8))
  largest=max(polys,key=lambda p:len(p[0]))[0];pts=np.array(largest);xx,yy=pts.mean(axis=0)
  if code in ['SP','RJ','MG','RS','BA','AM','PA','PR','SC','GO','MT']:
   axs[0].text(xx,yy,code,fontsize=11,ha='center',va='center',color='white' if norm(lookup.loc[code,'sales'])>.6 else INK)
 axs[0].set_xlim(-75,-33);axs[0].set_ylim(-35,6);axs[0].set_aspect('equal');axs[0].axis('off');subtitle(axs[0],'27州真实边界  颜色表示商品金额')
 z=st.head(10).iloc[::-1];axs[1].hlines(range(len(z)),0,z.share,color='#D4E0E8',lw=5);axs[1].scatter(z.share,range(len(z)),s=100,color=[ACCENT if s in ['SP','RJ','MG'] else BLUE for s in z.customer_state],zorder=3);axs[1].set_yticks(range(len(z)),z.customer_state);axs[1].set_xlim(0,47);axs[1].set_xlabel('占全样本商品金额 / %');subtle(axs[1]);
 for i,(_,r) in enumerate(z.iterrows()):label(axs[1],r.share+1,i,f'{r.share:.1f}%',ACCENT if r.customer_state in ['SP','RJ','MG'] else INK)
 save(fig,'04_geography')
 # Opportunity bubbles with readable manual annotation offsets.
 fig,ax=new(h=5.8);ax.axhline(d['summary']['late_rate']*100,color=ACCENT,lw=1,ls='--',alpha=.6);ax.axvline(d['summary']['sales']/d['summary']['orders'],color=NAVY,lw=1,ls='--',alpha=.5)
 for i,(reg,z) in enumerate(st[st.late_valid.ge(CONFIG['state_min_delivery_sample'])].groupby('region')):
  ax.scatter(z.aov,z.late_pct,marker=['o','s','D','^','v'][i],s=z.sales/st.sales.max()*1100+25,color=REGION_COLOR[reg],alpha=.8,edgecolor='white',lw=1.2,label=reg)
  for _,r in z.iterrows():
   if r.orders>=1000 or r.late_pct>=20:ax.annotate(r.customer_state,(r.aov,r.late_pct),xytext=(7,5),textcoords='offset points',fontsize=11.5,bbox=dict(facecolor='white',edgecolor='none',pad=.3,alpha=.9))
 ax.set_xlabel('每单商品金额 / BRL');ax.set_ylabel('州内可判断延迟订单的延迟比例 / %');ax.legend(frameon=False,ncols=5,loc='upper center',bbox_to_anchor=(.5,1.13),fontsize=11);subtle(ax,'y');save(fig,'05_opportunity')
 # Proper squarified treemap with area proportional to value.
 def treemap(vals,names,ax,box,color):
  if not vals:return
  if len(vals)==1:
   xx,yy,ww,hh=box;ax.add_patch(patches.Rectangle((xx,yy),ww,hh,facecolor=color,edgecolor='white',lw=2));
   if ww*hh>.018:
    ax.text(xx+ww/2,yy+hh/2,names[0],ha='center',va='center',fontsize=11.5 if ww>.2 else 10.5,color=('#000000' if color in [MID,ACCENT,LIGHT] else 'white'),linespacing=1.7)
   return
  total=sum(vals);best=min(range(1,len(vals)),key=lambda k:abs(sum(vals[:k])/total-.5));ratio=sum(vals[:best])/total;xx,yy,ww,hh=box
  if ww>=hh:b1=(xx,yy,ww*ratio,hh);b2=(xx+ww*ratio,yy,ww*(1-ratio),hh)
  else:b1=(xx,yy,ww,hh*ratio);b2=(xx,yy+hh*ratio,ww,hh*(1-ratio))
  treemap(vals[:best],names[:best],ax,b1,color);treemap(vals[best:],names[best:],ax,b2,color)
 fig,ax=new(h=6);cat=pd.DataFrame(x['categories']);secs=pd.DataFrame(x['sectors']);left=0
 for i,r in secs.iterrows():
  width=r.share/100;z=cat[cat.sector.eq(r.sector)].copy();large=z.head(4);vals=large.sales.tolist();names=[nm+'\n'+f'{v/d["summary"]["sales"]*100:.1f}%' for nm,v in zip(large.name,large.sales)]
  rest=float(z.iloc[4:].sales.sum())
  if rest:vals.append(rest);names.append('其余品类\n'+f'{rest/d["summary"]["sales"]*100:.1f}%')
  treemap(vals,names,ax,(left,0,width,1),COLORS[i]);ax.text(left+width/2,1.04,r.sector,ha='center',fontsize=11,color=NAVY);left+=width
 ax.set_xlim(0,1);ax.set_ylim(-.02,1.12);ax.axis('off');save(fig,'06_treemap')
 # Category bubbles; clean Pareto companion.
 fig,ax=new(h=5.7);cs=cat[cat.orders.ge(CONFIG['category_min_orders'])]
 for i,sec in enumerate(secs.sector):
  z=cs[cs.sector.eq(sec)];ax.scatter(z.freight_pct,z.rating,marker=['o','s','D','^','v'][i],s=z.sales/cat.sales.max()*950+25,c=COLORS[i],label=sec,alpha=.8,edgecolor='white',lw=1)
  for _,r in z.iterrows():
   if r.category in cat.head(7).category.values:
    offsets={'美妆健康':(-3,39),'创意好物':(-59,17),'运动休闲':(24,20),'手表礼品':(-10,-28),'床品卫浴':(12,-23),'电脑配件':(-54,-30),'家具装饰':(14,10)}
    ax.annotate(r['name'],(r.freight_pct,r.rating),xytext=offsets[r['name']],textcoords='offset points',fontsize=11,bbox=dict(boxstyle='round,pad=.15',fc='white',ec='none',alpha=.9),arrowprops=dict(arrowstyle='-',color=MUTED,lw=.7))
 ax.axhline(d['summary']['rating'],ls=':',color=MUTED);ax.axvline(d['scope']['freight_pct'],ls=':',color=MUTED);ax.set_xlabel('品类运费合计 / 商品金额合计 · %');ax.set_ylabel('涉及订单平均评分 / 分');ax.legend(frameon=False,ncols=3,loc='upper center',bbox_to_anchor=(.5,1.16),fontsize=11);subtle(ax,'y');save(fig,'07_category_risk')
 fig,ax=new(h=5.2);cross=int(cat.cum_pct.lt(CONFIG['research_design']['pareto_target_pct']).sum())+1;z=cat.head(max(22,cross));ax.bar(range(1,len(z)+1),z.sales/1e6,color=[ACCENT if i==cross-1 else BLUE for i in range(len(z))],alpha=.9);ax.set_xticks(range(1,len(z)+1),z.name,rotation=55,ha='right',fontsize=11);ax.set_ylabel('商品金额 / 百万BRL');ay=ax.twinx();ay.plot(range(1,len(z)+1),z.cum_pct,color=ACCENT,lw=2.5,marker='o',ms=3);ay.axhline(80,color=ACCENT,lw=.8,ls=':');ay.set_ylim(0,105);ay.set_ylabel('累计占全部品类商品金额 / %');ay.annotate(f"第{cross}类跨过{CONFIG['research_design']['pareto_target_pct']}%",xy=(cross,float(z.iloc[cross-1].cum_pct)),xytext=(max(1,cross-8),96),arrowprops=dict(arrowstyle='-',color=ACCENT),color=ACCENT);save(fig,'08_pareto')
 # Cross-region flow ribbons, exact scale and areas.
 fig,ax=new(h=6);flow=pd.DataFrame(x['flows']);regs=['东南部','南部','东北部','中西部','北部'];source=flow.groupby('seller_region').sales.sum().reindex(regs);target=flow.groupby('region').sales.sum().reindex(regs);total=flow.sales.sum();gap=.025;scale=(1-4*gap)/total
 def positions(s):
  out={};cursor=1
  for k,v in s.items():h=v*scale;out[k]=[cursor-h,cursor];cursor-=h+gap
  return out
 ps=positions(source);pt=positions(target);cs={r:ps[r][0] for r in regs};ct={r:pt[r][0] for r in regs}
 for i,src in enumerate(regs):
  for dst in regs:
   zz=flow[(flow.seller_region==src)&(flow.region==dst)];v=float(zz.sales.sum());h=v*scale
   if h<=0:continue
   y1=cs[src];y2=ct[dst];cs[src]+=h;ct[dst]+=h
   verts=[(.12,y1),(.42,y1),(.58,y2),(.88,y2),(.88,y2+h),(.58,y2+h),(.42,y1+h),(.12,y1+h),(.12,y1)]
   codes=[MPath.MOVETO,MPath.CURVE4,MPath.CURVE4,MPath.CURVE4,MPath.LINETO,MPath.CURVE4,MPath.CURVE4,MPath.CURVE4,MPath.CLOSEPOLY];ax.add_patch(patches.PathPatch(MPath(verts,codes),facecolor=REGION_COLOR[src],alpha=.3,edgecolor='none'))
 for i,r in enumerate(regs):
  for xx,dd in [(.1,ps),(.88,pt)]:ax.add_patch(patches.Rectangle((xx,dd[r][0]),.02,dd[r][1]-dd[r][0],color=REGION_COLOR[r]))
  ax.text(.075,sum(ps[r])/2,r,ha='right',va='center',fontsize=11.5);ax.text(.925,sum(pt[r])/2,r,ha='left',va='center',fontsize=11.5)
 ax.text(.1,1.08,'卖家大区',ha='center',fontsize=12);ax.text(.9,1.08,'客户大区',ha='center',fontsize=12);ax.set_xlim(-.07,1.08);ax.set_ylim(-.04,1.14);ax.axis('off');save(fig,'09_sankey')
 # Distribution ridges and quantile marks.
 fig,ax=new(h=6);tops=st.head(8).customer_state.tolist()[::-1];bins=np.linspace(0,70,141);centers=(bins[:-1]+bins[1:])/2
 for i,state in enumerate(tops):
  v=o.loc[o.customer_state.eq(state),'delivery_days'].dropna();h,_=np.histogram(v,bins);h=np.convolve(h,np.exp(-np.arange(-6,7)**2/10),mode='same');h=h/(h.max() or 1)*.8;col=ACCENT if state=='RJ' else BLUE
  ax.fill_between(centers,i,i+h,facecolor=col,alpha=.7);ax.plot(centers,i+h,color=col,lw=1);ax.plot(v.quantile([.25,.75]),[i+.06]*2,c=NAVY,lw=3);ax.plot(v.median(),i+.08,'o',c=NAVY,ms=4);ax.text(69,i+.22,f'n={len(v):,}    P50={v.median():.1f}天',ha='right',fontsize=11,color=MUTED)
 ax.set_yticks(range(8),tops);ax.set_xlim(0,70);ax.set_xlabel('下单至送达 / 自然日  图示0至70天');ax.spines['left'].set_visible(False);ax.tick_params(axis='y',length=0);save(fig,'10_ridges')
 # ECDF with full-sample quantiles; no truncation of statistics.
 fig,ax=new(h=4.7);v=np.sort(o.delivery_days.dropna());ax.plot(v,np.arange(1,len(v)+1)/len(v)*100,color=NAVY,lw=2.5);ax.set_xlim(0,70);ax.set_ylim(0,101)
 for q in [.5,.9,.95]:
  k=float(np.quantile(v,q));ax.plot([k,k,0],[0,q*100,q*100],ls=':',color=ACCENT,alpha=.8);ax.annotate(f'P{int(q*100)}  {k:.1f}天',(k,q*100),xytext=(6,-12 if q==.9 else 8),textcoords='offset points',color=ACCENT,fontsize=11.5)
 ax.set_xlabel('配送时长 / 自然日');ax.set_ylabel('累计送达订单比例 / %');subtle(ax,'y');save(fig,'11_ecdf')
 # Joint experience counts, forest chart and paired state comparison.
 fig,ax=new(h=5.2);risk=pd.DataFrame(d['risk']);ys=np.arange(len(risk));ax.hlines(ys,risk.lo,risk.hi,color=NAVY,lw=2);ax.scatter(risk.pct,ys,s=110,color=[NAVY]+[ACCENT]*4,zorder=3);ax.set_yticks(ys,risk.group);ax.invert_yaxis();ax.set_xlim(0,100);ax.set_xlabel(f"订单均分≤{CONFIG['low_score_max']}比例及Wilson 95%置信区间 / %");subtle(ax)
 for i,r in risk.iterrows():ax.text(r.pct+2,i-.15,f'{r.pct:.1f}%',color=NAVY if i==0 else ACCENT,fontsize=11);ax.text(99,i+.22,f'{r.low:,} / {r.n:,}',ha='right',fontsize=11.5,color=MUTED)
 ax.set_ylim(len(risk)-.45,-.5);save(fig,'12_risk')
 fig,ax=new(h=5.5);z=pd.DataFrame(x['state_risk']).head(10).iloc[::-1];ax.hlines(range(len(z)),z.on_pct,z.late_pct,color='#C8D8E3',lw=4);ax.scatter(z.on_pct,range(len(z)),c=NAVY,s=65,label='准时或提前');ax.scatter(z.late_pct,range(len(z)),c=ACCENT,s=65,label='延迟');ax.set_yticks(range(len(z)),z.state);ax.set_xlim(0,100);ax.set_xlabel('州内相应组别低评分比例 / %');ax.legend(frameon=False,ncols=2,loc='lower left',bbox_to_anchor=(0,1.01));subtle(ax);save(fig,'13_state_risk')
 fig,axs=plt.subplots(1,2,figsize=(8.8,4.8),layout='constrained',gridspec_kw={'width_ratios':[1,1.4]});z=pd.DataFrame(d['sensitivity']);zz=z[z.year.eq('all')];axs[0].plot(zz.cutoff,zz.ontime_pct,color=NAVY,lw=2.5,marker='o',label='准时或提前');axs[0].plot(zz.cutoff,zz.late_pct,color=ACCENT,lw=2.5,marker='o',label='延迟');axs[0].set_xticks([1,2,3],['≤1分','≤2分','≤3分']);axs[0].set_ylabel('组内低评分比例 / %');axs[0].legend(frameon=False);subtle(axs[0],'y')
 zz=z[z.cutoff.eq(CONFIG['low_score_max'])&z.year.ne('all')];ii=np.arange(2);axs[1].bar(ii-.17,zz.ontime_pct,width=.34,color=NAVY,label='准时或提前');axs[1].bar(ii+.17,zz.late_pct,width=.34,color=ACCENT,label='延迟');axs[1].set_xticks(ii,zz.year);axs[1].set_ylabel(f"低评分≤{CONFIG['low_score_max']}比例 / %");subtle(axs[1],'y');save(fig,'14_sensitivity')
 # Cohort exact cell labels and structural missingness.
 fig,ax=new(h=7);z=cohort_matrix(d['cohorts'],CONFIG);im=ax.imshow(z,aspect='auto',cmap=cmap,vmin=0,vmax=max(1,float(np.nanmax(z))));ax.set_xticks(range(len(z.columns)),['M+'+str(k) for k in z.columns]);ax.set_yticks(range(len(z)),z.index,fontsize=11);ax.set_xticks(np.arange(-.5,len(z.columns),1),minor=True);ax.set_yticks(np.arange(-.5,len(z),1),minor=True);ax.grid(which='minor',color='white',lw=2);ax.tick_params(which='minor',length=0)
 for i in range(len(z)):
  for j in range(len(z.columns)):
   v=z.iloc[i,j]
   if pd.notna(v):ax.text(j,i,f'{v:.2f}',ha='center',va='center',color='white' if v>.6 else INK,fontsize=10.5)
 ax.set_xlabel('首次观察到的已送达购买之后月份');fig.colorbar(im,ax=ax,shrink=.55,label='月度回购率 / %');save(fig,'15_cohort')
 # Price-freight density + amount-band interquartile profile.
 fig,axs=plt.subplots(1,2,figsize=(8.8,5),layout='constrained');z=o[o.sales.between(1,10000)].copy();z['ratio']=z.freight/z.sales*100;shown=z[z.ratio.between(0,100)];h=axs[0].hexbin(np.log10(shown.sales),shown.ratio,gridsize=32,bins='log',mincnt=1,cmap=cmap,lw=0);axs[0].set_xticks([0,1,2,3,4],['1','10','100','1,000','10,000']);axs[0].set_xlabel('订单商品金额 / BRL  对数刻度');axs[0].set_ylabel('运费 / 商品金额 · %');fig.colorbar(h,ax=axs[0],shrink=.7,label='格内订单数 对数色阶',format=FuncFormatter(lambda v,_:f'{v:,.0f}'));z=pd.DataFrame(x['freight_bands']);ix=np.arange(len(z));axs[1].fill_between(ix,z.p25,z.p75,color=ACCENT,alpha=.2,label='P25至P75');axs[1].plot(ix,z.median_ratio,c=ACCENT,lw=2.5,marker='o',label='中位数');axs[1].set_xticks(ix,z.band,rotation=45,ha='right',fontsize=11);axs[1].set_xlabel('订单商品金额分组 / BRL');axs[1].set_ylabel('订单运费占比 / %');axs[1].legend(frameon=False);subtle(axs[1],'y');save(fig,'16_freight')
 # Quality missingness matrix, metric branches, date segment diagnostics.
 fig,ax=new(h=5.5);z=pd.DataFrame(x['missing_by_status']);fields=['approved_missing','carrier_missing','delivery_missing','item_missing','rating_missing'];mat=z[fields].to_numpy()/z.n.to_numpy()[:,None]*100;im=ax.imshow(mat,cmap=warm,vmin=0,vmax=100,aspect='auto');ax.set_yticks(range(len(z)),[f'{s}  n={nn:,}' for s,nn in zip(z.status,z.n)],fontsize=11.5);ax.set_xticks(range(5),['批准时间','承运商时间','送达时间','商品明细','有效评分']);ax.xaxis.tick_top()
 for i in range(len(z)):
  for j in range(5):ax.text(j,i,('<0.1%' if 0<mat[i,j]<.1 else f'{mat[i,j]:.1f}%'),ha='center',va='center',fontsize=11.5,color='white' if mat[i,j]>55 else INK)
 fig.colorbar(im,ax=ax,shrink=.7,label='状态内缺失比例 / %');save(fig,'q01_status_missing')
 fig,ax=new(h=5.1);v=[len(o),int(o.order_status.eq('delivered').sum()),int(o.delivery_days.notna().sum()),int(o.rating.notna().sum())];names=['全部订单事实表','已送达订单','有效配送样本','有效评分样本'];ax.hlines(range(4),0,v,color=[NAVY,BLUE,BLUE,ACCENT],lw=16,alpha=.9);ax.scatter(v,range(4),s=160,color=[NAVY,BLUE,BLUE,ACCENT]);ax.set_yticks(range(4),names);ax.invert_yaxis();ax.set_xlim(0,115000);ax.set_xlabel('订单 / 笔  配送与评分为独立分支');
 for i,k in enumerate(v):label(ax,k+1500,i,f'{k:,}',NAVY if i<3 else ACCENT,size=12)
 ax.spines['left'].set_visible(False);ax.tick_params(axis='y',length=0);subtle(ax);save(fig,'q02_denominators')
 fig,ax=new(h=4.4);z=pd.DataFrame(x['delivery_stages']);ix=np.arange(len(z));ax.hlines(ix,z.p25,z.p75,color=BLUE,lw=9,alpha=.5);ax.scatter(z['median'],ix,s=100,c=ACCENT,zorder=3);ax.scatter(z.p90,ix,s=50,marker='|',c=NAVY);ax.set_yticks(ix,z.stage);ax.invert_yaxis();ax.set_xlabel('有效非负阶段耗时 / 自然日');subtle(ax)
 for i,r in z.iterrows():ax.text(24,i,f'中位数{r["median"]:.2f}天  n={r.n:,}',ha='right',fontsize=11.5,color=MUTED)
 ax.set_xlim(0,25);save(fig,'q03_stages')
 fig,axs=plt.subplots(1,2,figsize=(8.8,4.7),layout='constrained');z=pd.DataFrame(x['payment_diff_bins']);axs[0].barh(z['range'],z.orders,color=[BLUE]*3+[NAVY]+[ACCENT]*3);axs[0].set_xscale('symlog',linthresh=10);axs[0].xaxis.set_major_formatter(FuncFormatter(lambda v,_:f'{v:,.0f}'));axs[0].set_xlabel('订单 / 笔  对称对数刻度');axs[0].tick_params(axis='y',labelsize=9);vals=[d['summary']['sales']/1e6,d['extras']['freight_total']/1e6,d['extras']['payment_total']/1e6];axs[1].bar(['商品金额','运费','支付金额'],vals,color=[NAVY,MID,ACCENT],width=.55);axs[1].bar_label(axs[1].containers[0],fmt='%.2f',padding=5);axs[1].set_ylim(0,18);axs[1].set_ylabel('百万BRL');subtle(axs[1],'y');save(fig,'q04_money')
 fig,ax=new(h=4.8);pay=pd.DataFrame(x['payments']);labels=pay.payment_type.map({'credit_card':'信用卡','boleto':'Boleto付款单','voucher':'代金券','debit_card':'借记卡','not_defined':'未定义'});ax.barh(labels[::-1],pay.share.iloc[::-1],height=.55,color=[NAVY,BLUE,MID,ACCENT,LIGHT][::-1]);ax.set_xlim(0,100);ax.set_xlabel('占全部支付金额 / %');ax.bar_label(ax.containers[0],fmt='%.2f%%',padding=5,fontsize=11);subtle(ax);save(fig,'17_payment')
 # Geography and table grain plate for the quality report.
 fig,ax=new(h=4.8);z=pd.DataFrame(d['profiles']);g=z.groupby('table').agg(fields=('field','size'),missing_fields=('missing',lambda s:s.gt(0).sum())).reindex(['orders','customers','order_items','payments','reviews','products','sellers']);ax.barh(g.index,g.fields,color='#D4E1EA',height=.55,label='字段总数');ax.barh(g.index,g.missing_fields,color=ACCENT,height=.55,label='存在缺失的字段');ax.set_xlabel('字段 / 个');ax.legend(frameon=False,ncols=2);ax.invert_yaxis();subtle(ax);save(fig,'q05_field_profile')

def main(d=None,o=None):
 if d is None:d=json.loads((OUT/'analysis_snapshot.json').read_text())
 if o is None:_,o,_=load_data()
 x,items=compute(d,o);plot_all(d,o,x,items)
 (OUT/'extended_snapshot.json').write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False))
 for k in [key for key,val in x.items() if isinstance(val,list) and val and isinstance(val[0],dict)]:
  pd.DataFrame(x[k]).to_csv(OUT/'evidence'/('extended_'+k+'.csv'),index=False,encoding='utf-8-sig')
 print(json.dumps({k:x[k] for k in ['comparable_period','state_risk_summary','freight_ratio','payment_reconciliation','delivery_quantiles']},ensure_ascii=False,indent=2));print('Editorial figures',len(list(FIG.glob('*.png'))))
if __name__=='__main__':main()
