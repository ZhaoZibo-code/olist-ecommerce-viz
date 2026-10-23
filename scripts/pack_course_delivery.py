"""Package only the mandatory submission items in task-book section nine."""
from pathlib import Path
import csv,json,zipfile
ROOT=Path(__file__).resolve().parents[1]
TARGET=ROOT/'提交/Olist课程项目提交材料.zip'
SOURCES=['analysis/report_contract.py','analysis/pipeline.py','analysis/advanced_report.py','analysis/course_analysis.py','analysis/editorial_analysis.py','sql/import_to_sqlite.py','configs/analysis.json','assets/brazil_states.geojson','scripts/reproduce_reports.py','scripts/build_course_reports.py','scripts/report_layout.py','scripts/embed_report_fonts.py','scripts/render_course_reports.py','scripts/verify_pdf_output.py','reports/toc_manifest.json','requirements.txt','requirements-documents.txt']
CODE_README=(ROOT/'docs/报告复现说明.md').read_text()

def main():
 TARGET.parent.mkdir(exist_ok=True)
 data=(ROOT/'docs/数据说明.md').read_text()
 data=data.replace('全部45字段的含义与使用权限见 `reports/evidence/field_dictionary.csv`；类型、缺失数量和基数见 `profiles.csv`。只提供字段摘要，不输出原始客户、订单、卖家或评价标识。','下方列出全部45字段的含义。类型、缺失和基数画像可由分析代码重算，输出在分析代码/reports/evidence/。')
 data += '\n## 字段说明\n\n| 表 | 字段 | 含义与用途 |\n| --- | --- | --- |\n'
 with (ROOT/'reports/evidence/field_dictionary.csv').open(encoding='utf-8-sig') as stream:
  for row in csv.DictReader(stream):data += '| '+row['table']+' | '+row['field']+' | '+row['meaning']+' |\n'
 entries={}
 for stem in ['Olist数据质量分析报告','Olist数据分析报告']:
  for ext in ['docx','pdf']:entries[stem+'.'+ext]=(ROOT/'reports'/(stem+'_中蓝版.'+ext)).read_bytes()
 entries['数据说明.md']=data.encode();entries['分工与贡献说明.md']=(ROOT/'docs/组员分工与复核安排.md').read_bytes()
 entries['分析代码/README.md']=CODE_README.encode()
 entries['分析代码/requirements.txt']='pandas==3.0.6\nnumpy==2.5.4\nmatplotlib==3.11.2\nplotly==7.1.0\n'.encode()
 files=[ROOT/f for f in SOURCES]+list((ROOT/'assets/report-fonts').glob('*'))
 for p in files:
  if p.is_file() and p.name!='requirements.txt':entries['分析代码/'+p.relative_to(ROOT).as_posix()]=p.read_bytes()
 with zipfile.ZipFile(TARGET,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for name,data in sorted(entries.items()):z.writestr('Olist课程项目提交材料/'+name,data)
 with zipfile.ZipFile(TARGET) as z:assert z.testzip() is None
 print(TARGET,'files',len(entries),'bytes',TARGET.stat().st_size)
if __name__=='__main__':main()
