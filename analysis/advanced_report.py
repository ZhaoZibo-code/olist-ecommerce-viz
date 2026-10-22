"""Research atlas: pandas statistics, Python Plotly figures and matplotlib plates."""
from pathlib import Path
import json,base64,math
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots
from plotly.offline import get_plotlyjs
from plotly.colors import sample_colorscale
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'deliverables/analysis'
INK='#193e37';GREEN='#387b68';GOLD='#be8a43';RED='#bb6651';BLUE='#5c83a3';PAPER='#faf9f5'
FONT='Times New Roman, Noto Serif CJK SC, serif'
CONFIG=json.loads((ROOT/'configs/analysis.json').read_text())
PALETTE=[GREEN,BLUE,GOLD,RED,'#8d80a3','#80a899']
REGIONS={'东南部':['SP','RJ','MG','ES'],'南部':['PR','SC','RS'],'东北部':['BA','SE','AL','PE','PB','RN','CE','PI','MA'],'中西部':['DF','GO','MT','MS'],'北部':['AC','AP','AM','PA','RO','RR','TO']}
REGION={s:k for k,v in REGIONS.items() for s in v}
CODES=dict(zip('11 12 13 14 15 16 17 21 22 23 24 25 26 27 28 29 31 32 33 35 41 42 43 50 51 52 53'.split(),'RO AC AM RR PA AP TO MA PI CE RN PB PE AL SE BA MG ES RJ SP PR SC RS MS MT GO DF'.split()))
NAMES={'beleza_saude':'美妆健康','relogios_presentes':'手表礼品','cama_mesa_banho':'床品卫浴','esporte_lazer':'运动休闲','informatica_acessorios':'电脑配件','moveis_decoracao':'家具装饰','cool_stuff':'创意好物','utilidades_domesticas':'家居用品','automotivo':'汽车用品','ferramentas_jardim':'园艺工具','brinquedos':'玩具','bebes':'婴幼儿用品','perfumaria':'香水','telefonia':'移动通信','papelaria':'文具','unknown':'未分类','pet_shop':'宠物用品','eletronicos':'电子产品','eletrodomesticos':'家用电器','eletrodomesticos_2':'家用电器Ⅱ','moveis_escritorio':'办公家具','moveis_sala':'客厅家具','moveis_quarto':'卧室家具','moveis_cozinha_area_de_servico_jantar_e_jardim':'厨餐园艺家具','moveis_colchao_e_estofado':'床垫软装','fashion_bolsas_e_acessorios':'箱包配饰','fashion_calcados':'鞋靴','fashion_roupa_masculina':'男装','fashion_roupa_feminina':'女装','fashion_roupa_infanto_juvenil':'童装','fashion_underwear_e_moda_praia':'内衣泳装','fashion_esporte':'运动服饰','malas_acessorios':'旅行箱包','consoles_games':'游戏主机','pcs':'台式电脑','pc_gamer':'游戏电脑','tablets_impressao_imagem':'平板影像','telefonia_fixa':'固定通信','audio':'音频设备','cine_foto':'摄影器材','instrumentos_musicais':'乐器','musica':'音乐','cds_dvds_musicais':'音乐光盘','dvds_blu_ray':'影视光盘','livros_interesse_geral':'大众图书','livros_importados':'进口图书','livros_tecnicos':'技术图书','artes':'艺术','artes_e_artesanato':'工艺美术','artigos_de_natal':'圣诞用品','artigos_de_festas':'派对用品','flores':'鲜花','alimentos':'食品','bebidas':'饮品','alimentos_bebidas':'食品饮品','fraldas_higiene':'纸尿裤卫生','casa_construcao':'家装建材','construcao_ferramentas_construcao':'建筑工具','construcao_ferramentas_seguranca':'安全工具','construcao_ferramentas_iluminacao':'照明工具','construcao_ferramentas_ferramentas':'通用工具','construcao_ferramentas_jardim':'园林工具','climatizacao':'空调暖通','sinalizacao_e_seguranca':'标识安防','agro_industria_e_comercio':'农业工贸','industria_comercio_e_negocios':'工业商贸','eletroportateis':'小家电','portateis_casa_forno_e_cafe':'烤箱咖啡机','portateis_cozinha_e_preparadores_de_alimentos':'厨房电器','casa_conforto':'居家舒适','casa_conforto_2':'居家舒适Ⅱ','la_cuisine':'厨艺用品','market_place':'综合商品','seguros_e_servicos':'保险服务'}
def sector(k):
    if k in ['beleza_saude','perfumaria','relogios_presentes','bebes','fraldas_higiene','pet_shop'] or k.startswith('fashion') or k=='malas_acessorios':return '生活与个护'
    if k.startswith(('moveis','casa','construcao','portateis','eletrodomesticos')) or k in ['cama_mesa_banho','utilidades_domesticas','ferramentas_jardim','eletroportateis','climatizacao','la_cuisine']:return '家居与建材'
    if k in ['informatica_acessorios','telefonia','telefonia_fixa','eletronicos','pcs','pc_gamer','tablets_impressao_imagem','audio','cine_foto','consoles_games']:return '数码与通信'
    if k.startswith(('livros','artes','artigos')) or k in ['esporte_lazer','brinquedos','instrumentos_musicais','musica','dvds_blu_ray','cds_dvds_musicais','papelaria']:return '文娱与运动'
    return '其他消费与工贸'
def safe(v):return None if pd.isna(v) else float(v)
def rec(d):return json.loads(d.to_json(orient='records',date_format='iso',force_ascii=False))
def fmt(n):return f'{n:,.0f}'
def wilson(k,n):
    if not n:return (0.,0.)
    p=k/n;z=1.96;den=1+z*z/n;mid=(p+z*z/(2*n))/den;half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return (100*(mid-half),100*(mid+half))
def styled(fig,height=420):
    fig.update_layout(template='plotly_white',font=dict(family=FONT,size=12,color=INK),paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',colorway=PALETTE,height=height,margin=dict(l=60,r=35,t=24,b=65),legend=dict(orientation='h',x=0,y=-.18,font=dict(size=11)),hoverlabel=dict(font_family=FONT,bgcolor='#fffef9'),modebar=dict(bgcolor='rgba(0,0,0,0)',color='#739084',activecolor=GREEN))
    fig.update_xaxes(gridcolor='#e8ece6',zerolinecolor='#d4dfd6',automargin=True)
    fig.update_yaxes(gridcolor='#e8ece6',zerolinecolor='#d4dfd6',automargin=True)
    return json.loads(pio.to_json(fig))
def empty(message='当前样本不足以形成有效比较'):
    f=go.Figure();f.add_annotation(text=message,x=.5,y=.5,xref='paper',yref='paper',showarrow=False);return styled(f)
def prepare(t,f):
    cols=['order_id','month','region','customer_state','order_status','rating','delivery_days','late','delay_days']
    items=t['order_items'].merge(f[cols],on='order_id',validate='many_to_one').merge(t['products'][['product_id','product_category_name']],on='product_id',how='left',validate='many_to_one').merge(t['sellers'][['seller_id','seller_state']],on='seller_id',how='left',validate='many_to_one')
    items['category']=items.product_category_name.fillna('unknown');items['name']=items.category.map(NAMES);items['sector']=items.category.map(sector);items['seller_region']=items.seller_state.map(REGION)
    states=f.groupby('customer_state',as_index=False).agg(orders=('order_id','size'),sales=('sales','sum'),rating=('rating','mean'),delivery=('delivery_days','median'),late=('late','mean'),valid=('late','count'),freight=('freight','sum')).sort_values('sales',ascending=False)
    states['aov']=states.sales/states.orders;states['region']=states.customer_state.map(REGION);states['late_pct']=states.late*100
    cat=items.groupby(['category','name','sector'],as_index=False).agg(sales=('price','sum'),items=('order_id','size'),orders=('order_id','nunique'),freight=('freight_value','sum'))
    unique=items.drop_duplicates(['order_id','category']).groupby('category',as_index=False).agg(rating=('rating','mean'),late=('late','mean'),rated=('rating','count'))
    cat=cat.merge(unique,on='category').sort_values('sales',ascending=False);cat['freight_pct']=cat.freight/cat.sales*100;cat['cum_pct']=cat.sales.cumsum()/cat.sales.sum()*100
    daily=f.groupby(f.order_purchase_timestamp.dt.normalize()).agg(orders=('order_id','size'),sales=('sales','sum')).reindex(pd.date_range(f.order_purchase_timestamp.min().normalize(),f.order_purchase_timestamp.max().normalize()),fill_value=0)
    daily['rolling']=daily.orders.rolling(7,min_periods=1).mean()
    return items,states,cat,daily

def temporal_figs(f,items,cat,daily):
    charts={}
    fig=make_subplots(specs=[[{'secondary_y':True}]])
    fig.add_trace(go.Bar(x=daily.index.strftime('%Y-%m-%d').tolist(),y=daily.orders.tolist(),marker_color='#d7e4da',name='每日订单',hovertemplate='%{x}<br>%{y:,} 笔<extra></extra>'),secondary_y=False)
    fig.add_trace(go.Scatter(x=daily.index.strftime('%Y-%m-%d').tolist(),y=daily['rolling'].round(2).tolist(),mode='lines',line=dict(color=GREEN,width=2.6),name='7日移动均值'),secondary_y=False)
    monthly=f.groupby('month').sales.sum()
    fig.add_trace(go.Scatter(x=[m+'-15' for m in monthly.index],y=monthly.tolist(),mode='lines+markers',line=dict(color=GOLD,width=2,dash='dot'),marker=dict(size=5),name='月度商品金额'),secondary_y=True)
    fig.update_yaxes(title_text='订单 / 笔',rangemode='tozero',secondary_y=False);fig.update_yaxes(title_text='月度商品金额 / BRL',rangemode='tozero',tickformat='.2s',secondary_y=True)
    peak=daily.orders.idxmax();fig.add_annotation(x=str(peak.date()),y=int(daily.orders.max()),text=f'峰值 {fmt(daily.orders.max())} 笔<br>{peak.date()}',showarrow=True,arrowhead=0,ax=35,ay=-35,bgcolor='#f1ede1',borderpad=6,font=dict(size=11))
    fig.update_xaxes(type='date',rangeslider=dict(visible=True,thickness=.09,bgcolor='#edf1e9'),rangeselector=dict(buttons=[dict(count=3,label='3个月',step='month',stepmode='backward'),dict(count=6,label='6个月',step='month',stepmode='backward'),dict(step='all',label='全部')],font=dict(size=10),bgcolor='#e9eee7'))
    charts['pulse']=styled(fig,460)
    years=sorted(f.year.unique());fig=make_subplots(rows=len(years),cols=1,subplot_titles=[str(y)+' 年' for y in years],vertical_spacing=.11 if len(years)>1 else 0)
    vmax=float(daily.orders.quantile(.98)) or 1
    for row,y in enumerate(years,1):
        start=pd.Timestamp(int(y),1,1);end=pd.Timestamp(int(y),12,31);monday=start-pd.Timedelta(days=start.dayofweek);z=[[None]*54 for _ in range(7)];custom=[[None]*54 for _ in range(7)]
        for date in pd.date_range(start,end):
            w=(date-monday).days//7;dow=date.dayofweek
            if date in daily.index:z[dow][w]=int(daily.loc[date,'orders']);custom[dow][w]=str(date.date())
        fig.add_trace(go.Heatmap(z=z,x=list(range(54)),y=['一','二','三','四','五','六','日'],customdata=custom,colorscale=[[0,'#eef1e7'],[.3,'#a6c4ad'],[.65,'#63967c'],[1,INK]],zmin=0,zmax=vmax,xgap=2,ygap=2,showscale=row==1,colorbar=dict(title='订单',len=.35,thickness=9,x=1.015),hoverongaps=False,hovertemplate='%{customdata}<br>%{z:,} 笔<extra></extra>'),row=row,col=1)
        ticks=[(pd.Timestamp(int(y),m,1)-monday).days//7 for m in range(1,13)]
        fig.update_xaxes(tickvals=ticks,ticktext=[str(m)+'月' for m in range(1,13)],showgrid=False,zeroline=False,row=row,col=1,range=[-.5,53.5])
        fig.update_yaxes(autorange='reversed',showgrid=False,zeroline=False,row=row,col=1)
    charts['calendar']=styled(fig,190*len(years)+70)
    wide=items.groupby(['month','sector']).price.sum().unstack(fill_value=0).sort_index();fig=go.Figure()
    for i,col in enumerate(wide):fig.add_trace(go.Scatter(x=wide.index.tolist(),y=wide[col].tolist(),stackgroup='one',groupnorm='percent',mode='lines',line=dict(width=.7,color=PALETTE[i]),name=col,customdata=wide[col].tolist(),hovertemplate='%{x}<br>'+col+'<br>商品金额 R$ %{customdata:,.0f}<extra></extra>'))
    fig.update_yaxes(range=[0,100],title='商品金额结构 / %',ticksuffix='%');charts['stream']=styled(fig)
    return charts

def market_figs(f,states,daily):
    charts={};geo=json.loads((ROOT/'assets/brazil_states.geojson').read_text());lookup=states.set_index('customer_state');fig=go.Figure();maxv=float(states.sales.max()) or 1
    for feature in geo['features']:
        code=CODES[str(feature['properties']['codarea'])];v=float(lookup.loc[code,'sales']) if code in lookup.index else 0
        color=sample_colorscale([[0,'#e5e9d8'],[.45,'#7eab8b'],[1,INK]],[math.sqrt(v/maxv)])[0]
        rings=feature['geometry']['coordinates'];rings=[rings] if feature['geometry']['type']=='Polygon' else rings
        xs=[];ys=[]
        for poly in rings:
            xs += [p[0] for p in poly[0]]+[None];ys += [p[1] for p in poly[0]]+[None]
        if code in lookup.index:
            r=lookup.loc[code];text=f'{code} · {REGION[code]}<br>商品金额 R$ {r.sales:,.2f}<br>订单 {r.orders:,}<br>配送中位数 {r.delivery:.1f} 天<br>延迟率 {r.late_pct:.1f}%'
        else:text=code+' · 当前年份无订单'
        fig.add_trace(go.Scatter(x=xs,y=ys,fill='toself',fillcolor=color,line=dict(width=.7,color=PAPER),mode='lines',name=code,text=text,hoveron='fills',hoverinfo='text',customdata=[code]*len(xs),showlegend=False))
    fig.update_xaxes(visible=False,range=[-75,-33],fixedrange=True);fig.update_yaxes(visible=False,range=[-35,6],scaleanchor='x',scaleratio=1,fixedrange=True)
    fig.update_layout(margin=dict(l=5,r=5,t=0,b=0));charts['map']=styled(fig,440);charts['map']['layout']['margin']={'l':5,'r':5,'t':0,'b':0}
    top=states.head(10).iloc[::-1];fig=go.Figure(go.Bar(x=top.sales.tolist(),y=top.customer_state.tolist(),orientation='h',marker=dict(color=[PALETTE[list(REGIONS).index(r)] for r in top.region]),customdata=top[['customer_state','orders','late_pct']].values.tolist(),text=[f'{s/max(states.sales.sum(),1)*100:.1f}%' for s in top.sales],textposition='outside',cliponaxis=False,hovertemplate='%{y}<br>商品金额 R$ %{x:,.0f}<br>订单 %{customdata[1]:,}<br>延迟率 %{customdata[2]:.1f}%<extra></extra>'))
    fig.update_xaxes(tickformat='.2s',title='BRL');charts['ranking']=styled(fig,440)
    valid=states[states.valid>=CONFIG['state_min_delivery_sample']].copy();fig=go.Figure()
    for i,(region,z) in enumerate(valid.groupby('region')):
        fig.add_trace(go.Scatter(x=z.aov.tolist(),y=z.late_pct.tolist(),mode='markers+text',text=z.customer_state.tolist(),textposition='top center',marker=dict(size=np.sqrt(z.sales/max(states.sales.max(),1))*62+8,color=PALETTE[list(REGIONS).index(region)],opacity=.8,line=dict(width=1,color='white')),name=region,customdata=z[['customer_state','orders','sales','rating']].values.tolist(),hovertemplate='%{customdata[0]}<br>每单商品金额 R$ %{x:.2f}<br>延迟率 %{y:.1f}%<br>订单 %{customdata[1]:,}<br>商品金额 R$ %{customdata[2]:,.0f}<extra></extra>'))
    if len(valid):
        fig.add_hline(y=float(f.late.mean()*100),line_dash='dot',line_color=RED,annotation_text='全样本延迟率',annotation_position='top left')
        fig.add_vline(x=float(f.sales.mean()),line_dash='dot',line_color='#8fa592')
    fig.update_xaxes(title='每单商品金额 / BRL',rangemode='tozero');fig.update_yaxes(title='延迟率 / %',rangemode='tozero')
    charts['opportunity']=styled(fig,450)
    # Stable state identity and fixed axes across monthly animation frames.
    mo=f.groupby(['month','customer_state'],as_index=False).agg(orders=('order_id','size'),sales=('sales','sum'),late=('late','mean'));mo['aov']=mo.sales/mo.orders
    statekeys=states.customer_state.tolist();months=sorted(mo.month.unique());xmax=max(300,float(mo.loc[mo.orders>=30,'aov'].max())*1.12) if len(mo[mo.orders>=30]) else 500
    def frame_trace(month):
        z=mo[mo.month.eq(month)].set_index('customer_state').reindex(statekeys);eligible=z.orders.fillna(0)>=30
        return go.Scatter(x=[float(v) if ok else None for v,ok in zip(z.aov,eligible)],y=[float(v)*100 if ok and pd.notna(v) else None for v,ok in zip(z.late,eligible)],mode='markers+text',text=statekeys,textposition='top center',marker=dict(size=(np.sqrt(z.sales.fillna(0)/max(mo.sales.max(),1))*55+8).tolist(),color=[PALETTE[list(REGIONS).index(REGION[s])] for s in statekeys],opacity=.8,line=dict(width=1,color='white')),customdata=[[s,0 if pd.isna(r.orders) else int(r.orders),0 if pd.isna(r.sales) else float(r.sales)] for s,(_,r) in zip(statekeys,z.iterrows())],hovertemplate='%{customdata[0]}<br>每单商品金额 R$ %{x:.2f}<br>延迟率 %{y:.1f}%<br>本月订单 %{customdata[1]:,}<extra></extra>',showlegend=False)
    eligible_months=f.groupby('month').size();months=[m for m in months if eligible_months[m]>=50] or months
    initial=months[-1];fig=go.Figure(data=[frame_trace(initial)],frames=[go.Frame(name=m,data=[frame_trace(m)]) for m in months])
    fig.update_xaxes(range=[0,xmax],title='每单商品金额 / BRL');ymax=max(20,float(mo.loc[mo.orders>=30,'late'].max())*115) if len(mo[mo.orders>=30]) else 100;fig.update_yaxes(range=[0,min(100,ymax)],title='延迟率 / %')
    fig.update_layout(updatemenus=[dict(type='buttons',direction='left',x=0,y=-.2,buttons=[dict(label='▶ 播放',method='animate',args=[None,dict(frame=dict(duration=800,redraw=False),transition=dict(duration=400),fromcurrent=False,mode='immediate')]),dict(label='Ⅱ 暂停',method='animate',args=[[None],dict(mode='immediate',frame=dict(duration=0,redraw=False))])])],sliders=[dict(active=len(months)-1,x=.27,len=.72,y=-.17,currentvalue=dict(prefix='月份 ',font=dict(size=13)),pad=dict(t=10),steps=[dict(label=m[2:],method='animate',args=[[m],dict(mode='immediate',frame=dict(duration=0,redraw=False),transition=dict(duration=0))]) for m in months])])
    charts['evolution']=styled(fig,460);charts['evolution']['layout']['margin']['b']=110
    if len(valid)>1:
        dims=[dict(label='订单量',values=valid.orders.tolist()),dict(label='每单金额 / BRL',values=valid.aov.round(1).tolist()),dict(label='配送中位数 / 天',values=valid.delivery.round(1).tolist()),dict(label='延迟率 / %',values=valid.late_pct.round(1).tolist()),dict(label='订单均分',values=valid.rating.round(2).tolist())]
        fig=go.Figure(go.Parcoords(dimensions=dims,line=dict(color=valid.late_pct.tolist(),colorscale=[[0,'#b9cdb8'],[.5,GREEN],[1,RED]],showscale=True,colorbar=dict(title='延迟率',thickness=10,len=.7)),labelfont=dict(family=FONT,size=12),tickfont=dict(family=FONT,size=10)))
        charts['parallel']=styled(fig,370);charts['parallel']['layout']['margin']={'l':60,'r':65,'t':50,'b':35}
    else:charts['parallel']=empty('有效配送样本≥30的州不足2个，不展示多维比较')
    profiles={}
    for code,z in f.groupby('customer_state'):
        g=z.groupby('month').agg(orders=('order_id','size'),sales=('sales','sum'),late=('late','mean')).reset_index();r=lookup.loc[code]
        p=go.Figure(go.Scatter(x=g.month.tolist(),y=g.sales.tolist(),fill='tozeroy',line=dict(color=GREEN,width=2),fillcolor='rgba(56,123,104,.10)',customdata=g.orders.tolist(),hovertemplate='%{x}<br>商品金额 R$ %{y:,.0f}<br>%{customdata:,} 笔<extra></extra>'));p.update_yaxes(tickformat='.2s');profiles[code]={'orders':int(r.orders),'sales':float(r.sales),'late_pct':safe(r.late_pct),'delivery':safe(r.delivery),'figure':styled(p,220)}
    return charts,profiles

def category_figs(f,items,cat):
    charts={};labels=['全部商品'];ids=['root'];parents=[''];values=[float(cat.sales.sum())];colors=[PAPER]
    sectors=cat.groupby('sector').sales.sum().sort_values(ascending=False)
    for i,(sec,value) in enumerate(sectors.items()):
        ids.append(sec);labels.append(sec);parents.append('root');values.append(float(value));colors.append(PALETTE[i])
        for _,r in cat[cat.sector.eq(sec)].iterrows():ids.append(r.category);labels.append(r['name']);parents.append(sec);values.append(float(r.sales));colors.append(PALETTE[i])
    common=dict(ids=ids,labels=labels,parents=parents,values=values,branchvalues='total',marker=dict(colors=colors,line=dict(color=PAPER,width=2)),textinfo='label+percent entry',hovertemplate='%{label}<br>商品金额 R$ %{value:,.0f}<br>占当前层级 %{percentParent:.1%}<extra></extra>')
    charts['sunburst']=styled(go.Figure(go.Sunburst(**common,maxdepth=3,insidetextorientation='radial')),500)
    charts['treemap']=styled(go.Figure(go.Treemap(**common,pathbar=dict(visible=True),tiling=dict(packing='squarify'))),500)
    cats=cat[cat.orders>=30];fig=go.Figure()
    for i,(sec,z) in enumerate(cats.groupby('sector')):
        fig.add_trace(go.Scatter(x=z.freight_pct.tolist(),y=z.rating.tolist(),mode='markers+text',text=[n if code in cat.head(4).category.tolist() else '' for code,n in zip(z.category,z.name)],textposition=[{'beleza_saude':'top right','relogios_presentes':'top left','cama_mesa_banho':'bottom right','esporte_lazer':'bottom left'}.get(code,'top center') for code in z.category],textfont=dict(size=10),marker=dict(size=np.sqrt(z.sales/max(cat.sales.max(),1))*50+8,color=PALETTE[list(sectors.index).index(sec)],opacity=.8,line=dict(width=1,color='white')),name=sec,customdata=z[['category','name','orders','sales']].values.tolist(),hovertemplate='%{customdata[1]}<br>运费/商品金额 %{x:.1f}%<br>订单均分 %{y:.2f}<br>涉及订单 %{customdata[2]:,}<br>商品金额 R$ %{customdata[3]:,.0f}<extra></extra>'))
    if len(cats):fig.add_hline(y=float(f.rating.mean()),line_dash='dot',line_color=GOLD);fig.add_vline(x=float(items.freight_value.sum()/max(items.price.sum(),1)*100),line_dash='dot',line_color=GOLD)
    fig.update_xaxes(title='运费 / 商品金额 · %',rangemode='tozero');fig.update_yaxes(title='按订单去重后的平均评分',range=[max(0,min(3,float(cats.rating.min())-.2)) if len(cats) else 0,5.15]);charts['category_risk']=styled(fig,460)
    top=cat.head(18);fig=make_subplots(specs=[[{'secondary_y':True}]])
    fig.add_trace(go.Bar(x=top.name.tolist(),y=top.sales.tolist(),name='商品金额',marker=dict(color=[GREEN if v<=80 else '#c0d1c2' for v in top.cum_pct]),customdata=top.category.tolist(),hovertemplate='%{x}<br>R$ %{y:,.0f}<extra></extra>'),secondary_y=False)
    fig.add_trace(go.Scatter(x=top.name.tolist(),y=top.cum_pct.tolist(),name='累计金额占比',mode='lines+markers',line=dict(color=GOLD,width=2),hovertemplate='%{x}<br>累计 %{y:.1f}%<extra></extra>'),secondary_y=True)
    fig.update_yaxes(title_text='商品金额 / BRL',tickformat='.2s',secondary_y=False);fig.update_yaxes(range=[0,100],autorange=False,tickmode='array',tickvals=[0,20,40,60,80,100],ticksuffix='%',title_text='累计占全部品类',secondary_y=True);fig.update_xaxes(tickangle=-35)
    charts['pareto']=styled(fig,440);charts['pareto']['layout']['margin']['b']=115
    profiles={}
    for category,z in items.groupby('category'):
        g=z.groupby('month').price.sum().reset_index();r=cat.loc[cat.category.eq(category)].iloc[0];fig=go.Figure(go.Bar(x=g.month.tolist(),y=g.price.tolist(),marker_color=GREEN,hovertemplate='%{x}<br>商品金额 R$ %{y:,.0f}<extra></extra>'));fig.update_yaxes(tickformat='.2s')
        profiles[category]={'name':r['name'],'orders':int(r.orders),'sales':float(r.sales),'rating':safe(r.rating),'freight_pct':safe(r.freight_pct),'figure':styled(fig,220)}
    return charts,profiles

def delivery_figs(f,items,states):
    charts={};eligible=items[items.delay_days.notna()].copy();eligible['outcome']=np.where(eligible.delay_days>0,'延迟送达','准时或提前')
    regions=list(REGIONS);names=['卖家 · '+r for r in regions]+['客户 · '+r for r in regions]+['准时或提前','延迟送达'];sources=[];targets=[];values=[];linkcolors=[]
    a=eligible.groupby(['seller_region','region']).price.sum();b=eligible.groupby(['region','outcome']).price.sum()
    for (src,dst),v in a.items():sources.append(regions.index(src));targets.append(5+regions.index(dst));values.append(float(v));linkcolors.append('rgba(56,123,104,.19)')
    for (src,dst),v in b.items():sources.append(5+regions.index(src));targets.append(10+(dst=='延迟送达'));values.append(float(v));linkcolors.append('rgba(187,102,81,.35)' if dst=='延迟送达' else 'rgba(56,123,104,.23)')
    fig=go.Figure(go.Sankey(arrangement='snap',node=dict(label=names,pad=23,thickness=12,color=PALETTE[:5]+PALETTE[:5]+[GREEN,RED],line=dict(width=0)),link=dict(source=sources,target=targets,value=values,color=linkcolors,hovertemplate='%{source.label} → %{target.label}<br>商品金额 R$ %{value:,.0f}<extra></extra>')))
    charts['sankey']=styled(fig,470)
    fig=go.Figure();topstates=states.head(8).customer_state.tolist();xgrid=np.linspace(0,70,141);counts=[]
    for i,state in enumerate(topstates[::-1]):
        vals=f.loc[f.customer_state.eq(state),'delivery_days'].dropna();hist,_=np.histogram(vals,bins=np.linspace(0,70,142));smooth=np.convolve(hist,np.exp(-np.arange(-6,7)**2/8),mode='same');smooth=smooth/(smooth.max() or 1)*.78
        fig.add_trace(go.Scatter(x=xgrid.tolist()+xgrid[::-1].tolist(),y=(i+smooth).tolist()+[i]*len(xgrid),fill='toself',fillcolor=PALETTE[(len(topstates)-1-i)%len(PALETTE)],line=dict(width=1,color='white'),opacity=.8,hoverinfo='skip',showlegend=False))
        if len(vals):
            q=vals.quantile([.25,.5,.75,.95]);fig.add_trace(go.Scatter(x=[q.loc[.25],q.loc[.75],None,q.loc[.5]],y=[i+.08,i+.08,None,i+.17],mode='lines+markers',line=dict(color=INK,width=3),marker=dict(color=INK,size=6),showlegend=False,text=[f'{state}<br>n={len(vals):,}<br>P25={q.loc[.25]:.1f} / P50={q.loc[.5]:.1f}<br>P75={q.loc[.75]:.1f} / P95={q.loc[.95]:.1f}']*4,hovertemplate='%{text}<extra></extra>'))
            counts.append({'state':state,'n':len(vals),'p50':float(q.loc[.5]),'p95':float(q.loc[.95]),'tail':int((vals>70).sum())})
    fig.update_xaxes(title='配送时长 / 自然日',range=[0,70]);fig.update_yaxes(tickvals=list(range(len(topstates))),ticktext=topstates[::-1],showgrid=False,zeroline=False)
    charts['ridge']=styled(fig,480)
    de=f[f.delay_days.notna() & f.rating.notna()].copy();labels=['准时/提前','延迟1–3天','延迟4–7天','延迟8–14天','延迟≥15天'];de['group']=pd.cut(de.delay_days,[-np.inf,*CONFIG['delay_bins'],np.inf],labels=labels);de['experience']=np.where(de.rating<=CONFIG['low_score_max'],'低评分 ≤2',np.where(de.rating>=4,'高评分 ≥4','中间评分'))
    data=de.groupby(['group','experience'],observed=False).size().unstack(fill_value=0).reindex(labels);totals=data.sum(axis=1);fig=go.Figure()
    for name,color in [('低评分 ≤2',RED),('中间评分',GOLD),('高评分 ≥4',GREEN)]:
        vals=data.get(name,pd.Series(0,index=data.index));pcts=vals/totals.replace(0,np.nan)*100
        fig.add_trace(go.Bar(x=pcts.fillna(0).tolist(),y=labels,orientation='h',name=name,marker_color=color,customdata=[[int(v),int(n)] for v,n in zip(vals,totals)],text=[f'{p:.0f}%' if p>7 else '' for p in pcts.fillna(0)],textposition='inside',hovertemplate='%{y}<br>'+name+' %{x:.1f}%<br>%{customdata[0]:,} / %{customdata[1]:,} 笔<extra></extra>'))
    fig.update_layout(barmode='stack');fig.update_xaxes(range=[0,100],title='有效订单的评分构成 / %');fig.update_yaxes(autorange='reversed');charts['experience']=styled(fig,390)
    risk=[]
    for label in labels:
        z=de[de.group.eq(label)];n=len(z);k=int(z.rating.le(CONFIG['low_score_max']).sum());lo,hi=wilson(k,n);risk.append({'group':label,'n':n,'low':k,'pct':k/n*100 if n else None,'lo':lo if n else None,'hi':hi if n else None})
    riskdf=pd.DataFrame(risk);fig=go.Figure(go.Scatter(x=riskdf.pct.tolist(),y=[r['group']+f"  · n={r['n']:,}" for r in risk],mode='markers',marker=dict(color=[GREEN]+[RED]*4,size=10),error_x=dict(type='data',symmetric=False,array=(riskdf.hi-riskdf.pct).tolist(),arrayminus=(riskdf.pct-riskdf.lo).tolist(),color='#a58c76',thickness=2,width=5),customdata=riskdf[['lo','hi','n']].values.tolist(),hovertemplate='%{y}<br>低评分 %{x:.1f}%<br>95%区间 [%{customdata[0]:.1f}%, %{customdata[1]:.1f}%]<extra></extra>'))
    fig.update_xaxes(title='低评分占比及 Wilson 95% 置信区间 / %',range=[0,100]);fig.update_yaxes(autorange='reversed');charts['risk']=styled(fig,360)
    order=f[f.sales.gt(0)].copy();order['freight_pct']=order.freight/order.sales*100
    # Exact binned counts; values outside the visible window remain in the disclosed denominator.
    xedges=np.linspace(0,4,39);yedges=np.linspace(0,100,36);shown=order[order.sales.between(1,10000)&order.freight_pct.between(0,100)];counts2d,_,_=np.histogram2d(np.log10(shown.sales),shown.freight_pct,bins=[xedges,yedges]);fig=go.Figure(go.Heatmap(x=((xedges[:-1]+xedges[1:])/2).tolist(),y=((yedges[:-1]+yedges[1:])/2).tolist(),z=np.where(counts2d.T>0,np.log10(counts2d.T+1),np.nan).tolist(),customdata=counts2d.T.astype(int).tolist(),colorscale=[[0,'#f0eddd'],[.45,'#82aa8e'],[1,INK]],colorbar=dict(title='log₁₀(n+1)',thickness=11),hoverongaps=False,hovertemplate='商品金额对数 %{x:.2f}<br>运费压力约 %{y:.1f}%<br>%{customdata:,} 笔<extra></extra>'))
    fig.update_xaxes(title='每单商品金额 / BRL · 对数刻度',tickvals=[0,1,2,3,4],ticktext=['1','10','100','1,000','10,000'],range=[0,4]);fig.update_yaxes(title='运费 / 商品金额 · %',range=[0,100]);charts['freight']=styled(fig,440)
    return charts,{'risk':risk,'delivery_quantiles':counts,'freight_total':len(order),'freight_shown':len(shown),'freight_excluded':len(order)-len(shown),'flow_orders':int(eligible.order_id.nunique()),'flow_sales':float(eligible.price.sum()),'tail_over_70':int((f.delivery_days>70).sum())}

def cohort_figure(t,f,year):
    # Cohorts refer to first observed delivered purchase in the full available sample.
    allorders=t['orders'].merge(t['customers'][['customer_id','customer_unique_id']],on='customer_id',validate='many_to_one');allorders=allorders[allorders.order_status.eq('delivered')].copy();allorders['date']=pd.to_datetime(allorders.order_purchase_timestamp);allorders['period']=allorders.date.dt.to_period('M');first=allorders.groupby('customer_unique_id').period.min();allorders['cohort']=allorders.customer_unique_id.map(first);allorders['offset']=[p.ordinal-c.ordinal for p,c in zip(allorders.period,allorders.cohort)]
    sizes=allorders[allorders.offset.eq(0)].groupby('cohort').customer_unique_id.nunique();cohorts=[p for p,n in sizes.items() if n>=CONFIG['cohort_min_customers'] and (year=='all' or p.year==int(year))];last=allorders.period.max();last_date=allorders.date.max();last=last-1 if last_date.day<last_date.days_in_month else last;cohorts=[c for c in cohorts if c<last];z=[];hover=[];text=[]
    for c in cohorts:
        row=[];h=[];tx=[];n=int(sizes[c])
        for m in range(1,CONFIG['cohort_horizon_months']+1):
            if c+m>last:row.append(None);h.append(None);tx.append('');continue
            k=int(allorders.loc[allorders.cohort.eq(c)&allorders.offset.eq(m),'customer_unique_id'].nunique());p=k/n*100;row.append(p);h.append([str(c),n,k,m]);tx.append(f'{p:.1f}%')
        z.append(row);hover.append(h);text.append(tx)
    if not cohorts:return empty('该年份没有首购客户数≥50的可比队列'),{'cohort_n':0,'last_month':str(last)}
    fig=go.Figure(go.Heatmap(z=z,x=['M+'+str(i) for i in range(1,CONFIG['cohort_horizon_months']+1)],y=[str(c)+f' · {sizes[c]:,}人' for c in cohorts],customdata=hover,text=text,texttemplate='%{text}',textfont=dict(size=11),colorscale=[[0,'#f0f1e6'],[.5,'#91b299'],[1,INK]],zmin=0,zmax=max(1,max(v for row in z for v in row if v is not None)),xgap=3,ygap=3,colorbar=dict(title='复购率 / %',thickness=11),hoverongaps=False,hovertemplate='首购 %{customdata[0]}<br>队列 %{customdata[1]:,} 人<br>M+%{customdata[3]} 回购 %{customdata[2]:,} 人<br>月度回购率 %{z:.2f}%<extra></extra>'))
    fig.update_yaxes(autorange='reversed',showgrid=False);fig.update_xaxes(side='top',showgrid=False);return styled(fig,max(300,24*len(cohorts)+90)),{'cohort_n':len(cohorts),'last_month':str(last)}

def make_dataset(t,o,year):
    f=o if year=='all' else o[o.year.eq(int(year))];items,states,cat,daily=prepare(t,f)
    charts=temporal_figs(f,items,cat,daily);m,profiles=market_figs(f,states,daily);charts.update(m);m,catprofiles=category_figs(f,items,cat);charts.update(m);m,evidence=delivery_figs(f,items,states);charts.update(m);charts['cohort'],cohortmeta=cohort_figure(t,f,year)
    valid=f[f.late.notna()];top3=states.head(3);eighty=int((cat.cum_pct<80).sum()+1);risk=evidence['risk'];ontime=risk[0];late=f[f.delay_days.gt(0)&f.rating.notna()];late_low=float(late.rating.le(CONFIG['low_score_max']).mean()*100) if len(late) else 0
    peak=daily.orders.idxmax();summary={'orders':len(f),'sales':float(f.sales.sum()),'aov':float(f.sales.mean()),'rating':float(f.rating.mean()),'delivery':float(f.delivery_days.median()),'late_pct':float(valid.late.mean()*100),'late_n':int(valid.late.sum()),'delivery_n':int(f.delivery_days.notna().sum()),'rated_n':int(f.rating.notna().sum()),'top3share':float(top3.sales.sum()/f.sales.sum()*100),'top3states':' / '.join(top3.customer_state),'categories':len(cat),'pareto80':eighty,'peak_date':str(peak.date()),'peak_orders':int(daily.orders.max()),'ontime_low':ontime['pct'],'late_low':late_low,'low_gap':late_low-(ontime['pct'] or 0),'freight_pct':float(items.freight_value.sum()/items.price.sum()*100),'repeat_cohort':cohortmeta}
    return {'year':year,'summary':summary,'charts':charts,'states':rec(states),'categories':rec(cat),'state_profiles':profiles,'category_profiles':catprofiles,'evidence':evidence,'daily':rec(daily.reset_index(names='date'))},(f,items,states,cat,daily)

def static_plate(data):
    for bundled in (ROOT/'assets/report-fonts').glob('*.otf'):
        font_manager.fontManager.addfont(bundled)
    f,items,states,cat,daily=data
    for p in [Path('/System/Library/Fonts/Supplemental/Times New Roman.ttf'),Path('/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf'),Path('/Users/ZZB/Library/Fonts/NotoSerifCJKsc-Regular.otf'),OUT/'noto-analysis-subset.otf']:
        if p.exists():font_manager.fontManager.addfont(p)
    plt.rcParams.update({'font.family':['Times New Roman','Noto Serif CJK SC'],'axes.unicode_minus':False,'font.size':11,'axes.titleweight':'normal','axes.spines.top':False,'axes.spines.right':False,'text.color':INK,'axes.labelcolor':INK,'xtick.color':'#687a70','ytick.color':'#687a70'})
    fig,axs=plt.subplots(2,3,figsize=(22,13),layout='constrained');fig.set_facecolor(PAPER)
    ax=axs[0,0];d=daily.loc['2017-01-01':'2017-12-31'];grid=np.full((7,53),np.nan);start=pd.Timestamp('2016-12-26')
    for dt,r in d.iterrows():grid[dt.dayofweek,(dt-start).days//7]=r.orders
    im=ax.pcolormesh(np.arange(54)-.5,np.arange(8)-.5,grid,cmap='YlGn',vmin=0,vmax=np.nanquantile(grid,.98),edgecolors=PAPER,linewidth=.5);ax.invert_yaxis();ax.set_yticks(range(7),['一','二','三','四','五','六','日']);ax.set_xticks([1,14,27,40],['1月','4月','7月','10月']);ax.set_title('01  2017年日历热力 · 每日订单',loc='left',pad=18);fig.colorbar(im,ax=ax,shrink=.55,label='订单 / 笔')
    ax=axs[0,1];z=cat.head(12);ax.bar(range(len(z)),z.sales/1e6,color=GREEN,width=.72);ax.set_xticks(range(len(z)),z.name,rotation=55,ha='right',fontsize=9);ax.set_ylabel('商品金额 / 百万BRL');a2=ax.twinx();a2.plot(range(len(z)),z.cum_pct,color=GOLD,marker='o',ms=3);a2.set_ylim(0,100);a2.set_ylabel('累计占全部品类 / %');ax.set_title('02  品类帕累托 · 规模与集中度',loc='left',pad=18)
    ax=axs[0,2]
    for region,z in states[states.valid>=CONFIG['state_min_delivery_sample']].groupby('region'):
        ax.scatter(z.aov,z.late_pct,s=z.sales/2000+35,alpha=.68,color=PALETTE[list(REGIONS).index(region)],label=region,edgecolor='white')
        for _,r in z.iterrows():ax.annotate(r.customer_state,(r.aov,r.late_pct),xytext=(3,5),textcoords='offset points',fontsize=9)
    ax.axhline(f.late.mean()*100,color=RED,lw=1,ls=':');ax.axvline(f.sales.mean(),color=GOLD,lw=1,ls=':');ax.set_xlabel('每单商品金额 / BRL');ax.set_ylabel('延迟率 / %');ax.legend(frameon=False,fontsize=8,ncols=3,loc='upper center',bbox_to_anchor=(.5,-.19));ax.set_title('03  州份机会矩阵 · 面积表示金额',loc='left',pad=18)
    ax=axs[1,0];z=f[f.sales.between(1,10000)].copy();z['ratio']=z.freight/z.sales*100;z=z[z.ratio.between(0,100)];hb=ax.hexbin(np.log10(z.sales),z.ratio,gridsize=36,bins='log',mincnt=1,cmap='YlGn',linewidths=0);ax.set_xticks([0,1,2,3,4],['1','10','100','1,000','10,000']);ax.set_xlabel('商品金额 / BRL · 对数刻度');ax.set_ylabel('运费 / 商品金额 · %');ax.set_title('04  运费压力 · 六边形密度',loc='left',pad=18);fig.colorbar(hb,ax=ax,shrink=.55,label='格内订单数 · 对数色阶')
    ax=axs[1,1];top=states.head(7).customer_state.tolist()[::-1];centers=np.linspace(0,70,140)
    for i,state in enumerate(top):
        v=f.loc[f.customer_state.eq(state),'delivery_days'].dropna();h,_=np.histogram(v,bins=np.linspace(0,70,141));sm=np.convolve(h,np.exp(-np.arange(-5,6)**2/6),mode='same');sm=sm/(sm.max() or 1)*.8;ax.fill_between(centers,i,i+sm,color=PALETTE[i%6],alpha=.75,lw=.5,edgecolor='white');ax.plot([v.quantile(.25),v.quantile(.75)],[i+.08]*2,color=INK,lw=3);ax.plot(v.median(),i+.1,'o',color=INK,ms=4)
    ax.set_yticks(range(len(top)),top);ax.set_xlabel('配送时长 / 自然日 · 仅展示0–70天');ax.set_xlim(0,70);ax.set_title('05  配送分布 · 山脊与四分位',loc='left',pad=18)
    ax=axs[1,2];de=f[f.delay_days.notna()&f.rating.notna()];bins=[-np.inf,*CONFIG['delay_bins'],np.inf];labels=['准时/提前','延迟1–3天','延迟4–7天','延迟8–14天','延迟≥15天']
    for i,label in enumerate(labels):
        z=de[(de.delay_days>bins[i])&(de.delay_days<=bins[i+1])];n=len(z);k=z.rating.le(CONFIG['low_score_max']).sum();p=k/n*100 if n else 0;lo,hi=wilson(k,n);ax.errorbar(p,i,xerr=[[max(0,p-lo)],[max(0,hi-p)]],fmt='o',color=GREEN if i==0 else RED,capsize=4);ax.text(99,i,f'n={n:,}',ha='right',va='center',fontsize=9,color='#7e8578')
    ax.set_yticks(range(5),labels);ax.invert_yaxis();ax.set_xlim(0,100);ax.set_xlabel('低评分≤2占比 / % · Wilson 95%区间');ax.set_title('06  延迟体验 · 效应量与不确定性',loc='left',pad=18)
    fig.suptitle('Olist 研究图谱  /  规模、结构与履约体验',fontsize=27,x=.025,ha='left')
    fig.supxlabel('99,441笔真实订单 · 商品金额非净收入 · 配送仅含有效已送达样本 · 描述性关联不代表因果',fontsize=11,color='#7d887c')
    fig.savefig(OUT/'matplotlib_advanced.png',dpi=180,facecolor=PAPER);fig.savefig(OUT/'matplotlib_advanced.svg',facecolor=PAPER);plt.close(fig)

def embed_font(text):
    original=Path('/Users/ZZB/Library/Fonts/NotoSerifCJKsc-Regular.otf');target=OUT/'noto-analysis-subset.otf'
    if original.exists():
        from fontTools import subset
        opts=subset.Options();opts.name_IDs=['*'];opts.name_legacy=True;opts.name_languages=['*'];opts.layout_features=['*'];font=subset.load_font(str(original),opts);sub=subset.Subsetter(options=opts);sub.populate(text=text);sub.subset(font);subset.save_font(font,str(target),opts)
    else:target=target if target.exists() else ROOT/'assets/noto-serif-cjk-subset.otf'
    return base64.b64encode(target.read_bytes()).decode()

def build(t,o,quality):
    OUT.mkdir(parents=True,exist_ok=True);datasets={}
    for year in ['all','2016','2017','2018']:
        datasets[year],data=make_dataset(t,o,year)
        if year=='all':static_plate(data)
        print('Research atlas:',year,len(datasets[year]['charts']),'figures',flush=True)
    package_report(datasets,quality)

def package_report(datasets,quality):
    payload=json.dumps(datasets,ensure_ascii=False,allow_nan=False).replace('</','<\\/')
    (OUT/'research_data.json').write_text(payload,encoding='utf-8')
    template=(ROOT/'analysis/report_template.html').read_text()
    font=embed_font(template+payload+Path(__file__).read_text())
    html=template.replace('__PLOTLY__',get_plotlyjs()).replace('__ATLAS__',payload).replace('__QUALITY__',json.dumps(quality,ensure_ascii=False)).replace('__STATIC__',base64.b64encode((OUT/'matplotlib_advanced.png').read_bytes()).decode()).replace('__SVG__',base64.b64encode((OUT/'matplotlib_advanced.svg').read_bytes()).decode()).replace('__FONT__',font)
    (OUT/'analysis_report.html').write_text(html,encoding='utf-8')
    print('Advanced standalone report:',OUT/'analysis_report.html',flush=True)
if __name__=='__main__':
    import sys
    if '--package-only' in sys.argv:
        package_report(json.loads((OUT/'research_data.json').read_text()),json.loads((OUT/'quality.json').read_text()))
    else:
        from pipeline import load_data
        t,o,q=load_data();build(t,o,q)
