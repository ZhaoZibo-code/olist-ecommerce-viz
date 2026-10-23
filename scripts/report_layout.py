"""Build course DOCX reports and an editable writing template from aggregate evidence."""
from pathlib import Path
import json,sys
from docx import Document
from docx.shared import Cm,Pt,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT,WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports'
D=json.loads((OUT/'analysis_snapshot.json').read_text());Q=D['quality'];S=D['summary'];E=D['extras'];SC=D['scope'];C=D['config']
FONT='Noto Serif CJK SC'; LATIN='Times New Roman'
TOC_PATH=OUT/'.qa/toc_pages.json'
if not TOC_PATH.exists():TOC_PATH=OUT/'toc_manifest.json'
TOC_MAP=json.loads(TOC_PATH.read_text()) if TOC_PATH.exists() else {}

def n(v):return f'{v:,.0f}'
def f(v,places=2):return f'{v:,.{places}f}'
def p(v):return f'{v:.2f}%'
def setfont(style,size,bold=False):
 style.font.name=LATIN;style.font.size=Pt(size);style.font.bold=bold;style.font.color.rgb=RGBColor(0,0,0)
 r=style.element.get_or_add_rPr();rf=r.find(qn('w:rFonts'))
 if rf is None:rf=OxmlElement('w:rFonts');r.insert(0,rf)
 for attr in ['asciiTheme','hAnsiTheme','eastAsiaTheme','csTheme','cstheme']:
  rf.attrib.pop(qn('w:'+attr),None)
 for k in ['ascii','hAnsi','cs']:rf.set(qn('w:'+k),LATIN)
 rf.set(qn('w:eastAsia'),FONT)

def element(tag,**attrs):
 x=OxmlElement('w:'+tag)
 for k,v in attrs.items():x.set(qn('w:'+k),str(v))
 return x

class Report:
 def __init__(self,title,subtitle):
  self.doc=Document();self.title=title;self.headings=[];self.body_started=False;s=self.doc.sections[0]
  # WPS can snap proportional leading to the default 18 pt document grid.
  # Use explicit leading and no grid so native editors agree on pagination.
  for grid in s._sectPr.findall(qn('w:docGrid')):s._sectPr.remove(grid)
  for style in self.doc.styles:
   if hasattr(style,'font'):setfont(style,11.5)
   if style.type==1:
    style.element.get_or_add_pPr().append(element('snapToGrid',val='false'))
  for border in self.doc.styles.element.xpath('.//w:pBdr'):
   border.getparent().remove(border)
  s.page_width=Cm(21);s.page_height=Cm(29.7);s.top_margin=Cm(2.2);s.bottom_margin=Cm(2.1);s.left_margin=Cm(2.4);s.right_margin=Cm(2.3);s.header_distance=Cm(1);s.footer_distance=Cm(1)
  for name,size,bold in [('Normal',11.5,False),('Title',25,True),('Subtitle',13,False),('Heading 1',18,True),('Heading 2',12.5,True),('Caption',10,False)]:setfont(self.doc.styles[name],size,bold)
  for name in ['Normal','Caption']:
   pf=self.doc.styles[name].paragraph_format;pf.line_spacing=Pt(15 if name=='Caption' else 18.5);pf.space_after=Pt(8)
  for name in ['Heading 1','Heading 2']:
   pf=self.doc.styles[name].paragraph_format;pf.space_before=Pt(9);pf.space_after=Pt(10);pf.keep_with_next=True
   pf.line_spacing=Pt(28 if name=='Heading 1' else 20)
  self.doc.styles['Title'].paragraph_format.line_spacing=Pt(39)
  self.doc.styles['Subtitle'].paragraph_format.line_spacing=Pt(21)
  for name,size,bold in [('TOC Heading',18,True),('TOC 1',10.5,False),('Header',8.5,False),('Footer',8.5,False),('Table Normal',10,False)]:
   if name in self.doc.styles:setfont(self.doc.styles[name],size,bold)
  for style in self.doc.styles:
   for rf in style.element.xpath('.//w:rFonts'):
    for attr in ['asciiTheme','hAnsiTheme','eastAsiaTheme','csTheme','cstheme']:rf.attrib.pop(qn('w:'+attr),None)
    for attr in ['ascii','hAnsi','cs']:rf.set(qn('w:'+attr),LATIN)
    rf.set(qn('w:eastAsia'),FONT)
  self.doc.styles['Normal'].paragraph_format.widow_control=True
  for name,leading in [('TOC Heading',28),('TOC 1',17),('Header',13),('Footer',13)]:
   if name in self.doc.styles:self.doc.styles[name].paragraph_format.line_spacing=Pt(leading)
  s.different_first_page_header_footer=True
  hp=s.header.paragraphs[0];hp.text='OLIST  /  巴西电商数据研究';hp.alignment=WD_ALIGN_PARAGRAPH.RIGHT
  for r in hp.runs:r.font.size=Pt(8);r.font.color.rgb=RGBColor(0,0,0)
  foot=s.footer.paragraphs[0];foot.alignment=WD_ALIGN_PARAGRAPH.CENTER
  foot.add_run('Olist 电商课程项目    ')
  fld=element('fldSimple',instr='PAGE');fld.append(element('r'));foot._p.append(fld)
  for r in foot.runs:r.font.size=Pt(8)
  self.doc.core_properties.title=title;self.doc.core_properties.author='Olist 电商项目组';self.doc.core_properties.subject=subtitle
  self.para('数据分析课程项目',after=36)
  self.doc.add_paragraph(title,'Title');self.doc.add_paragraph(subtitle,'Subtitle')
  self.para('研究对象  2016—2018 年 Olist 历史交易样本',before=28)
  self.para('数据来源  和鲸社区公开 SQL 数据集')
  self.para('编制日期  '+C['report_date'])
  self.para('项目组  赵子博  杨宇航  王子豪  周书悦')
  self.para('分析方法  pandas 与 matplotlib  支持交互研究图谱',after=26)
  self.para('本研究将订单、商品、支付和评价分别按业务粒度处理，用可复算的数字回答规模、结构和履约体验问题。报告中的图表仅使用汇总数据。')
  toc_heading=self.doc.add_paragraph('目录','TOC Heading');toc_heading.paragraph_format.page_break_before=True
  self.toc=self.doc.add_paragraph()
  self.para('阅读方式  正文按问题展开；图下注明分母与来源；附录给出代码入口、证据文件和辅助使用记录。',before=16)
 def para(self,text,before=0,after=7,bold=False):
  x=self.doc.add_paragraph();x.paragraph_format.space_before=Pt(before);x.paragraph_format.space_after=Pt(after);x.add_run(text).bold=bold;return x
 def page(self,title):
  heading=self.doc.add_paragraph(title,'Heading 1');heading.paragraph_format.page_break_before=(not self.body_started or title.startswith('附录'))
  heading.paragraph_format.space_before=Pt(18);heading.paragraph_format.space_after=Pt(9)
  self.body_started=True;self.headings.append(title)
 def sub(self,title):self.doc.add_paragraph(title,'Heading 2')
 def paras(self,*texts):
  for text in texts:self.para(text)
 def fig(self,name,caption,note,interpret):self.figure('editorial/'+name,caption,note,interpret)
 def table(self,caption,heads,rows,widths=None):
  cap=self.para(caption,before=6,after=6,bold=True);cap.paragraph_format.keep_with_next=True
  t=self.doc.add_table(rows=1,cols=len(heads));t.alignment=WD_TABLE_ALIGNMENT.CENTER;t.autofit=False
  if widths:
   for col,w in zip(t.columns,widths):col.width=Cm(w)
  for i,x in enumerate(heads):t.rows[0].cells[i].text=str(x)
  for row in rows:
   cells=t.add_row().cells
   for i,x in enumerate(row):cells[i].text=str(x)
  for j,row in enumerate(t.rows):
   row._tr.get_or_add_trPr().append(element('cantSplit'))
   if j==0:row._tr.get_or_add_trPr().append(element('tblHeader',val='true'))
   for i,cell in enumerate(row.cells):
    if widths:cell.width=Cm(widths[i])
    cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
    tcpr=cell._tc.get_or_add_tcPr();tcpr.append(element('shd',fill=C['theme']['navy'].lstrip('#') if j==0 else ('F1F5F8' if j%2==0 else 'FFFFFF')))
    borders=element('tcBorders')
    for side in ['top','left','bottom','right']:borders.append(element(side,val='single',sz=4,color='D9D9D9'))
    tcpr.append(borders);m=element('tcMar')
    for side in ['top','bottom']:m.append(element(side,w=85,type='dxa'))
    for side in ['left','right']:m.append(element(side,w=100,type='dxa'))
    tcpr.append(m)
    for pp in cell.paragraphs:
     pp.paragraph_format.space_after=Pt(0);pp.paragraph_format.line_spacing=Pt(15)
     if i==0 or (len(str(rows[0][i]))<16 if rows else True):pp.alignment=WD_ALIGN_PARAGRAPH.CENTER
     for r in pp.runs:
      r.font.size=Pt(10);r.bold=j==0
      if j==0:r.font.color.rgb=RGBColor(255,255,255)
  self.para('',after=2)
 def figure(self,name,caption,note,interpret):
  pp=self.doc.add_paragraph();pp.paragraph_format.space_after=Pt(2);pp.paragraph_format.keep_with_next=True
  pp.paragraph_format.line_spacing=1
  pp.add_run().add_picture(str(OUT/'figures'/(name+'.png')),width=Cm(16.1))
  pp=self.doc.add_paragraph(caption,'Caption');pp.alignment=WD_ALIGN_PARAGRAPH.CENTER;pp.paragraph_format.keep_with_next=True
  source=self.para('口径与来源  '+note,after=6)
  source.paragraph_format.line_spacing=Pt(14.5)
  for run in source.runs:run.font.size=Pt(9.5);run.font.color.rgb=RGBColor.from_string('526A7A')
  self.para('图表解读  '+interpret)
 def save(self,name):
  # TOC field with a readable cache; Word can regenerate from Heading styles.
  r=element('r');r.append(element('fldChar',fldCharType='begin',fldLock='true'));self.toc._p.append(r)
  r=element('r');txt=element('instrText',space='preserve');txt.text=' TOC \\o "1-1" \\h \\z \\u ';r.append(txt);self.toc._p.append(r)
  r=element('r');r.append(element('fldChar',fldCharType='separate'));self.toc._p.append(r)
  for i,h in enumerate(self.headings):
   self.toc.paragraph_format.line_spacing=Pt(19)
   rr=self.toc.add_run(h+'  ……  '+str(TOC_MAP.get(name,{}).get(h,i+3)));rr.font.size=Pt(10.5)
   if i<len(self.headings)-1:rr.add_break()
  r=element('r');r.append(element('fldChar',fldCharType='end'));self.toc._p.append(r)
  self.doc.settings.element.append(element('updateFields',val='false'))
  self.doc.settings.element.append(element('embedTrueTypeFonts',val='true'))
  self.doc.settings.element.append(element('doNotEmbedSystemFonts',val='true'))
  self.doc.save(OUT/name)
  from embed_report_fonts import normalize_and_embed
  normalize_and_embed(OUT/name)
  print(name,len(self.headings),'sections')

def use_record(r,chapter,index=2):
 r.table('表 '+chapter+'-'+str(index)+' 大模型辅助使用及验证记录',['环节','采纳与处理','验证方法'],[
 ['需求衔接','根据项目任务书完成Olist质量与分析报告','阅读任务书及四份参考文档；不沿用信令示例数字'],
 ['质量与分析','辅助编写审计、汇总、图表和报告生成代码','本机运行原始七表；订单粒度与金额独立核对'],
 ['写作排版','辅助统一字体、目录、行距与配色，正文数字由汇总结果生成','核对正文、图表与汇总快照，检查Word和PDF版式'],
 ['代码审查','使用大模型辅助检查复现入口、参数配置和关联校验，建议经检查和实际运行后采用','检查源码并重新运行；已验证macOS环境，Windows命令尚未实测']
 ],[2.1,7.2,6.8])
 r.para('大模型用于辅助代码编写、报告组织和排版检查。统计结果由原始七表计算，并以独立SQL和自动测试核对。原始数据在本地处理，报告仅展示汇总结果。项目组负责复核与解释最终内容。')
 r.table('表 '+chapter+'-3 小组分工与交叉复核安排',['成员','安排占比','负责内容','复核人'],[[m['name'],str(m['share'])+'%',m['role'],rv] for m,rv in zip(C['team'],['杨宇航','王子豪','周书悦','赵子博'])],[2.2,2.2,9.4,2.3])
 r.para('四名成员各承担25%的安排比例。真实个人提交、完成后的交叉复核和成员确认由小组据实际协作补充，本表不代替个人Git记录或签字。')
