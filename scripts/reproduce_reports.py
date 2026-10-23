"""Recompute formal-report evidence from seven SQL files; optional DOCX/PDF export."""
from pathlib import Path
import argparse,hashlib,importlib.util,importlib.metadata,json,os,platform,sqlite3,subprocess,sys,tempfile,time,traceback
ROOT=Path(__file__).resolve().parents[1]

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--documents',action='store_true',help='rebuild editable Word documents')
 ap.add_argument('--artifact-python',type=Path,help='Python with python-docx/pypdf/lxml')
 ap.add_argument('--render',action='store_true',help='export PDFs; needs the optional documents renderer')
 ap.add_argument('--renderer',type=Path,help='explicit render_docx.py path for --render')
 args=ap.parse_args();os.chdir(ROOT);report=ROOT/'reports';report.mkdir(exist_ok=True);started=time.time()
 sys.path.insert(0,str(ROOT/'analysis'))
 from report_contract import verify_aggregates
 record={'result':'running','started_at':time.strftime('%Y-%m-%dT%H:%M:%S%z'),'command':sys.argv,'environment':{'python':sys.version,'platform':platform.platform(),'packages':{k:importlib.metadata.version(k) for k in ['pandas','numpy','matplotlib','plotly']}},'steps':[]}
 def persist():
  record['seconds']=round(time.time()-started,3);(report/'reproduction.json').write_text(json.dumps(record,ensure_ascii=False,indent=2))
 def run(name,command,env,input_rows=None):
  row={'step':name,'status':'running','input_rows':input_rows};record['steps'].append(row);persist();t=time.time()
  try:
   p=subprocess.run(command,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
   with (report/'reproduction.log').open('a') as log:log.write('\n'+name+'\n'+p.stdout)
   print(p.stdout,end='',flush=True)
   if p.returncode:raise RuntimeError(f'{name} failed; exit code={p.returncode}; see reports/reproduction.log')
   row.update(status='passed',seconds=round(time.time()-t,3))
  except Exception as exc:row.update(status='failed',error=str(exc));raise
  finally:persist()
 before={};raw=None
 try:
  persist();(report/'reproduction.log').write_text('Formal report reproduction\n')
  spec=importlib.util.spec_from_file_location('raw_importer',ROOT/'sql/import_to_sqlite.py');importer=importlib.util.module_from_spec(spec);spec.loader.exec_module(importer)
  raw=importer.RAW_DIR;missing=[f for f in importer.SQL_FILES if not (raw/f).exists()]
  if missing:raise ValueError('先按数据说明取得七个SQL并放到 data/raw/；缺少：'+','.join(missing))
  sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
  before={f:sha(raw/f) for f in importer.SQL_FILES};record['source_sha256']=before
  with tempfile.TemporaryDirectory(prefix='olist-reports-') as tmp:
   source=Path(tmp)/'olist.sqlite';t=time.time()
   with sqlite3.connect(source) as conn:
    for name in importer.SQL_FILES:
     with conn:importer.import_file(conn,raw/name)
    counts={name:conn.execute('SELECT COUNT(*) FROM '+name).fetchone()[0] for name in ['orders','customers','order_items','products','payments','reviews','sellers']}
   record['steps'].append({'step':'SQL接入临时SQLite','status':'passed','input_files':len(before),'output_rows':counts,'seconds':round(time.time()-t,3)});persist()
   env=os.environ.copy();env['OLIST_SOURCE_DB']=str(source)
   run('质量审计 业务指标与正式图表',[sys.executable,str(ROOT/'analysis/course_analysis.py')],env,counts)
   summary=verify_aggregates(ROOT);record['steps'][-1]['output_rows']=summary;persist()
   if args.documents or args.render:
    dp=str(args.artifact_python or sys.executable)
    run('Word报告',[dp,str(ROOT/'scripts/build_course_reports.py')],env,summary)
    if args.render:
     command=[dp,str(ROOT/'scripts/render_course_reports.py')]
     if args.renderer:command += ['--renderer',str(args.renderer)]
     run('PDF导出及页面渲染',command,env)
     run('PDF文件 字体与目录验收',[dp,str(ROOT/'scripts/verify_pdf_output.py')],env)
  after={f:sha(raw/f) for f in before};record['raw_unchanged']=before==after
  if not record['raw_unchanged']:raise ValueError('原始SQL发生变化')
  record['result']='passed';record['scope']='数字和22幅图已重算；DOCX/PDF是否重建以命令参数和各步骤状态为准'
 except Exception as exc:
  record.update(result='failed',error=str(exc))
  if before:record['raw_unchanged']=all((raw/f).is_file() and hashlib.sha256((raw/f).read_bytes()).hexdigest()==h for f,h in before.items())
  raise
 finally:persist()
 print('完成。运行环境、步骤、对账与原始SQL哈希见 reports/reproduction.json。')
if __name__=='__main__':main()
