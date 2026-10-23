"""Regression checks for the requested monochrome theme and editor compatibility."""
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET
import unittest,colorsys,re
ROOT=Path(__file__).resolve().parents[1]
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
NS={'w':W,'r':R,'p':'http://schemas.openxmlformats.org/package/2006/relationships'}

class ReportConsistencyTests(unittest.TestCase):
 def files(self):
  files=[p for p in (ROOT/'reports').glob('Olist*_中蓝版.docx') if '模板' not in p.name]
  self.assertEqual(len(files),2)
  return files
 def test_report_fonts_are_embedded_and_roundtrip(self):
  for p in self.files():
   with ZipFile(p) as z:
    fonts=ET.fromstring(z.read('word/fontTable.xml'));rels=ET.fromstring(z.read('word/_rels/fontTable.xml.rels'))
    self.assertEqual({n.get('{'+W+'}name') for n in fonts},{'Times New Roman','Noto Serif CJK SC'})
    links={n.get('Id'):n.get('Target') for n in rels}
    embedded=list(fonts.findall('.//w:embedRegular',NS))+list(fonts.findall('.//w:embedBold',NS))
    self.assertEqual(len(embedded),2)
    for e in embedded:
     key=bytes.fromhex(e.get('{'+W+'}fontKey').strip('{}').replace('-',''))[::-1]
     raw=bytearray(z.read('word/'+links[e.get('{'+R+'}id')]))
     for i in range(32):raw[i]^=key[i%16]
     self.assertEqual(raw[:4],b'OTTO')
 def test_fixed_leading_without_document_grid(self):
  for p in self.files():
   with ZipFile(p) as z:
    styles=ET.fromstring(z.read('word/styles.xml'));doc=ET.fromstring(z.read('word/document.xml'))
   normal=next(n for n in styles.findall('w:style',NS) if n.get('{'+W+'}styleId')=='Normal')
   spacing=normal.find('w:pPr/w:spacing',NS)
   self.assertEqual(spacing.get('{'+W+'}lineRule'),'exact')
   self.assertEqual(normal.find('w:pPr/w:snapToGrid',NS).get('{'+W+'}val'),'false')
   self.assertFalse(doc.findall('.//w:docGrid',NS))
 def test_all_report_figures_use_only_blue_and_neutral_colors(self):
  files=list((ROOT/'reports/figures/editorial').glob('*.svg'));self.assertEqual(len(files),22)
  for p in files:
   for color in set(re.findall(r'#[0-9a-fA-F]{6}\b',p.read_text())):
    rgb=[int(color[i:i+2],16)/255 for i in (1,3,5)];h,s,v=colorsys.rgb_to_hsv(*rgb)
    self.assertTrue(s<=.1 or .52<=h<=.65,(p.name,color))

if __name__=='__main__':unittest.main()
