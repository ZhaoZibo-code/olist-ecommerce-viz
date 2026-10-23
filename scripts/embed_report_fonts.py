"""Embed the OFL report fonts and remove unused template font declarations."""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from lxml import etree as ET
import uuid

W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
P='http://schemas.openxmlformats.org/package/2006/relationships'
A='http://schemas.openxmlformats.org/drawingml/2006/main'
CT='http://schemas.openxmlformats.org/package/2006/content-types'
ROOT=Path(__file__).resolve().parents[1]

def normalize_and_embed(path):
 with ZipFile(path) as z:parts={n:z.read(n) for n in z.namelist()}
 fonts=ET.Element('{'+W+'}fonts',nsmap={'w':W,'r':R})
 times=ET.SubElement(fonts,'{'+W+'}font',{'{'+W+'}name':'Times New Roman'})
 ET.SubElement(times,'{'+W+'}family',{'{'+W+'}val':'roman'})
 noto=ET.SubElement(fonts,'{'+W+'}font',{'{'+W+'}name':'Noto Serif CJK SC'})
 ET.SubElement(noto,'{'+W+'}family',{'{'+W+'}val':'roman'})
 rels=ET.Element('{'+P+'}Relationships',nsmap={None:P})
 for weight,tag in [('Regular','embedRegular'),('Bold','embedBold')]:
  fontpath=ROOT/'assets/report-fonts'/('NotoSerifCJKsc-'+weight+'.otf')
  key=uuid.uuid5(uuid.NAMESPACE_URL,'olist-report-font-'+weight)
  data=bytearray(fontpath.read_bytes());mask=key.bytes[::-1]
  for i in range(32):data[i]^=mask[i%16]
  rid='rFont'+weight;name='fonts/NotoSerifCJKsc-'+weight+'.odttf'
  parts['word/'+name]=bytes(data)
  ET.SubElement(noto,'{'+W+'}'+tag,{'{'+R+'}id':rid,'{'+W+'}fontKey':'{'+str(key).upper()+'}','{'+W+'}subsetted':'true'})
  ET.SubElement(rels,'{'+P+'}Relationship',Id=rid,Type=R+'/font',Target=name)
 parts['word/fontTable.xml']=ET.tostring(fonts,xml_declaration=True,encoding='UTF-8',standalone=True)
 parts['word/_rels/fontTable.xml.rels']=ET.tostring(rels,xml_declaration=True,encoding='UTF-8',standalone=True)
 types=ET.fromstring(parts['[Content_Types].xml'])
 if not any(x.get('Extension')=='odttf' for x in types):
  ET.SubElement(types,'{'+CT+'}Default',Extension='odttf',ContentType='application/vnd.openxmlformats-officedocument.obfuscatedFont')
 parts['[Content_Types].xml']=ET.tostring(types,xml_declaration=True,encoding='UTF-8',standalone=True)
 # Do not let theme defaults reintroduce unavailable Calibri/Cambria families.
 theme=ET.fromstring(parts['word/theme/theme1.xml'])
 for font in theme.xpath('//a:majorFont/*|//a:minorFont/*',namespaces={'a':A}):
  if 'typeface' in font.attrib:font.set('typeface','Noto Serif CJK SC' if font.get('script') in ['Hans','Hant'] or ET.QName(font).localname=='ea' else 'Times New Roman')
 parts['word/theme/theme1.xml']=ET.tostring(theme,xml_declaration=True,encoding='UTF-8',standalone=True)
 with ZipFile(path,'w',ZIP_DEFLATED) as z:
  for name,data in parts.items():z.writestr(name,data)
