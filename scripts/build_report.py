from pathlib import Path
import sqlite3, json, statistics, base64, os, io, hashlib, re, math
from datetime import datetime
from zoneinfo import ZoneInfo
from fontTools import subset
ROOT = Path(__file__).resolve().parents[1]
c = sqlite3.connect('file:'+os.environ.get('OLIST_SOURCE_DB',str(ROOT/'data/olist.sqlite'))+'?mode=ro',uri=True)
c.row_factory = sqlite3.Row
c.executescript('''
CREATE TEMP TABLE facts AS
SELECT o.*, c.customer_state,
       COALESCE(i.sales,0) sales, COALESCE(i.freight,0) freight,
       r.rating,
       CASE WHEN o.order_status='delivered' AND julianday(o.order_delivered_customer_date)>=julianday(o.order_purchase_timestamp)
         THEN julianday(o.order_delivered_customer_date)-julianday(o.order_purchase_timestamp) END delivery_days,
       CASE WHEN o.order_status='delivered' AND o.order_delivered_customer_date IS NOT NULL AND o.order_estimated_delivery_date IS NOT NULL
         THEN date(o.order_delivered_customer_date)>date(o.order_estimated_delivery_date) END late
FROM orders o
LEFT JOIN customers c USING(customer_id)
LEFT JOIN (SELECT order_id,SUM(price) sales,SUM(freight_value) freight FROM order_items GROUP BY order_id) i USING(order_id)
LEFT JOIN (SELECT order_id,AVG(review_score) rating FROM reviews WHERE review_score BETWEEN 1 AND 5 GROUP BY order_id) r USING(order_id);
CREATE INDEX temp.facts_id ON facts(order_id);
''')
def q(sql, args=()): return [dict(r) for r in c.execute(sql,args)]
result={}
for year in ['all','2016','2017','2018']:
    where = '1=1' if year=='all' else f"substr(order_purchase_timestamp,1,4)='{year}'"
    summary=q(f'''SELECT COUNT(*) orders,SUM(sales) sales,SUM(freight) freight,AVG(rating) rating,
       SUM(late) late_orders,COUNT(late) delivery_eligible, SUM(order_status='delivered') delivered,
       COUNT(rating) rated_orders,COUNT(delivery_days) delivery_sample,
       AVG(CASE WHEN late=1 THEN rating END) late_rating,AVG(CASE WHEN late=0 THEN rating END) ontime_rating,
       SUM(CASE WHEN late=1 AND rating IS NOT NULL THEN 1 ELSE 0 END) late_rated,
       SUM(CASE WHEN late=0 AND rating IS NOT NULL THEN 1 ELSE 0 END) ontime_rated
       FROM facts WHERE {where}''')[0]
    days=[r[0] for r in c.execute(f'SELECT delivery_days FROM facts WHERE {where} AND delivery_days IS NOT NULL')]
    summary['median_days']=statistics.median(days) if days else None
    summary['late_rate']=(summary['late_orders'] or 0)/summary['delivery_eligible'] if summary['delivery_eligible'] else None
    result[year]={
      'summary':summary,
      'trend':q(f"SELECT substr(order_purchase_timestamp,1,7) label,COUNT(*) orders,SUM(sales) sales FROM facts WHERE {where} GROUP BY label ORDER BY label"),
      'states':q(f"SELECT COALESCE(customer_state,'未知') label,COUNT(*) orders,SUM(sales) value FROM facts WHERE {where} GROUP BY label ORDER BY value DESC LIMIT 10"),
      'categories':q(f'''SELECT COALESCE(p.product_category_name,'unknown') label,SUM(i.price) value,COUNT(*) items
        FROM order_items i JOIN facts f USING(order_id) LEFT JOIN products p USING(product_id)
        WHERE {where} GROUP BY label ORDER BY value DESC LIMIT 10'''),
      'payments':q(f'''SELECT p.payment_type label,COUNT(*) records,SUM(p.payment_value) value FROM payments p
        JOIN facts f USING(order_id) WHERE {where} GROUP BY label ORDER BY value DESC'''),
      'ratings':q(f'''SELECT CAST(r.review_score AS TEXT) label,COUNT(*) value FROM reviews r JOIN facts f USING(order_id)
        WHERE {where} AND r.review_score BETWEEN 1 AND 5 GROUP BY r.review_score ORDER BY r.review_score'''),
      'delivery':q(f'''SELECT CASE WHEN delivery_days<3 THEN '0–3 天' WHEN delivery_days<7 THEN '3–7 天'
        WHEN delivery_days<14 THEN '7–14 天' WHEN delivery_days<21 THEN '14–21 天'
        WHEN delivery_days<30 THEN '21–30 天' ELSE '30 天以上' END label,COUNT(*) value,
        MIN(delivery_days) sort FROM facts WHERE {where} AND delivery_days IS NOT NULL GROUP BY label ORDER BY sort''')
    }

regions = {'东南部':['SP','RJ','MG','ES'],'南部':['PR','SC','RS'],'东北部':['BA','SE','AL','PE','PB','RN','CE','PI','MA'],'中西部':['DF','GO','MT','MS'],'北部':['AC','AP','AM','PA','RO','RR','TO']}
def regcase(field):
    return "CASE " + " ".join("WHEN " + field + " IN (" + ",".join("'"+s+"'" for s in states) + ") THEN '"+region+"'" for region,states in regions.items()) + " ELSE '未知' END"
def quant(vals, p):
    vals=sorted(vals); pos=(len(vals)-1)*p; k=int(pos)
    return vals[k]+(vals[min(k+1,len(vals)-1)]-vals[k])*(pos-k)
for year,d in result.items():
    where='1=1' if year=='all' else f"substr(order_purchase_timestamp,1,4)='{year}'"
    d['states']=q(f"SELECT customer_state label,COUNT(*) orders,SUM(sales) value,AVG(late)*100 late_pct,AVG(rating) rating FROM facts WHERE {where} GROUP BY customer_state ORDER BY value DESC")
    d['allCategories']=q(f"SELECT COALESCE(p.product_category_name,'unknown') label,SUM(i.price) value,COUNT(*) items FROM order_items i JOIN facts f USING(order_id) LEFT JOIN products p USING(product_id) WHERE {where} GROUP BY label ORDER BY value DESC")
    d['hours']=q(f"SELECT (CAST(strftime('%w',order_purchase_timestamp) AS INT)+6)%7 weekday,CAST(strftime('%H',order_purchase_timestamp) AS INT) hour,COUNT(*) value FROM facts WHERE {where} GROUP BY weekday,hour")
    d['flows']=q(f"SELECT {regcase('s.seller_state')} source,{regcase('f.customer_state')} target,SUM(i.price) value FROM order_items i JOIN facts f USING(order_id) JOIN sellers s USING(seller_id) WHERE {where} GROUP BY source,target")
    d['boxes']=[]
    for state in d['states'][:8]:
        vals=[r[0] for r in c.execute(f"SELECT delivery_days FROM facts WHERE {where} AND customer_state=? AND delivery_days IS NOT NULL",(state['label'],))]
        if vals:
            d['boxes'].append({'label':state['label'],'n':len(vals),'value':[round(quant(vals,p),2) for p in [.05,.25,.5,.75,.95]]})
    d['delayRating']=q(f"""SELECT CASE WHEN late=0 THEN '准时送达' WHEN julianday(date(order_delivered_customer_date))-julianday(date(order_estimated_delivery_date))<=3 THEN '延迟1–3天' WHEN julianday(date(order_delivered_customer_date))-julianday(date(order_estimated_delivery_date))<=7 THEN '延迟4–7天' WHEN julianday(date(order_delivered_customer_date))-julianday(date(order_estimated_delivery_date))<=14 THEN '延迟8–14天' ELSE '延迟15天+' END label,COUNT(*) n,AVG(rating) rating,AVG(rating<=2)*100 low_pct FROM facts WHERE {where} AND late IS NOT NULL AND rating IS NOT NULL GROUP BY label""")
    d['status']=q(f"SELECT order_status label,COUNT(*) value FROM facts WHERE {where} GROUP BY order_status ORDER BY value DESC")
    d['stateMonths']=q(f"SELECT substr(order_purchase_timestamp,1,7) month,customer_state state,COUNT(*) orders,SUM(sales) value,AVG(delivery_days) delivery,AVG(rating) rating,COUNT(delivery_days) delivered_n,COUNT(rating) rating_n FROM facts WHERE {where} GROUP BY month,state ORDER BY month,state")
    d['daily']=q(f"SELECT date(order_purchase_timestamp) day,COUNT(*) orders,SUM(sales) sales FROM facts WHERE {where} GROUP BY day ORDER BY day")
    d['categoryRegions']=q(f"SELECT COALESCE(p.product_category_name,'unknown') category,{regcase('f.customer_state')} region,SUM(i.price) value FROM order_items i JOIN facts f USING(order_id) LEFT JOIN products p USING(product_id) WHERE {where} GROUP BY category,region")
    month_rows={r['label']:r for r in d['trend']}
    start=d['trend'][0]['label']; end=d['trend'][-1]['label']
    y,m=map(int,start.split('-')); filled=[]
    while f'{y:04}-{m:02}'<=end:
        key=f'{y:04}-{m:02}'
        filled.append(month_rows.get(key,{'label':key,'orders':0,'sales':0}))
        m+=1
        if m==13: y+=1; m=1
    d['trend']=filled
    d['summary']['aov']=d['summary']['sales']/d['summary']['orders']
    d['summary']['cross_region_share']=sum(r['value'] for r in d['flows'] if r['source']!=r['target'])/sum(r['value'] for r in d['flows'])
    d['summary']['peak']=max(d['trend'],key=lambda r:r['orders'])
    d['summary']['top3state_share']=sum(r['value'] for r in d['states'][:3])/d['summary']['sales']
    d['summary']['category_count']=len(d['allCategories'])
import json
geo=json.loads((ROOT/'assets/brazil_states.geojson').read_text())
state_codes={'11':'RO','12':'AC','13':'AM','14':'RR','15':'PA','16':'AP','17':'TO','21':'MA','22':'PI','23':'CE','24':'RN','25':'PB','26':'PE','27':'AL','28':'SE','29':'BA','31':'MG','32':'ES','33':'RJ','35':'SP','41':'PR','42':'SC','43':'RS','50':'MS','51':'MT','52':'GO','53':'DF'}
for feat in geo['features']:
    feat['properties']['name']=state_codes[str(feat['properties']['codarea'])]
c.close()
snapshot=json.loads((ROOT/'reports/analysis_snapshot.json').read_text())
for key in ['orders','sales','rated_orders','delivery_sample','late_orders']:
    if not math.isclose(result['all']['summary'][key],snapshot['summary'][key],abs_tol=.001):
        raise ValueError(f'Web 与正式快照的 {key} 不一致，请先核验数据版本')
defense={key:snapshot[key] for key in ['quality','checks','ledger','extras','risk','sensitivity','repeat','cohorts','summary','scope']}
defense['team']=snapshot['config']['team']
defense['dataVersion']=snapshot['config']['report_date']
defense['sourceUrl']=snapshot['config']['source_url']
defense['builtAt']=datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(timespec='seconds')
video=(ROOT/'video/olist-vibe/final.mp4').read_bytes()
poster=(ROOT/'video/olist-vibe/qa/stills/003.000.jpg').read_bytes()
defense['videoSha256']=hashlib.sha256(video).hexdigest()
html=(ROOT/'scripts/roadshow_template.html').read_text()
font_text=html+json.dumps(defense,ensure_ascii=False)+json.dumps(result,ensure_ascii=False)
font_source=ROOT/'video/olist-vibe/assets/Film-Regular.otf'
opts=subset.Options();opts.layout_features=['*'];opts.name_IDs=['*'];opts.name_languages=['*']
font=subset.load_font(str(font_source),opts)
missing={ch for ch in font_text if ord(ch)>127 and not ch.isspace() and ord(ch) not in font.getBestCmap()}
if missing:raise ValueError('展示字体缺少字符：'+''.join(sorted(missing)))
sub=subset.Subsetter(options=opts);sub.populate(text=font_text);sub.subset(font)
font_buffer=io.BytesIO();font.save(font_buffer)
for token,content in [('__DATA__',json.dumps(result,ensure_ascii=False)),('__DEFENSE__',json.dumps(defense,ensure_ascii=False)),('__GEO__',json.dumps(geo,ensure_ascii=False)),('__ECHARTS__',(ROOT/'assets/echarts.min.js').read_text())]:
    html=html.replace(token,content.replace('</script','<\\/script'))
html=html.replace('__FONT__',base64.b64encode(font_buffer.getvalue()).decode())
html=html.replace('__VIDEO__',base64.b64encode(video).decode()).replace('__POSTER__',base64.b64encode(poster).decode())
unresolved=re.findall(r'__(?:DATA|DEFENSE|GEO|ECHARTS|FONT|VIDEO|POSTER)__',html)
if unresolved:raise ValueError('未替换的展示资源：'+str(unresolved))
report=ROOT/'deliverables/olist_visual_report.html'
report.write_text(html,encoding='utf-8')
(ROOT/'deliverables/analysis_data.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'reports/roadshow_build.json').write_text(json.dumps({'built_at':defense['builtAt'],'data_version':defense['dataVersion'],'video_sha256':defense['videoSha256'],'html_sha256':hashlib.sha256(report.read_bytes()).hexdigest(),'html_bytes':report.stat().st_size,'font_missing_characters':[],'main_chapters':11,'supplemental_chapters':2,'planned_seconds':535},ensure_ascii=False,indent=2))
print(report, report.stat().st_size)
print(json.dumps(result['all']['summary'],ensure_ascii=False,indent=2))
