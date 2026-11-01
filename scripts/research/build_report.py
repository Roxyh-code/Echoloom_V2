"""Build the offline literature report from reviewed coding data.

Requires Python 3, matplotlib, markdown. Does not fetch sources or call models.
Run from repository root: python scripts/research/build_report.py
"""
from pathlib import Path
from collections import Counter
import json,re,html,base64,shutil
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import markdown

ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/'docs/research/review'; FIG=SRC/'figures'; FIG.mkdir(exist_ok=True)
OUT=ROOT/'outputs'/'literature-review';OUT.mkdir(parents=True,exist_ok=True)
data=json.loads((SRC/'coding.json').read_text(encoding='utf-8'));papers=data['papers'];byid={p['id']:p for p in papers}
plt.rcParams.update({'font.family':'Microsoft YaHei','axes.unicode_minus':False,'svg.fonttype':'none','font.size':11,'axes.spines.top':False,'axes.spines.right':False,'axes.spines.left':False,'axes.edgecolor':'#cbd5e1','xtick.color':'#475569','ytick.color':'#334155','text.color':'#14283f','axes.labelcolor':'#475569','figure.facecolor':'#fff','axes.facecolor':'#fff','savefig.facecolor':'#fff'})
TEAL='#168a82';NAVY='#244768';AMBER='#c58b2c';GRAY='#94a3b8'
quant=[];figures={};tips={};tip_n=0
def q(pid,series,condition,value,unit,locator,scope,sd=None):
 d=dict(id=f'Q{len(quant)+1:03}',paper=pid,series=series,condition=condition,value=value,unit=unit,locator=locator,scope=scope,sd=sd,source=byid[pid]['pdf'],provenance='论文原值')
 quant.append(d);return d
def tooltip(patch,label):
 global tip_n
 tip_n+=1;key=f'tip_{tip_n}';patch.set_gid(key);tips[key]=label
def bars(ax,labels,values,ids,colors=None,xmax=None,errors=None,units='%'):
 patches=ax.barh(labels,values,color=colors or TEAL,height=.57,xerr=errors,error_kw={'elinewidth':1,'capsize':3})
 ax.invert_yaxis();ax.grid(axis='x',color='#e2e8f0',zorder=0);ax.set_axisbelow(True)
 for i,p in enumerate(patches):
  tooltip(p,f'{labels[i]}：{values[i]:g}{units}；{ids[i]}')
  ax.text(values[i]+(xmax or max(values))*.015,i,f'{values[i]:g}',va='center',fontsize=11,fontweight='bold')
 if xmax:ax.set_xlim(0,xmax)
def save(fig,key,title):
 fig.savefig(FIG/f'{key}.svg',bbox_inches='tight',pad_inches=.25)
 fig.savefig(FIG/f'{key}.png',dpi=160,bbox_inches='tight',pad_inches=.25)
 plt.close(fig)
 svg=(FIG/f'{key}.svg').read_text(encoding='utf-8')
 for k,v in tips.items():svg=svg.replace(f'<g id="{k}">',f'<g id="{k}"><title>{html.escape(v)}</title>')
 svg=re.sub(r'<\?xml[^>]*\?>','',svg);svg=re.sub(r'<!DOCTYPE[^>]*>','',svg,flags=re.S)
 figures[key]=f'<figure aria-label="{html.escape(title)}">{svg}<figcaption>{html.escape(title)} · 悬停条块可查看数值与论文ID</figcaption></figure>'

# 1 Corpus composition. Counts reflect selection, not field prevalence.
groups=Counter(p['group'] for p in papers);years=Counter(p['year'] for p in papers)
fig,axs=plt.subplots(1,2,figsize=(12,5),gridspec_kw={'width_ratios':[1.25,1]})
bars(axs[0],list(groups),list(groups.values()),[', '.join(p['id'] for p in papers if p['group']==g) for g in groups],xmax=10,units='篇')
axs[0].set_title('主要研究问题（每篇归入一类）',loc='left',fontweight='bold',pad=16)
ys=sorted(years);bp=axs[1].bar([str(y) for y in ys],[years[y] for y in ys],color=NAVY,width=.65)
for y,b in zip(ys,bp):
 tooltip(b,f'{y}：{years[y]}篇；'+', '.join(p['id'] for p in papers if p['year']==y));axs[1].text(b.get_x()+b.get_width()/2,b.get_height()+.1,str(years[y]),ha='center')
axs[1].set_ylim(0,max(years.values())+2);axs[1].tick_params(axis='x',rotation=55);axs[1].set_title('本候选池的出版年份',loc='left',fontweight='bold',pad=16)
fig.tight_layout(w_pad=2);save(fig,'landscape','图1｜39篇目的性候选的研究方向与年份')

# 2 Multi-label map: unfilled is unconfirmed, not absence.
features=list(papers[0]['features']);fig,ax=plt.subplots(figsize=(11,13))
short=['原文／事实核查','特质／人格表示','时间／状态变化','编辑／共创','人物归属','直接多来源\n冲突重建']
for i,p in enumerate(papers):
 for j,f in enumerate(features):
  yes=p['features'][f]==1;r=Rectangle((j-.45,i-.42),.90,.84,facecolor=TEAL if yes else '#f1f5f9',edgecolor='white')
  ax.add_patch(r);tooltip(r,f"{p['id']} {p['title']}｜{f}："+('已读到明确线索' if yes else '本轮未确认，不表示不支持'))
ax.set(xlim=(-.5,len(features)-.5),ylim=(len(papers)-.5,-.5));ax.set_xticks(range(len(features)),short);ax.xaxis.tick_top();ax.set_yticks(range(len(papers)),[p['id']+' '+p['group'] for p in papers],fontsize=8)
ax.tick_params(length=0);ax.set_title('绿色：本轮确认涉及　浅灰：未确认；非系统能力评测',pad=48,fontsize=12,loc='left');fig.tight_layout();save(fig,'coverage','图2｜研究线索覆盖矩阵，分母为39篇论文')

# 3 Fidelity versus coverage tradeoff, same paper and experiment.
raw=[q('P06','生成陈述标签','完全支持',52,'%', 'Table 2 / PDF p.5','1,000条标注陈述'),q('P06','生成陈述标签','大致支持',15.4,'%', 'Table 2 / PDF p.5','同上；不是完全支持'),q('P06','生成陈述标签','不支持、矛盾或模糊',32.6,'%', 'Table 2 / PDF p.5','三类合计；不能全部称为编造')]
vals=[q('P06','验证器','Zero-shot None precision',83.5,'%', 'Table 3 / PDF p.5','该任务的分类精确率'),q('P06','验证器','Trained All precision',93.0,'%', 'Table 3 / PDF p.5','训练后的完整设置'),q('P06','验证器','Zero-shot None recall',93.0,'%', 'Table 3 / PDF p.5','该任务召回率'),q('P06','验证器','Trained All recall',74.6,'%', 'Table 3 / PDF p.5','与精确率同时报告')]
fig,axs=plt.subplots(1,2,figsize=(12,4),gridspec_kw={'width_ratios':[.85,1.15]})
bottom=0
for d,c in zip(raw,[TEAL,AMBER,GRAY]):
 b=axs[0].bar('原始陈述',d['value'],bottom=bottom,color=c,label=d['condition']);tooltip(b[0],f"P06：{d['condition']} {d['value']}%；n=1,000")
 axs[0].text(0,bottom+d['value']/2,f"{d['value']}%",ha='center',va='center',color='white',fontweight='bold');bottom+=d['value']
axs[0].set_ylim(0,100);axs[0].set_title('过滤之前：支持程度分布',loc='left');axs[0].legend(fontsize=8,loc='upper left',bbox_to_anchor=(-.05,-.12))
bars(axs[1],['无训练 · 精确率','训练后 · 精确率','无训练 · 召回率','训练后 · 召回率'],[d['value'] for d in vals],['P06 Table 3']*4,[NAVY,TEAL,NAVY,TEAL],xmax=105)
axs[1].set_title('提高精确率，同时损失召回',loc='left');fig.tight_layout();save(fig,'validation','图3｜CHIRON：错误过滤的收益和遗漏代价')

# 4 Representation, strictly paired conditions.
conditions=['全片段 · 摘要','全片段 · CHIRON','仅人物视角 · 摘要','仅人物视角 · CHIRON'];numbers=[44.9,47.6,42.2,56.5]
for c,v in zip(conditions,numbers):q('P06','遮名人物识别',c,v,'%', 'Table 6 / PDF p.7','147个人物实例；不是人格抽取正确率')
fig,ax=plt.subplots(figsize=(10,3.8));bars(ax,conditions,numbers,['P06 Table 6；147实例']*4,[NAVY,TEAL,NAVY,TEAL],xmax=70);ax.set_xlabel('遮名人物识别准确率（%）');fig.tight_layout();save(fig,'representation','图4｜同一任务中，档案与自由摘要的比较')

# 5 Retrieval, proxy metric explicitly labeled.
labs=['Llama-3 微调','＋BM25检索','＋共指检索','参考文本（量尺背景）'];vs=[16.87,22.70,40.21,65.27]
for c,v in zip(labs,vs):q('P07','人物描述NLI指标',c,v,'分', 'Table 3 / PDF p.8','自动NLI指标，不能视为人工准确率')
fig,ax=plt.subplots(figsize=(10,3.8));bars(ax,labs,vs,['P07 Table 3']*4,[NAVY,AMBER,TEAL,GRAY],xmax=80,units='分');ax.set_xlabel('人物描述任务：自动NLI指标（非人工准确率）');fig.tight_layout();save(fig,'retrieval','图5｜BookWorm：检索改进与自动量尺的边界')

# 6 History, std is not CI.
labs=['无历史 · 480 tokens','无历史 · 2K tokens','人物历史 · 1.6K tokens'];vs=[42.75,42.42,45.33];sd=[.97,.39,1.11]
for c,v,e in zip(labs,vs,sd):q('P08','英文测试特质选择',c,v,'%', 'Table 4 / PDF p.8','全量测试；五次运行；信息与长度同时变化',e)
fig,ax=plt.subplots(figsize=(10,3.4));bars(ax,labs,vs,['P08 Table 4；误差线为跨运行SD']*3,[NAVY,AMBER,TEAL],xmax=55,errors=sd);ax.set_xlabel('特质选择准确率（%）；误差线为标准差，不是置信区间');fig.tight_layout();save(fig,'context','图6｜PersoNet：扩大窗口与加入人物历史不是一回事')

# 7 Personality dimensions vs entire scales.
labs=['BFI · 单维度','BFI · 全维度','16P · 单维度','16P · 全维度'];vs=[76.6,31.2,80.7,44.8]
for c,v in zip(labs,vs):q('P19','人格标签对齐',c,v,'%', 'Table 2 / PDF p.7','GPT-4 ER-batch；32角色；边缘维度按论文规则忽略')
fig,ax=plt.subplots(figsize=(10,3.8));bars(ax,labs,vs,['P19 Table 2；不是原文重建准确率']*4,[TEAL,NAVY,TEAL,NAVY],xmax=100);ax.set_xlabel('访谈所得人格与人类感知标签的对齐（%）');fig.tight_layout();save(fig,'personality','图7｜InCharacter：单维度高分不等于全维度对齐')

# 8 Anonymous paired comparison, no universal decrease claim.
models=['Gemini-2.0-flash','Llama-3.1-405B','GPT-4o'];original=[3.251,2.907,2.884];anon=[3.229,2.913,2.792]
fig,ax=plt.subplots(figsize=(10,3.7))
for i,(m,a,b) in enumerate(zip(models,original,anon)):
 q('P22','匿名化平均一致性',m+' 原名',a,'分','Table 2 / PDF p.4','CharacterEval 1–5分；只GPT-4o平均下降有显著标记')
 q('P22','匿名化平均一致性',m+' 匿名',b,'分','Table 2 / PDF p.4','同上；不是所有模型都下降')
 ax.plot([a,b],[i,i],color=GRAY,lw=3);p=ax.scatter([a],[i],color=NAVY,s=80,label='原名' if i==0 else None);tooltip(p,f'P22 {m} 原名 {a}')
 p=ax.scatter([b],[i],color=TEAL,s=80,label='匿名' if i==0 else None);tooltip(p,f'P22 {m} 匿名 {b}')
 ax.text(3.40,i,f'{a:.3f} → {b:.3f}',va='center',fontsize=10)
ax.set_yticks(range(3),models);ax.invert_yaxis();ax.set_xlim(2.65,3.9);ax.set_xticks([2.7,2.9,3.1,3.3]);ax.grid(axis='x',color='#e2e8f0');ax.legend(loc='lower right');ax.set_xlabel('平均一致性评分（1–5分）；横轴局部放大显示条件差异');fig.tight_layout();save(fig,'anonymous','图8｜匿名化效应依赖模型，不能一概而论')

# 9 Human study cohorts, not summed across papers.
cohorts=[('P28','文本审核研究',12),('P28','创作交互研究',8),('P29','问卷',22),('P30','一周使用完成者',13),('P31','问卷',43),('P31','访谈',13),('P36','用户研究',14),('P37','对照用户研究',11),('P38','专业创作者',15),('P39','用户研究',12)]
fig,ax=plt.subplots(figsize=(10,5.2));bars(ax,[f'{p} {c}' for p,c,n in cohorts],[n for p,c,n in cohorts],[f'{p}；{c}；不同队列不合并' for p,c,n in cohorts],xmax=50,units='人');ax.set_xlabel('该研究队列人数；不跨论文汇总为独立参与者');fig.tight_layout();save(fig,'cohorts','图9｜交互与用户研究：证据来自具体任务与小型队列')
for p,c,n in cohorts:q(p,'参与者队列',c,n,'人',byid[p]['locator'],'仅该队列，不与其他论文合并')

# Other headline figures remain traceable even when not plotted.
for pid,series,c,v,unit,loc,scope in [
 ('P21','角色识别','Gemini-2.5-pro 全量',68.8,'%', 'Figure 3 / PDF p.6','全基准模型结果'),
 ('P21','角色识别','人类困难子集',90.8,'%', '§4.4 / PDF p.8','20人×50困难案例；分布与模型全量不同'),
 ('P15','错误类型','状态错误',38.6,'%', 'Table 3 / PDF p.5','205条可分析不忠实错误；多标签'),
 ('P15','错误类型','事件错误',31.5,'%', 'Table 3 / PDF p.5','同上，不是全部主张错误率'),
 ('P15','反驳推理','间接推理',50.2,'%', 'Table 3 / PDF p.5','错误分析子集'),
 ('P28','用户体验','CSI均值',71.5,'分','Table 2 / PDF p.9','第二研究n=8；SD=21.12；不是准确率'),
 ('P39','人工成对偏好','刻画：多数票',29,'对','§6.1 / PDF p.7','30对中的29对；不是个体评分比例'),
 ('P39','人工成对偏好','整体质量：多数票',25,'对','§6.1 / PDF p.7','30对中的25对'),
 ('P24','共指管道','gold CoNLL-F1',80.5,'分','Table 2 / PDF p.7','人工gold仅3书'),
 ('P02','原子事实支持','InstructGPT',42.5,'%', 'Table 1 / PDF p.4','183人物；2023年任务条件'),
 ('P02','原子事实支持','ChatGPT',58.3,'%', 'Table 1 / PDF p.4','同上，非当前模型基准'),
 ('P02','原子事实支持','PerplexityAI',71.5,'%', 'Table 1 / PDF p.4','同上，非当前产品基准')]:q(pid,series,c,v,unit,loc,scope)
(SRC/'quantitative.json').write_text(json.dumps({'as_of':data['as_of'],'records':quant},ensure_ascii=False,indent=2),encoding='utf-8')

# Generate compact per-paper evidence notes; do not relabel as page-by-page close reads.
for p in papers:
 note=f"# {p['id']} — {p['title']}\n\n阅读层级：{p['reading']}。{p['reading_scope']}。未复现。\n\n- 原文：{p['url']}\n- 阅读版本：{p['version']}\n- PDF SHA256：{p['sha256'] or '未取得'}\n- 定位：{p['locator']}\n\n## 方法与规模\n\n{p['method']}。{p['scale']}。\n\n## 作者结果与证据边界\n\n{p['finding']}。\n\n{p['limitations']}。\n\n## 对EchoLoom的分析\n\n{p['implication']}。这是待验证的迁移建议，不是本文已完成的实验。\n\n具体数字见[数值编码](../review/quantitative.json)，综合结论见[报告](../review/report.md)。\n"
 (ROOT/f"docs/research/papers/{p['id']}-evidence-review.md").write_text(note,encoding='utf-8')

body=markdown.markdown((SRC/'report.md').read_text(encoding='utf-8'),extensions=['tables','fenced_code','toc'])
for key,block in figures.items():
 body=body.replace(f'<!-- FIG:{key} -->',block)
 body=re.sub(r'<p><img alt="[^"]*" src="figures/'+re.escape(key)+r'\.png"\s*/?></p>',lambda m:block,body)
cards=[]
for p in papers:
 search=html.escape(' '.join(str(p[k]) for k in ['id','title','group','method','scale','finding','limitations']),quote=True)
 cards.append(f'''<article class="paper" id="{p['id']}" data-group="{html.escape(p['group'])}" data-reading="{p['reading']}" data-search="{search}"><details><summary><span class="pid">{p['id']}</span><span>{html.escape(p['title'])}<small>{p['year']} · {p['group']} · {p['reading']}</small></span></summary><div class="paperbody"><dl>{''.join('<dt>'+a+'</dt><dd>'+html.escape(str(p[b]))+'</dd>' for a,b in [('研究方法','method'),('材料与规模','scale'),('作者发现','finding'),('证据边界','limitations'),('设计启发（我们的分析）','implication'),('原文定位','locator'),('版本','version')])}</dl><p><a href="{html.escape(p['url'])}" target="_blank" rel="noopener">原论文／元数据 ↗</a> · <a href="{html.escape(p['pdf'])}" target="_blank" rel="noopener">阅读PDF ↗</a></p><p class="fine">{p['reading_scope']}。未复现。<br>SHA256：{p['sha256'] or '未取得可读全文'}</p></div></details></article>''')
options=''.join(f'<option>{html.escape(g)}</option>' for g in groups)
qrows=''.join(f'<tr><td><a href="#{d["paper"]}">{d["paper"]}</a></td><td>{html.escape(d["series"])}</td><td>{html.escape(d["condition"])}</td><td class="num">{d["value"]:g}{d["unit"]}</td><td>{html.escape(d["locator"])}</td><td>{html.escape(d["scope"])}</td></tr>' for d in quant)
dataset=json.dumps({'coding':data,'quantitative':quant},ensure_ascii=False).replace('</','<\\/')
style='''
:root{--ink:#14283f;--muted:#526477;--teal:#168a82;--line:#dce5ec;--paper:#fff;--bg:#f2f5f7}*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.85 "Microsoft YaHei","PingFang SC",sans-serif}a{color:#087f79;text-underline-offset:3px}header{background:#14283f;color:white;padding:55px max(6vw,24px) 45px}header .eyebrow{color:#82d3c6;letter-spacing:3px;font-size:13px}header h1{font-size:38px;line-height:1.4;max-width:1000px;margin:12px 0 18px}header p{max-width:900px;color:#d8e4ed}.stats{display:flex;gap:35px;flex-wrap:wrap;margin-top:28px}.stats strong{font-size:32px;color:white;display:block}.stats span{font-size:13px;color:#aac1d2}.layout{max-width:1500px;margin:auto;display:grid;grid-template-columns:210px minmax(0,1fr);gap:28px;padding:30px 24px}nav{position:sticky;top:24px;height:calc(100vh - 48px);overflow:auto;font-size:13px;padding:20px 10px}nav a{display:block;padding:8px 10px;text-decoration:none;color:var(--muted);border-left:2px solid transparent}nav a:hover{background:#e2eeed;border-left-color:var(--teal)}main{min-width:0;background:white;border:1px solid var(--line);border-radius:12px;padding:40px 48px;box-shadow:0 8px 30px #15304506}main>h1{display:none}h2{font-size:27px;margin-top:58px;border-top:1px solid var(--line);padding-top:30px;scroll-margin-top:24px;line-height:1.5}h3{font-size:21px;margin:30px 0 14px}p{margin:16px 0}strong{color:#114c58}table{border-collapse:collapse;width:100%;font-size:13px;line-height:1.7;margin:24px 0;display:block;overflow:auto}th{background:#edf4f5;color:#194a57;text-align:left;white-space:nowrap}th,td{border-bottom:1px solid var(--line);padding:12px 14px;vertical-align:top}tbody tr:nth-child(even){background:#fafcfd}.num{font-variant-numeric:tabular-nums;white-space:nowrap;font-weight:bold}figure{margin:30px 0;border:1px solid var(--line);border-radius:10px;padding:15px 15px 8px;background:white}figure svg{display:block;width:100%;height:auto}figcaption{font-size:12px;color:var(--muted);border-top:1px solid var(--line);padding:10px 5px}.controls{display:flex;gap:10px;flex-wrap:wrap;position:sticky;top:0;background:#fffffff5;padding:15px 0;z-index:3;border-bottom:1px solid var(--line)}input,select,button{font:inherit;font-size:13px;border:1px solid #bacbd6;border-radius:6px;padding:9px 12px;background:white;color:var(--ink)}input{min-width:240px;flex:1}button{cursor:pointer;background:var(--teal);color:white;border-color:var(--teal)}.paper{border:1px solid var(--line);border-radius:8px;margin:10px 0;scroll-margin-top:90px}.paper summary{display:flex;gap:13px;cursor:pointer;padding:16px;line-height:1.6;font-size:14px}.pid{background:#e6f2f0;color:#0d756e;border-radius:4px;height:28px;min-width:43px;padding:2px 7px;font-weight:bold}small{display:block;color:var(--muted);font-size:12px;margin-top:5px}.paperbody{padding:0 20px 20px}.paper dl{display:grid;grid-template-columns:155px 1fr;gap:8px;font-size:13px}.paper dt{font-weight:bold;color:#427078}.paper dd{margin:0}.fine{font-size:12px;color:var(--muted);overflow-wrap:anywhere}.note{background:#fff6e7;border-left:4px solid #c58b2c;padding:16px 20px;border-radius:4px}.toolbar{display:flex;gap:12px;flex-wrap:wrap}.hidden{display:none}footer{padding:30px;color:var(--muted);text-align:center;font-size:12px}@media(max-width:1000px){.layout{grid-template-columns:1fr;padding:15px}nav{position:static;height:auto;display:flex;overflow:auto;padding:0}nav a{white-space:nowrap}main{padding:22px}header h1{font-size:29px}}@media print{body{background:white;font-size:11pt}.layout{display:block;padding:0}nav,.controls,.toolbar,header .stats{display:none}header{background:white;color:var(--ink);padding:0 20px}header p,header .eyebrow{color:var(--muted)}header h1{font-size:24pt}main{padding:10px 20px;border:0;box-shadow:none}figure,table,.paper{break-inside:avoid}h2{break-after:avoid;font-size:19pt}h3{break-after:avoid}.paper details:not([open]) .paperbody{display:block}table{font-size:9pt}a{color:inherit;text-decoration:none}.paper summary{font-size:10pt}button{display:none}}
'''
nav=''.join(f'<a href="#{m.group(1)}">{re.sub("<[^>]+>","",m.group(2))}</a>' for m in re.finditer(r'<h2 id="([^"]+)">(.*?)</h2>',body))
page=f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>EchoLoom 文献结论报告</title><style>{style}</style></head><body><header><div class="eyebrow">ECHOLOOM / RESEARCH SYNTHESIS 01</div><h1>从多来源材料重建人物：<br>证据支持什么，下一步验证什么</h1><p>面向人物表示、证据链与角色一致性的文献结论报告。以可追溯结果支持设计判断，保留反例、分母和未解决的问题。</p><div class="stats"><div><strong>39</strong><span>目的性候选论文</span></div><div><strong>37 + 2</strong><span>全文定向核读＋摘要背景</span></div><div><strong>9</strong><span>可追溯研究图表</span></div><div><strong>2026.10.31</strong><span>本轮检索截止日</span></div></div></header><div class="layout"><nav>{nav}<a href="#papers">39篇逐篇明细</a><a href="#numbers">图表原始数字</a></nav><main><div class="toolbar"><button onclick="window.print()">打印／另存PDF</button><button id="downloadCoding">下载编码JSON</button><button id="downloadNumbers">下载数字JSON</button></div>{body}<h2 id="papers">附录A · 39篇逐篇明细</h2><p>展开查看原文定位、结果边界与设计启发。搜索同时检索方法与局限。浅灰矩阵格不代表能力不存在。</p><div class="controls"><input id="search" aria-label="搜索论文" placeholder="搜索ID、标题、方法或问题…"><select id="group" aria-label="按研究方向筛选"><option value="">全部方向</option>{options}</select><select id="reading" aria-label="按阅读层级筛选"><option value="">全部阅读层级</option><option>全文定向核读</option><option>摘要／理论背景</option></select><span id="count" class="fine"></span></div>{''.join(cards)}<h2 id="numbers">附录B · 图表与正文的原始数字</h2><p>保留指标与范围，禁止跨任务平均。误差线定义见各图；数字为论文原值，不是我们的复现实验。</p><table><thead><tr><th>论文</th><th>指标</th><th>条件</th><th>值</th><th>位置</th><th>分母／边界</th></tr></thead><tbody>{qrows}</tbody></table><div class="note">本报告为单一AI编码者完成的第一轮证据综合；未进行第二编码者逐格核查或代码复现。后续逐页精读应更新记录与结论，不将本版本标为“39篇全部精读完成”。</div></main></div><footer>EchoLoom · 公开论文链接与原创图表 · 本HTML可离线阅读，不加载第三方脚本</footer><script type="application/json" id="dataset">{dataset}</script><script>
const dataset=JSON.parse(document.querySelector('#dataset').textContent);const cards=[...document.querySelectorAll('.paper')];
function filter(){{const term=document.querySelector('#search').value.toLowerCase(),group=document.querySelector('#group').value,reading=document.querySelector('#reading').value;let n=0;for(const p of cards){{const show=(!term||p.dataset.search.toLowerCase().includes(term))&&(!group||p.dataset.group===group)&&(!reading||p.dataset.reading===reading);p.classList.toggle('hidden',!show);n+=show?1:0}}document.querySelector('#count').textContent=n+' / 39篇'}}
for(const id of ['search','group','reading'])document.querySelector('#'+id).addEventListener('input',filter);filter();
function openHash(){{const p=document.getElementById(location.hash.slice(1));if(p&&p.classList.contains('paper')){{for(const id of ['search','group','reading'])document.getElementById(id).value='';filter();p.querySelector('details').open=true;p.scrollIntoView()}}}}window.addEventListener('hashchange',openHash);openHash();
function download(obj,name){{const url=URL.createObjectURL(new Blob([JSON.stringify(obj,null,2)],{{type:'application/json;charset=utf-8'}}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}}document.querySelector('#downloadCoding').onclick=()=>download(dataset.coding,'EchoLoom-coding.json');document.querySelector('#downloadNumbers').onclick=()=>download(dataset.quantitative,'EchoLoom-quantitative.json');
</script></body></html>'''
(OUT/'EchoLoom-literature-report.html').write_text(page,encoding='utf-8')
(SRC/'index.html').write_text(page,encoding='utf-8')
for f in ['report.md','codebook.md','coding.json','quantitative.json']:shutil.copy2(SRC/f,OUT/f)
shutil.copytree(FIG,OUT/'figures',dirs_exist_ok=True)
# Standalone Markdown gets ordinary chart links; the repository source uses build markers.
md=(SRC/'report.md').read_text(encoding='utf-8')
for k in figures:md=md.replace(f'<!-- FIG:{k} -->',f'![{k}](figures/{k}.png)')
(OUT/'report.md').write_text(md,encoding='utf-8')
assert len(papers)==39 and len({p['id'] for p in papers})==39
assert all(q['paper'] in byid for q in quant)
assert len(figures)==9 and '<!-- FIG:' not in page
print(json.dumps({'papers':len(papers),'full_text_directed':sum(p['reading']=='全文定向核读' for p in papers),'figures':len(figures),'quantitative_records':len(quant),'output':str(OUT/'EchoLoom-literature-report.html')},ensure_ascii=False))
