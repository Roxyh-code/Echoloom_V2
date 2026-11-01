"""Build the focused schema review. No downloads or model calls.

Run from repo root: python literature/scripts/build_schema_report.py
Requires matplotlib, markdown and a Chinese font.
"""
from pathlib import Path
import json, re, html, shutil, zipfile
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import markdown

ROOT = Path(__file__).resolve().parents[2]
LIT = ROOT / 'literature'
OUT = LIT / 'output/schema-foundations'
FIG = OUT / 'figures'
FIG.mkdir(exist_ok=True)
sources = json.loads((LIT/'data/schema-sources.json').read_text(encoding='utf-8'))['sources']
plt.rcParams.update({'font.family':'Microsoft YaHei','axes.unicode_minus':False,
                     'svg.fonttype':'none','font.size':11})
navy, teal, amber = '#19334a', '#17877d', '#b97d26'

fig, ax = plt.subplots(figsize=(12,5.4))
ax.set(xlim=(0,12),ylim=(0,6)); ax.axis('off')
panels = [(.2,1,3.2,3.5,'原始材料与来源',
           '文档／片段／作品版本\n人物提及与原话\n故事时间与叙述位置\n发言者和嵌套转述',navy),
          (4.3,1,3.2,3.5,'Evidence 候选',
           '原子主张与归属\n极性／模态／立场\n支持、反证和未知\n派生与审核记录',teal),
          (8.4,1,3.3,3.5,'人物表示候选',
           '倾向、状态、价值、目标\n信念、知识与情境反应\n语言风格与关系\n经历与自我解释',navy)]
for x,y,w,h,title,body,c in panels:
 ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.05',facecolor='#f0f6f6',edgecolor=c,lw=1.4))
 ax.text(x+.15,y+h-.35,title,color=c,fontweight='bold',fontsize=15)
 ax.text(x+.15,y+h-.95,body,va='top',linespacing=2,color=navy)
for a,b in [(3.45,4.2),(7.55,8.3)]:
 ax.annotate('',xy=(b,2.8),xytext=(a,2.8),arrowprops=dict(arrowstyle='->',color=teal,lw=2))
ax.text(6,5.4,'候选结构：证据链连接材料与解释',ha='center',fontsize=19,fontweight='bold',color=navy)
ax.text(6,.4,'时间 · 条件 · 世界版本 · 冲突记录贯穿各层；箭头不表示已证明心理因果',ha='center',color=amber,fontsize=11)
for ext in ['png','svg']:fig.savefig(FIG/f'candidate-structure.{ext}',dpi=160,bbox_inches='tight',facecolor='white')
plt.close(fig)

fields = ['traits','states','values','goals','beliefs_knowledge','behavior_patterns',
          'speech_style','relationships','biography','evidence','time_version','conflicts']
labels = ['稳定倾向','临时状态','价值取舍','目标与承诺','信念／知识','情境反应',
          '语言风格','人物关系','经历／自我解释','主张与证据','时间／版本','冲突记录']
theory={'P25','P26','S01','S02'}; resources={'S09','S10','S11'}; evaluation={'P19','S08','S13','S14'}
fig, ax=plt.subplots(figsize=(15,7.5))
colors={'T':navy,'M':teal,'R':'#6a62a6','E':amber}
for j,s in enumerate(sources):
 code='T' if s['id'] in theory else 'R' if s['id'] in resources else 'E' if s['id'] in evaluation else 'M'
 for i,f in enumerate(fields):
  relevant=f in s['fields']
  rect=plt.Rectangle((j-.46,i-.42),.92,.84,facecolor=colors[code] if relevant else '#eef1f3',edgecolor='white')
  ax.add_patch(rect)
  if relevant:ax.text(j,i,code,ha='center',va='center',color='white',fontweight='bold',fontsize=10)
ax.set_xlim(-.5,len(sources)-.5);ax.set_ylim(len(fields)-.5,-.5)
ax.set_xticks(range(len(sources)),[s['id']+('*' if s['id']=='S02' else '') for s in sources],rotation=45)
ax.set_yticks(range(len(labels)),labels);ax.tick_params(length=0)
for sp in ax.spines.values():sp.set_visible(False)
ax.set_title('字段与依据类型：同主题关联，不是独立证据投票',loc='left',pad=22,color=navy,fontweight='bold',fontsize=17)
fig.text(.17,.01,'T 理论概念 · M 方法/表示 · R 规范/文档 · E 评估需求；* S02仅摘要；空白表示本轮未建立关联',fontsize=11,color=navy)
fig.tight_layout(rect=(0,.045,1,1))
for ext in ['png','svg']:fig.savefig(FIG/f'field-source-map.{ext}',dpi=160,bbox_inches='tight',facecolor='white')
plt.close(fig)

report=OUT/'report.md'
for svg_path in FIG.glob('*.svg'):
 svg_path.write_text('\n'.join(line.rstrip() for line in svg_path.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8')
text=report.read_text(encoding='utf-8').replace('<!-- FIELD_DIAGRAM -->','![候选结构图](figures/candidate-structure.png)')
appendix='## 附录：来源与阅读层级\n\n| ID | 年份与来源 | 类型 | 阅读层级 |\n| --- | --- | --- | --- |\n'
for s in sources:
 appendix+=f"| [{s['id']}](../../organization/reading-notes/{s['id']}-schema-basis.md) | {s['year']} · [{s['title']}]({s['url']}) | {s['kind']} | {s['reading']} |\n"
appendix+='\n完整数据见[23项来源](../../data/schema-sources.json)、[检索记录](../../data/search-log.json)与[下一步计划](../../plans/next-steps.md)。\n'
field_section='## 附录：候选字段的逐项依据\n\n![字段与来源类型](figures/field-source-map.png)\n\n'
matrix=(LIT/'organization/schema-field-matrix.md').read_text(encoding='utf-8')
start=matrix.index('| 模块/候选对象');end=matrix.index('## 三类不确定性')
field_section+=matrix[start:end]
generated='<!-- GENERATED_APPENDIX_START -->\n'+field_section+'\n'+appendix+'<!-- GENERATED_APPENDIX_END -->'
if '<!-- SOURCE_APPENDIX -->' in text:text=text.replace('<!-- SOURCE_APPENDIX -->',generated)
else:text=re.sub(r'<!-- GENERATED_APPENDIX_START -->.*?<!-- GENERATED_APPENDIX_END -->',lambda m:generated,text,flags=re.S)
report.write_text(text,encoding='utf-8')
body=markdown.markdown(text,extensions=['tables','toc','fenced_code'])
for name in ['candidate-structure','field-source-map']:
 svg=(FIG/f'{name}.svg').read_text(encoding='utf-8');svg=re.sub(r'<\?xml[^>]*\?>|<!DOCTYPE[^>]*>','',svg,flags=re.S)
 body=re.sub(r'<img alt="[^"]*" src="figures/'+name+r'\.png"\s*/?>',lambda m:svg,body)
# Internal repo links are represented by corresponding public repo paths in the offline copy.
def externalize(m):
 url=m[1]
 if url.startswith(('https:','http:','#')):return m[0]
 target=(OUT/url).resolve()
 if target.is_relative_to(ROOT):return 'href="https://github.com/Roxyh-code/Echoloom_V2/blob/main/'+target.relative_to(ROOT).as_posix()+'"'
 return m[0]
body=re.sub(r'href="([^"]+)"',externalize,body)
cards=[]
for s in sources:
 search=html.escape(' '.join(str(s[k]) for k in ['id','title','authors','concept','design','limit']),quote=True)
 cards.append(f'''<details class="source" data-axis="{s['axis']}" data-search="{search}"><summary>{s['id']} · {html.escape(s['title'])}<small>{s['year']} · {s['kind']} · {s['reading']}</small></summary><dl>{''.join('<dt>'+label+'</dt><dd>'+html.escape(str(s[key]))+'</dd>' for label,key in [('作者','authors'),('原文定位','locator'),('概念','concept'),('设计推导','design'),('边界','limit')])}</dl><p><a href="{s['url']}">原文 ↗</a></p></details>''')
axes=list(dict.fromkeys(s['axis'] for s in sources))
style='''*{box-sizing:border-box}body{margin:0;background:#eef3f5;color:#19334a;font:16px/1.9 "Microsoft YaHei",sans-serif}header{background:#19334a;color:white;padding:45px max(25px,7vw)}header h1{font-size:32px;line-height:1.6;margin:10px 0}header p{color:#c8dce5}.wrap{max-width:1200px;margin:30px auto;background:white;padding:35px 50px;border-radius:12px}h2{margin-top:50px;padding-top:20px;border-top:1px solid #dce5e9;font-size:25px}h3{font-size:20px;margin-top:30px}a{color:#087e75}table{display:block;overflow:auto;border-collapse:collapse;font-size:13px;line-height:1.8;margin:25px 0;width:100%}th,td{padding:12px;border-bottom:1px solid #dce5e9;vertical-align:top}th{background:#eaf3f3;text-align:left;white-space:nowrap}svg{max-width:100%;height:auto}small{display:block;color:#63778a;font-size:12px}.source{border:1px solid #dce5e9;border-radius:7px;margin:12px 0;padding:14px}.source summary{cursor:pointer;font-weight:bold}.source dl{font-size:14px}.source dt{font-weight:bold;color:#16877e;margin-top:12px}.source dd{margin-left:0}.controls{display:flex;gap:12px;flex-wrap:wrap;position:sticky;top:0;background:white;padding:15px 0}input,select{padding:10px;border:1px solid #c5d6de;border-radius:6px;font:inherit;font-size:14px}input{flex:1;min-width:220px}.hidden{display:none}.meta{font-size:13px;color:#63778a}.intro{padding:16px;background:#ecf7f3;border-left:4px solid #17877d}@media(max-width:750px){.wrap{margin:12px;padding:22px}header{padding:25px}header h1{font-size:25px}}@media print{body{background:white}.wrap{padding:0;margin:0}.controls{display:none}table{font-size:9pt}h2{break-after:avoid}svg{break-inside:avoid}}'''
page=f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>EchoLoom · Schema依据专项报告</title><style>{style}</style></head><body><header><small style="color:#92d0c6">ECHOLOOM / SCHEMA FOUNDATIONS</small><h1>人物应该表示什么，<br>每项判断依据什么？</h1><p>23项核心来源 · 12组候选字段 · 四条研究线 · 2026-10-31</p></header><main class="wrap"><p class="intro">当前任务：为Personality Schema与Evidence Schema建立依据。字段仍是候选；本报告不声称已完成Schema验证。</p>{body}<h2>逐篇概念与设计边界</h2><div class="controls"><input aria-label="搜索来源" id="search" placeholder="搜索文献、概念或字段设计…"><select aria-label="按研究方向筛选" id="axis"><option value="">全部方向</option>{''.join('<option>'+a+'</option>' for a in axes)}</select><span id="count" class="meta"></span></div>{''.join(cards)}<p class="meta">本HTML内嵌图表，可离线阅读。原文和Git文件链接需要网络；来源数据与计划随完整资料包提供。</p></main><script>const cards=[...document.querySelectorAll('.source')];function filter(){{const q=document.querySelector('#search').value.toLowerCase(),a=document.querySelector('#axis').value;let n=0;for(const c of cards){{const show=(!q||c.dataset.search.toLowerCase().includes(q))&&(!a||c.dataset.axis===a);c.classList.toggle('hidden',!show);n+=show?1:0}}document.querySelector('#count').textContent=n+' / 23项'}}document.querySelector('#search').addEventListener('input',filter);document.querySelector('#axis').addEventListener('input',filter);filter();</script></body></html>'''
page='\n'.join(line.rstrip() for line in page.splitlines())+'\n'
(OUT/'index.html').write_text(page,encoding='utf-8')
deliver=ROOT/'outputs/schema-foundations'
shutil.copytree(OUT,deliver,dirs_exist_ok=True)
for path in ['data/schema-sources.json','data/search-log.json','data/source-manifest.json','plans/next-steps.md','organization/schema-field-matrix.md']:
 dst=deliver/path;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(LIT/path,dst)
matrix_copy=deliver/'organization/schema-field-matrix.md'
matrix_copy.write_text(matrix_copy.read_text(encoding='utf-8').replace('../output/schema-foundations/report.md','../report.md'),encoding='utf-8')
# Keep Markdown relative paths usable within the deliverable directory tree.
for note in (LIT/'organization/reading-notes').glob('*-schema-basis.md'):
 dst=deliver/'organization/reading-notes'/note.name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(note,dst)
(deliver/'report.md').write_text(text.replace('../../organization/','organization/').replace('../../data/','data/').replace('../../plans/','plans/'),encoding='utf-8')
(deliver/'README.md').write_text('打开 index.html 阅读当前报告。report.md 为正文，figures 为原创图，data 为来源数据，organization 为逐篇依据，plans 为下一步计划。\n',encoding='utf-8')
with zipfile.ZipFile(ROOT/'outputs/EchoLoom-schema-foundations.zip','w',zipfile.ZIP_DEFLATED) as z:
 for f in deliver.rglob('*'):
  if f.is_file():z.write(f,Path('schema-foundations')/f.relative_to(deliver))
assert len(sources)==23 and len({s['id'] for s in sources})==23
assert page.count('<details class="source"')==23 and '<!-- FIELD_DIAGRAM -->' not in page
print('Built: 23 sources, 12 field groups, 2 figures; repo report + outputs + ZIP')
