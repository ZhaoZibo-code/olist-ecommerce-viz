from contextlib import closing
"""Reproducible pandas analysis, matplotlib exports and Plotly HTML/JSON."""
from pathlib import Path
import base64, json, sqlite3, os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots
from plotly.offline import get_plotlyjs

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'deliverables/analysis'
FONT="Times New Roman, Noto Serif CJK SC, serif"
REGIONS={'东南部':['SP','RJ','MG','ES'],'南部':['PR','SC','RS'],'东北部':['BA','SE','AL','PE','PB','RN','CE','PI','MA'],'中西部':['DF','GO','MT','MS'],'北部':['AC','AP','AM','PA','RO','RR','TO']}
REGION={s:r for r,states in REGIONS.items() for s in states}
CONFIG=json.loads((ROOT/'configs/analysis.json').read_text())
CATS={'beleza_saude':'美妆健康','relogios_presentes':'手表礼品','cama_mesa_banho':'床品卫浴','esporte_lazer':'运动休闲','informatica_acessorios':'电脑配件','moveis_decoracao':'家具装饰','cool_stuff':'创意好物','utilidades_domesticas':'家居用品','automotivo':'汽车用品','ferramentas_jardim':'园艺工具','brinquedos':'玩具','bebes':'婴幼儿用品','perfumaria':'香水','telefonia':'电话通信','papelaria':'文具','unknown':'未分类'}
PAY={'credit_card':'信用卡','boleto':'Boleto 付款单','voucher':'代金券','debit_card':'借记卡','not_defined':'未定义'}
GREEN='#317963'; BLUE='#4c7eaa'; ORANGE='#cc8a5d'

def records(df):
    return json.loads(df.to_json(orient='records',date_format='iso',force_ascii=False))

def load_data():
    source=Path(os.environ.get('OLIST_SOURCE_DB',str(ROOT/'data/olist.sqlite')))
    with closing(sqlite3.connect(f'file:{source}?mode=ro',uri=True)) as conn:
        tables={name:pd.read_sql_query(f'SELECT * FROM {name}',conn) for name in ['orders','customers','order_items','products','payments','reviews','sellers']}
    from report_contract import validate_sources,validate_config
    validate_config(CONFIG);validate_sources(tables)
    o=tables['orders'].merge(tables['customers'][['customer_id','customer_state']],on='customer_id',how='left',validate='many_to_one')
    item=tables['order_items'].groupby('order_id',as_index=False).agg(sales=('price','sum'),freight=('freight_value','sum'))
    review=tables['reviews'].loc[lambda d:d.review_score.between(CONFIG['valid_score_min'],CONFIG['valid_score_max'])].groupby('order_id',as_index=False).agg(rating=('review_score','mean'))
    o=o.merge(item,on='order_id',how='left',validate='one_to_one').merge(review,on='order_id',how='left',validate='one_to_one')
    o[['sales','freight']]=o[['sales','freight']].fillna(0)
    for col in [c for c in o if c.endswith('_date') or c.endswith('_timestamp') or c=='order_approved_at']:
        o[col]=pd.to_datetime(o[col],errors='coerce')
    o['year']=o.order_purchase_timestamp.dt.year.astype('Int64')
    o['month']=o.order_purchase_timestamp.dt.strftime('%Y-%m')
    o['customer_state']=o.customer_state.fillna('未知')
    o['region']=o.customer_state.map(REGION).fillna('未知')
    valid=(o.order_status=='delivered')&o.order_delivered_customer_date.notna()&(o.order_delivered_customer_date>=o.order_purchase_timestamp)
    o['delivery_days']=((o.order_delivered_customer_date-o.order_purchase_timestamp).dt.total_seconds()/86400).where(valid)
    delta=(o.order_delivered_customer_date.dt.normalize()-o.order_estimated_delivery_date.dt.normalize()).dt.days
    o['delay_days']=delta.where(valid & delta.notna())
    o['late']=o.delay_days.gt(0).astype(float).where(o.delay_days.notna())
    assert o.order_id.is_unique and len(o)==len(tables['orders'])
    assert abs(o.sales.sum()-tables['order_items'].price.sum())<.01
    quality={'table_rows':{k:len(v) for k,v in tables.items()},'unique_orders':len(o),'duplicate_order_ids':int(o.order_id.duplicated().sum()),'sales_reconciled':True,'missing_item_orders':int((~o.order_id.isin(item.order_id)).sum()),'orders_without_rating':int(o.rating.isna().sum()),'valid_deliveries':int(o.delivery_days.notna().sum()),'date_start':str(o.order_purchase_timestamp.min()),'date_end':str(o.order_purchase_timestamp.max())}
    return tables,o,quality

def aggregates(t,o,year):
    f=o if year=='all' else o[o.year==int(year)]
    keys=f[['order_id','month','region']]
    items=t['order_items'].merge(keys,on='order_id',validate='many_to_one').merge(t['products'][['product_id','product_category_name']],on='product_id',how='left',validate='many_to_one')
    categories=items.assign(category=lambda d:d.product_category_name.fillna('unknown')).groupby('category',as_index=False).agg(sales=('price','sum'),items=('order_id','size')).sort_values('sales',ascending=False)
    categories['name']=categories.category.map(CATS).fillna(categories.category)
    payments=t['payments'].merge(keys[['order_id']],on='order_id',validate='many_to_one').groupby('payment_type',as_index=False).agg(value=('payment_value','sum')).sort_values('value',ascending=False)
    ratings=t['reviews'].merge(keys[['order_id']],on='order_id',validate='many_to_one').loc[lambda d:d.review_score.between(1,5)].groupby('review_score',as_index=False).size()
    trend=f.groupby('month').agg(orders=('order_id','size'),sales=('sales','sum')).reindex(pd.period_range(f.month.min(),f.month.max(),freq='M').astype(str),fill_value=0).rename_axis('month').reset_index()
    states=f.groupby('customer_state',as_index=False).agg(orders=('order_id','size'),sales=('sales','sum'),rating=('rating','mean'),delivery=('delivery_days','median')).sort_values('sales',ascending=False)
    hours=f.groupby([f.order_purchase_timestamp.dt.dayofweek.rename('weekday'),f.order_purchase_timestamp.dt.hour.rename('hour')]).size().unstack(fill_value=0).reindex(index=range(7),columns=range(24),fill_value=0)
    region_items=items.merge(t['sellers'][['seller_id','seller_state']],on='seller_id',how='left',validate='many_to_one').assign(seller_region=lambda d:d.seller_state.map(REGION).fillna('未知'))
    flows=region_items.groupby(['seller_region','region'],as_index=False).price.sum()
    bins=['准时送达','延迟1–3天','延迟4–7天','延迟8–14天','延迟15天以上']
    df=f[f.delay_days.notna()&f.rating.notna()].copy()
    df['delay_group']=pd.cut(df.delay_days,[-np.inf,0,3,7,14,np.inf],labels=bins)
    df['low']=(df.rating<=CONFIG['low_score_max']).astype(float)
    delay=df.groupby('delay_group',observed=False).agg(n=('order_id','size'),rating=('rating','mean'),low_pct=('low','mean')).reset_index()
    summary={'orders':len(f),'sales':round(float(f.sales.sum()),2),'rating':float(f.rating.mean()),'median_days':float(f.delivery_days.median()),'late_rate':float(f.late.mean()),'late_orders':int(f.late.eq(1).sum()),'rated_orders':int(f.rating.notna().sum()),'delivery_sample':int(f.delivery_days.notna().sum())}
    return f,{'trend':trend,'states':states,'categories':categories,'payments':payments,'ratings':ratings,'hours':hours,'flows':flows,'delay':delay},summary

def style(fig,title):
    fig.update_layout(template='plotly_white',font=dict(family=FONT,color='#243d38',size=12),title=dict(text=title,font=dict(size=17)),paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',margin=dict(l=48,r=38,t=60,b=50),colorway=[GREEN,BLUE,ORANGE,'#8f7eae','#84a59a'],height=390,legend=dict(orientation='h',y=-.18),hoverlabel=dict(font_family=FONT))
    return json.loads(pio.to_json(fig))

def figures(f,a):
    out=[]
    def add(id,title,fig,note):out.append({'id':id,'title':title,'figure':style(fig,title),'note':note})
    tr=a['trend'];fig=make_subplots(specs=[[{'secondary_y':True}]])
    fig.add_trace(go.Bar(x=tr.month.tolist(),y=tr.orders.tolist(),name='订单量',marker_color='#8db3a5'),secondary_y=False)
    fig.add_trace(go.Scatter(x=tr.month.tolist(),y=tr.sales.tolist(),name='商品金额 / BRL',line=dict(color=GREEN,width=3)),secondary_y=True)
    fig.update_yaxes(title_text='订单量 / 笔',secondary_y=False);fig.update_yaxes(title_text='商品金额 / BRL',secondary_y=True,rangemode='tozero')
    add('trend','月度订单与商品金额',fig,'按下单月份统计；首尾年度不完整，不直接用于年度同比。')
    st=a['states'].head(10).iloc[::-1]
    add('states','核心消费州 · 商品金额 Top10',go.Figure(go.Bar(x=st.sales.tolist(),y=st.customer_state.tolist(),orientation='h',marker_color=GREEN,hovertemplate='%{y}<br>R$ %{x:,.2f}<extra></extra>')),'客户州份通过 customer_id 关联；金额不含运费，包含全部订单状态。')
    cat=a['categories'].head(14)
    add('categories','商品结构 · 矩形树图',go.Figure(go.Treemap(labels=cat.name.tolist()+['其他品类'],parents=['']*(len(cat)+1),values=cat.sales.tolist()+[float(a['categories'].iloc[14:].sales.sum())],textinfo='label+percent root',marker=dict(colorscale='Greens',line=dict(color='white',width=2)),root=dict(color='white'),hovertemplate='%{label}<br>R$ %{value:,.2f}<extra></extra>')),'前14品类单列，其余合并；面积表示商品金额。')
    pay=a['payments'].loc[lambda d:d.value>0];add('payments','支付方式 · 金额结构',go.Figure(go.Pie(labels=pay.payment_type.map(PAY).fillna(pay.payment_type).tolist(),values=pay.value.tolist(),hole=.65,text=[f'{v/pay.value.sum()*100:.1f}%' if v/pay.value.sum()>=.03 else '' for v in pay.value],textinfo='text',textposition='inside',hovertemplate='%{label}<br>R$ %{value:,.2f}<extra></extra>')),'按支付金额统计，可包含运费；不能与商品金额相加。')
    hours=a['hours'];add('hours','星期 × 小时 · 订单热力矩阵',go.Figure(go.Heatmap(z=hours.to_numpy().tolist(),x=list(range(24)),y=['周一','周二','周三','周四','周五','周六','周日'],colorscale=[[0,'#eef3ef'],[.5,'#84ad9c'],[1,GREEN]],hovertemplate='%{y} %{x}:00<br>%{z} 笔订单<extra></extra>')),'原始记录时间，不做时区转换；每格为当前年份相应时段的订单总数。')
    r=a['ratings'];add('ratings','评价记录 · 星级分布',go.Figure(go.Bar(x=[str(v)+'星' for v in r.review_score],y=r['size'].tolist(),marker_color=[ORANGE,ORANGE,'#98b4a9','#6b9c87',GREEN])),'本图按原始评价记录统计；核心平均评分先按订单平均，再对订单取均值。')
    boxes=go.Figure()
    for state in a['states'].head(8).customer_state:
        vals=f.loc[f.customer_state.eq(state),'delivery_days'].dropna()
        if len(vals):
            q=vals.quantile([.05,.25,.5,.75,.95]).tolist()
            boxes.add_trace(go.Box(name=state,q1=[q[1]],median=[q[2]],q3=[q[3]],lowerfence=[q[0]],upperfence=[q[4]],boxpoints=False,showlegend=False,marker_color=GREEN))
    boxes.update_yaxes(title='自然日');add('delivery','配送时长 · 州份分位比较',boxes,'仅使用有效已送达订单；箱体P25—P75，中位线P50，须P5/P95。')
    flow=a['flows'];regions=list(REGIONS)+(['未知'] if '未知' in set(flow.region)|set(flow.seller_region) else []);idx={r:i for i,r in enumerate(regions)}
    add('flow','交易流向 · 卖家大区 → 客户大区',go.Figure(go.Sankey(node=dict(label=['卖家 · '+r for r in regions]+['客户 · '+r for r in regions],pad=18,thickness=12),link=dict(source=[idx[r] for r in flow.seller_region],target=[len(regions)+idx[r] for r in flow.region],value=flow.price.tolist()))),'流带宽度为商品金额，包括同区交易；大区依据巴西五大区映射。')
    de=a['delay'];fig=make_subplots(specs=[[{'secondary_y':True}]])
    fig.add_trace(go.Bar(x=de.delay_group.astype(str).tolist(),y=(de.low_pct*100).tolist(),name='低评分占比 / %',marker_color='#d8b098'),secondary_y=True)
    fig.add_trace(go.Scatter(x=de.delay_group.astype(str).tolist(),y=de.rating.tolist(),name='订单均分',line=dict(color=GREEN,width=3),customdata=de.n.tolist(),hovertemplate='%{x}<br>均分 %{y:.2f}<br>有效订单 %{customdata}<extra></extra>'),secondary_y=False)
    fig.update_yaxes(range=[0,5],secondary_y=False);fig.update_yaxes(range=[0,100],secondary_y=True)
    add('delay','履约延迟与评分关联',fig,'低评分定义为订单均分≤2；不同分组样本量不同，描述性相关不代表因果。')
    return out

def static_exports(a,f):
    for bundled in (ROOT/'assets/report-fonts').glob('*.otf'):
        font_manager.fontManager.addfont(bundled)
    for name in ['Times New Roman.ttf','Times New Roman Bold.ttf']:
        file=Path('/System/Library/Fonts/Supplemental')/name
        if file.exists():font_manager.fontManager.addfont(file)
    noto=Path('/Users/ZZB/Library/Fonts/NotoSerifCJKsc-Regular.otf')
    if noto.exists():font_manager.fontManager.addfont(noto)
    plt.rcParams['font.family']=['Times New Roman','Noto Serif CJK SC']
    plt.rcParams['axes.unicode_minus']=False
    fig,axes=plt.subplots(2,3,figsize=(20,11),layout='constrained')
    tr=a['trend'];ax=axes[0,0];ax.plot(range(len(tr)),tr.orders,color=GREEN,lw=2);ax.set_xticks(range(0,len(tr),4),tr.month.iloc[::4],rotation=25);ax.set_title('月度订单量');ax.set_ylabel('笔')
    for ax,key,title in [(axes[0,1],'states','消费州金额 Top10'),(axes[0,2],'categories','商品类别金额 Top10')]:
        z=a[key].head(10).iloc[::-1];labels=z.customer_state if key=='states' else z.name
        ax.barh(labels,z.sales/1e6,color=GREEN);ax.set_title(title);ax.set_xlabel('百万 BRL')
    z=a['payments'].copy();z['pct']=z.value/z.value.sum()*100;z=z.iloc[::-1];ax=axes[1,0];ax.barh(z.payment_type.map(PAY),z.pct,color=GREEN);ax.set_xlim(0,100);ax.set_xlabel('支付金额占比 / %');ax.set_title('支付金额结构')
    for i,p in enumerate(z.pct):ax.text(p+1,i,f'{p:.2f}%',va='center',fontsize=10)
    z=a['ratings'];axes[1,1].bar(z.review_score,z['size'],color=GREEN);axes[1,1].set_title('评价星级分布');axes[1,1].set_xlabel('星');axes[1,1].set_ylabel('评价记录数')
    bins=[0,3,7,14,21,30,np.inf];counts=pd.cut(f.delivery_days,bins,right=False).value_counts(sort=False)
    axes[1,2].bar(['0–3','3–7','7–14','14–21','21–30','≥30'],counts,color=GREEN);axes[1,2].set_title('配送时长分布');axes[1,2].set_xlabel('自然日，区间左闭右开');axes[1,2].set_ylabel('有效配送订单数')
    for ax in axes.flat:
        ax.spines[['top','right']].set_visible(False)
    fig.suptitle('Olist 巴西电商 · pandas / matplotlib 分析总览',fontsize=23)
    fig.savefig(OUT/'matplotlib_overview.png',dpi=180,facecolor='white');fig.savefig(OUT/'matplotlib_overview.svg',facecolor='white');plt.close(fig)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    t,o,quality=load_data()
    with closing(sqlite3.connect(ROOT/'data/analysis.sqlite')) as c:
        o.to_sql('analysis_orders',c,if_exists='replace',index=False)
        c.execute('CREATE INDEX IF NOT EXISTS ix_analysis_year ON analysis_orders(year)')
        c.execute('CREATE INDEX IF NOT EXISTS ix_analysis_id ON analysis_orders(order_id)')
        c.commit()
    results={}
    for year in ['all','2016','2017','2018']:
        f,a,summary=aggregates(t,o,year)
        charts=figures(f,a)
        results[year]={'year':year,'summary':summary,'charts':charts,'tables':{k:records(v.reset_index()) if k=='hours' else records(v) for k,v in a.items()}}
        (OUT/f'dashboard_{year}.json').write_text(json.dumps(results[year],ensure_ascii=False,allow_nan=False),encoding='utf-8')
        if year=='all':static_exports(a,f)
        print(year,summary)
    (OUT/'quality.json').write_text(json.dumps(quality,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'frontend/vendor/plotly.min.js').write_text(get_plotlyjs(),encoding='utf-8')
    from advanced_report import build
    build(t,o,quality)
    print('Analysis complete:',OUT)
if __name__=='__main__':main()
