"""One command: optional raw SQL import -> atlas -> audit -> reports -> checks.

The raw database remains untouched. --from-raw imports SQL into a temporary
SQLite file and directs all analysis processes to that reconstructed source.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,sqlite3,subprocess,sys,tempfile,time
ROOT=Path(__file__).resolve().parents[1]
TABLES=['orders','customers','order_items','products','payments','reviews','sellers']

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def counts(p):
 with sqlite3.connect(f'file:{p}?mode=ro',uri=True) as c:return {t:c.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in TABLES}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--from-raw',action='store_true');ap.add_argument('--skip-render',action='store_true');ap.add_argument('--artifact-python',type=Path);args=ap.parse_args()
 os.chdir(ROOT);(ROOT/'reports').mkdir(exist_ok=True);started=time.time();log=[]
 runtime=Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3'
 artifact=args.artifact_python or (runtime if runtime.exists() else Path(sys.executable))
 before={str(p.relative_to(ROOT)):sha(p) for p in sorted((ROOT/'data/raw').glob('*.sql'))}
 if (ROOT/'data/olist.sqlite').exists():before['data/olist.sqlite']=sha(ROOT/'data/olist.sqlite')
 env=os.environ.copy()
 with tempfile.TemporaryDirectory(prefix='olist-reproduce-') as tmp:
  source=ROOT/'data/olist.sqlite'
  if args.from_raw:
   st=time.time();spec=importlib.util.spec_from_file_location('importer',ROOT/'sql/import_to_sqlite.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
   missing=[x for x in mod.SQL_FILES if not (mod.RAW_DIR/x).exists()]
   if missing:raise SystemExit('请先按 docs/数据说明.md 取得七个SQL文件；缺少：'+','.join(missing))
   source=Path(tmp)/'olist.sqlite'
   with sqlite3.connect(source) as c:
    for name in mod.SQL_FILES:
     with c:mod.import_file(c,mod.RAW_DIR/name)
   log.append(dict(step='原始SQL接入临时SQLite',input_files=len(mod.SQL_FILES),output_rows=counts(source),seconds=round(time.time()-st,3)))
  elif not source.exists():raise SystemExit('原始库不存在，请取得SQL后加 --from-raw 重跑')
  env['OLIST_SOURCE_DB']=str(source);rawcounts=counts(source)
  def run(step,python,script,extra=()):
   st=time.time();subprocess.run([str(python),str(ROOT/script),*extra],cwd=ROOT,env=env,check=True)
   row=dict(step=step,input_rows=rawcounts,seconds=round(time.time()-st,3))
   if script=='analysis/pipeline.py':
    with sqlite3.connect(ROOT/'data/analysis.sqlite') as c:row['output_rows']={'analysis_orders':c.execute('SELECT COUNT(*) FROM analysis_orders').fetchone()[0]}
   elif script=='analysis/course_analysis.py':
    d=json.loads((ROOT/'reports/analysis_snapshot.json').read_text());row['output_rows']={k:len(d[k]) for k in ['checks','profiles','ledger','risk','sensitivity','cohorts']}
   elif script=='scripts/build_course_reports.py':row['output_files']=3
   log.append(row)
  run('Python交互研究图谱与事实表',sys.executable,'analysis/pipeline.py')
  # The roadshow SQL reads the existing raw database; for an empty checkout point it at the temporary source.
  run('原版ECharts展示',sys.executable,'scripts/build_report.py')
  run('课程质量审计与汇总证据',sys.executable,'analysis/course_analysis.py')
  run('开源字体子集与字形准备',sys.executable,'scripts/prepare_report_fonts.py')
  run('正式Word报告及自建模板',artifact,'scripts/build_course_reports.py')
  if not args.skip_render:
   run('PDF导出和逐页渲染',artifact,'scripts/render_course_reports.py')
   run('PDF嵌入字体与目录核验',artifact,'scripts/verify_pdf_output.py')
  subprocess.run([sys.executable,str(ROOT/'scripts/verify_course_delivery.py')],cwd=ROOT,env=env,check=True)
 after={name:sha(ROOT/name) for name in before}
 assert before==after,'原始数据在处理过程中发生变化'
 record=dict(result='passed',raw_unchanged=True,source_sha256=before,from_raw=args.from_raw,rendered=not args.skip_render,steps=log,total_seconds=round(time.time()-started,3))
 (ROOT/'reports/pipeline_run.json').write_text(json.dumps(record,ensure_ascii=False,indent=2))
 print('Reproduction passed. Raw data unchanged. Log: reports/pipeline_run.json')
if __name__=='__main__':main()
