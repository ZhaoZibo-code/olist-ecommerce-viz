from contextlib import closing
from pathlib import Path
from typing import Literal
from functools import lru_cache
import json, sqlite3
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'deliverables/analysis'
Year=Literal['all','2016','2017','2018']
Status=Literal['all','delivered','shipped','canceled','unavailable','invoiced','processing','created','approved']
app=FastAPI(title='Olist 数据分析与展示 API',version='1.0.0')
@app.get('/api/health')
def health():
    ready=(ROOT/'data/analysis.sqlite').is_file() and (OUT/'dashboard_all.json').is_file()
    if not ready:raise HTTPException(503,'请先运行 analysis/pipeline.py 生成分析结果')
    return {'status':'ok','database':'SQLite','analysis':'pandas + matplotlib + Plotly'}
@lru_cache(maxsize=4)
def dashboard_data(year):
    path=OUT/f'dashboard_{year}.json'
    if not path.exists():raise HTTPException(503,'分析结果未生成，请先运行 analysis/pipeline.py')
    return json.loads(path.read_text())
@app.get('/api/dashboard')
def dashboard(year:Year='all'):return dashboard_data(year)
@app.get('/api/meta')
def meta():
    health()
    with closing(sqlite3.connect(f'file:{ROOT}/data/analysis.sqlite?mode=ro',uri=True)) as c:
        states=[r[0] for r in c.execute('SELECT DISTINCT customer_state FROM analysis_orders ORDER BY customer_state')]
    return {'years':['all','2016','2017','2018'],'states':states,'quality':json.loads((OUT/'quality.json').read_text()),'analysis_modified':(OUT/'dashboard_all.json').stat().st_mtime}
@app.get('/api/orders')
def orders(year:Year='all',state:str=Query('all',min_length=2,max_length=7),status:Status='all',q:str=Query('',max_length=32,pattern='^[0-9a-fA-F]*$'),page:int=Query(1,ge=1),size:int=Query(15,ge=1,le=100)):
    health(); clauses=[];args=[]
    if year!='all':clauses.append('year = ?');args.append(int(year))
    if state!='all':clauses.append('customer_state = ?');args.append(state)
    if status!='all':clauses.append('order_status = ?');args.append(status)
    if q:
        if any(x not in '0123456789abcdefABCDEF' for x in q):raise HTTPException(422,'订单ID只支持十六进制字符')
        clauses.append('order_id LIKE ?');args.append(q.lower()+'%')
    where=' WHERE '+' AND '.join(clauses) if clauses else ''
    with closing(sqlite3.connect(f'file:{ROOT}/data/analysis.sqlite?mode=ro',uri=True)) as c:
        c.row_factory=sqlite3.Row
        total=c.execute('SELECT COUNT(*) FROM analysis_orders'+where,args).fetchone()[0]
        rows=c.execute('SELECT order_id,customer_state,order_status,order_purchase_timestamp,sales,freight,rating,delivery_days FROM analysis_orders'+where+' ORDER BY order_purchase_timestamp DESC,order_id LIMIT ? OFFSET ?',args+[size,(page-1)*size]).fetchall()
    return {'total':total,'page':page,'size':size,'rows':[dict(r) for r in rows]}
@app.get('/')
def index():return FileResponse(ROOT/'deliverables/olist_visual_report.html')
@app.get('/workbench')
def workbench():return FileResponse(ROOT/'frontend/index.html')
app.mount('/static',StaticFiles(directory=ROOT/'frontend'),name='frontend')
app.mount('/reports',StaticFiles(directory=ROOT/'deliverables'),name='reports')
