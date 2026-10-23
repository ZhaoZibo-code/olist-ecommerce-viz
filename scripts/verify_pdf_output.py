"""Check exported PDF typography, embedded fonts, TOC destinations and blank pages.

This complements manual inspection of rendered page PNGs; it cannot assess layout.
Run with the bundled document Python, which provides pypdf.
"""
from pathlib import Path
import json
from pypdf import PdfReader
from pypdf.generic import ContentStream

ROOT=Path(__file__).resolve().parents[1]
ALLOWED={'NotoSerifCJKsc-Regular','NotoSerifCJKsc-Bold',
         'TimesNewRomanPSMT','TimesNewRomanPS-BoldMT'}

def inspect(path):
 reader=PdfReader(path);families=set();embedded=True;blank=[]
 for i,page in enumerate(reader.pages,1):
  for ref in page.get('/Resources',{}).get('/Font',{}).values():
   font=ref.get_object();families.add(str(font['/BaseFont']).split('+')[-1].lstrip('/'))
   descriptor=font.get('/FontDescriptor')
   embedded=embedded and bool(descriptor and any(k in descriptor.get_object() for k in ['/FontFile','/FontFile2','/FontFile3']))
  operations=ContentStream(page.get_contents(),reader).operations
  if len((page.extract_text() or '').strip())<40 and not any(op==b'Do' for _,op in operations):blank.append(i)
 def outline(items):
  result={}
  for item in items:
   if isinstance(item,list):result.update(outline(item))
   else:result[item.title]=reader.get_destination_page_number(item)+1
  return result
 toc=json.loads((ROOT/'reports/toc_manifest.json').read_text())[path.stem+'.docx']
 destinations=outline(reader.outline)
 assert destinations==toc,('TOC mismatch',path.name)
 assert families<=ALLOWED and embedded,('Unexpected or unembedded font',families)
 assert not blank,('Blank pages',blank)
 return dict(pages=len(reader.pages),font_families=sorted(families),all_fonts_embedded=embedded,
             toc_destinations_match=True,blank_pages=blank)

EXPECTED=['Olist数据质量分析报告_中蓝版.pdf','Olist数据分析报告_中蓝版.pdf']

def main():
 result={'result':'running','reports':{}}
 try:
  for name in EXPECTED:
   path=ROOT/'reports'/name
   if not path.is_file() or path.stat().st_size==0:raise ValueError('正式PDF缺失或为空：'+name)
  result['reports']={name:inspect(ROOT/'reports'/name) for name in EXPECTED};result['result']='passed'
 except Exception as exc:
  result.update(result='failed',error=str(exc));raise
 finally:
  (ROOT/'reports').mkdir(exist_ok=True)
  (ROOT/'reports/pdf_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
  print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
