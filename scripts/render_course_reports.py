"""Render DOCX with the packaged documents renderer and explicit CJK fonts."""
import argparse,importlib.util,shutil,json,subprocess,sys,zipfile
from xml.etree import ElementTree as ET
from pypdf import PdfReader
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def cache_page_count(path,pages):
 # Keep the editor's document-properties preview consistent with the render.
 with zipfile.ZipFile(path) as z:entries={n:z.read(n) for n in z.namelist()}
 ns='http://schemas.openxmlformats.org/officeDocument/2006/extended-properties'
 xml=ET.fromstring(entries['docProps/app.xml']);node=xml.find('{'+ns+'}Pages')
 if node is None:node=ET.SubElement(xml,'{'+ns+'}Pages')
 node.text=str(pages);entries['docProps/app.xml']=ET.tostring(xml,encoding='UTF-8',xml_declaration=True)
 with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
  for name,data in entries.items():z.writestr(name,data)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--renderer',type=Path);ap.add_argument('--only',choices=['quality','analysis','template']);args=ap.parse_args()
 candidates=sorted((Path.home()/'.codex/plugins/cache/openai-primary-runtime/documents').glob('*/skills/documents/render_docx.py'))
 source=args.renderer or (candidates[-1] if candidates else None)
 if not source:raise SystemExit('需要 documents 技能的 render_docx.py；请使用 --renderer 指定')
 spec=importlib.util.spec_from_file_location('docx_renderer',source);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 original=mod._build_lo_env
 fonts=ROOT/'assets/report-fonts'
 def env_with_fonts(profile):
  target=Path(profile)/'user/fonts';target.parent.mkdir(parents=True,exist_ok=True)
  if not target.exists():target.symlink_to(fonts,target_is_directory=True)
  env=original(profile)
  bundle=Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/native/libreoffice-headless/libreoffice/LibreOfficeDev.app/Contents/Resources/fontconfig/fonts.conf'
  if bundle.exists():
   cfg=Path(profile)/'fonts.conf';cfg.write_text(f'<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "fonts.dtd"><fontconfig><include>{bundle}</include><dir>{fonts}</dir><dir>/System/Library/Fonts/Supplemental</dir><cachedir>{profile}/fontcache</cachedir></fontconfig>');env['FONTCONFIG_FILE']=str(cfg)
  env['SAL_FONTPATH']=str(fonts)
  return env
 mod._build_lo_env=env_with_fonts
 files=[('quality','Olist数据质量分析报告_中蓝版'),('analysis','Olist数据分析报告_中蓝版'),('template','Olist电商报告自建写作模板_中蓝版')]
 cache=ROOT/'reports/.qa/toc_pages.json'
 public_toc=ROOT/'reports/toc_manifest.json'
 maps=json.loads(cache.read_text()) if cache.exists() else (json.loads(public_toc.read_text()) if public_toc.exists() else {})
 for attempt in range(3):
  updated=dict(maps);pagecounts={}
  for kind,name in files:
   if args.only and args.only!=kind:continue
   target=ROOT/'reports/.qa'/kind;target.mkdir(parents=True,exist_ok=True)
   for f in target.glob('page-*.png'):f.unlink()
   mod.rasterize(str(ROOT/'reports'/(name+'.docx')),str(target),150,verbose=False,emit_pdf=True)
   pdf=target/(name+'.pdf');reader=PdfReader(pdf);pagecounts[kind]=len(reader.pages)
   def destinations(outline):
    result={}
    for item in outline:
     if isinstance(item,list):result.update(destinations(item))
     else:result[item.title]=reader.get_destination_page_number(item)+1
    return result
   updated[name+'.docx']=destinations(reader.outline)
   if kind!='template':shutil.copy2(pdf,ROOT/'reports'/(name+'.pdf'))
   print(kind,'rendered',len(reader.pages),'pages',flush=True)
  if updated==maps:
   for kind,name in files:
    if kind in pagecounts:cache_page_count(ROOT/'reports'/(name+'.docx'),pagecounts[kind])
   manifest=ROOT/'reports/page_manifest.json'
   previous=json.loads(manifest.read_text()) if manifest.exists() else {}
   previous.update(pagecounts);manifest.write_text(json.dumps(previous,ensure_ascii=False,indent=2))
   public_toc.write_text(json.dumps(maps,ensure_ascii=False,indent=2));break
  maps=updated;cache.parent.mkdir(parents=True,exist_ok=True);cache.write_text(json.dumps(maps,ensure_ascii=False,indent=2))
  subprocess.run([sys.executable,str(ROOT/'scripts/build_course_reports.py')],check=True)
 else:raise RuntimeError('目录页码未收敛，请检查目录和正文分页')
if __name__=='__main__':main()
