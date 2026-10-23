"""Subset the installed open Noto fonts to the actual report/script character set."""
from pathlib import Path
from zipfile import ZipFile
from fontTools import subset
ROOT=Path(__file__).resolve().parents[1]
def main():
 text=''
 for directory in ['scripts','analysis','docs','configs']:
  for f in (ROOT/directory).rglob('*'):
   if f.is_file() and f.suffix in ['.py','.md','.json'] and 'archive' not in f.parts:text+=f.read_text()
 for f in (ROOT/'reports').glob('*.docx'):
  if f.name.startswith('.'):continue
  with ZipFile(f) as z:
   for name in z.namelist():
    if name.endswith('.xml'):text+=z.read(name).decode()
 for f in (ROOT/'reports').glob('*snapshot.json'):text+=f.read_text()
 target=ROOT/'assets/report-fonts';target.mkdir(exist_ok=True)
 opts=subset.Options();opts.name_IDs=['*'];opts.name_legacy=True;opts.name_languages=['*'];opts.layout_features=['*']
 for weight in ['Regular','Bold']:
  source=Path.home()/'Library/Fonts'/('NotoSerifCJKsc-'+weight+'.otf');dest=target/source.name
  if not source.exists():
   if not dest.exists():raise SystemExit('需要安装开源字体 Noto Serif CJK SC')
   continue
  font=subset.load_font(str(source),opts);sub=subset.Subsetter(options=opts);sub.populate(text=text);sub.subset(font);subset.save_font(font,str(dest),opts)
 print('Report font subsets prepared')
if __name__=='__main__':main()
