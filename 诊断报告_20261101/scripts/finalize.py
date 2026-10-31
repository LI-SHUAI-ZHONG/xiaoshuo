from pathlib import Path
import json,collections,hashlib,re,os,zipfile
O=Path('D:/诊断报告_20261101');R=Path('D:/搭建');os.environ['TEMP']=os.environ['TMP']=str(O/'tmp')
lib=json.loads((O/'tmp/library_final_stats.json').read_text(encoding='utf8'));inv=json.loads((O/'tmp/core_inventory.json').read_text(encoding='utf8'));counts=json.loads((O/'tmp/audit_counts.json').read_text(encoding='utf8'))
# Scope the 8400-style statement to actual SOURCE tables rather than all nested tables.
d=json.loads((O/'tmp/type_network_parsed.json').read_text(encoding='utf8'));per=[]
def collect(x,out):
 if isinstance(x,dict):
  for k,v in x.items():
   if k=='not_guaranteed':
    if isinstance(v,list):out.extend(z for z in v if isinstance(z,str))
    elif isinstance(v,str):out.append(v)
   else:collect(v,out)
 elif isinstance(x,list):
  for v in x:collect(v,out)
for b in d['blocks']['类型连接']:
 a=[];collect(b['data'],a)
 if a:per.append((b['name'],b['line'],len(a),len(set(a))))
with(O/'03a_规则与组合追踪.md').open('a',encoding='utf8')as h:
 h.write('\n\n## 按SOURCE复算不能保证字段\n\n|SOURCE|行|字符串出现|精确去重|\n|---|---:|---:|---:|\n')
 for n,l,total,uniq in per:h.write(f'|{n}|{l}|{total}|{uniq}|\n')
# Split oversized supporting exclusion inventory; keep first filename as index.
p=O/'scripts/目录排除清单.txt';txt=p.read_text(encoding='utf8');parts=[];buf=''
for line in txt.splitlines(True):
 if len((buf+line).encode())>55000:parts.append(buf);buf=''
 buf+=line
parts.append(buf)
if len(parts)>1:
 for i,b in enumerate(parts,1):(O/f'scripts/目录排除清单_{i:02}.txt').write_text(b,encoding='utf8')
 p.write_text('完整排除目录清单见同目录 目录排除清单_01.txt 起。\n',encoding='utf8')
findings=[
'当前地图已更新至11月1日并登记07新框架，任务提供的旧地图状态已过时（00_资料说明.md:4、24；01）。',
'资料库全量识别1206个出现位置、159个板块编号；模板剥离后的保守代理量为132741字符，不能把文件体积当独有知识（02）。',
'资料库已包含场景精选、文风、篇幅与推进规则；问题包含深度不均和错误转译，不能统一写成“全无”（资料库.txt:189728、197405、100815；02）。',
'78–80正文仍缺；多个设计文件与融合清单有大小却全NUL，无法解析，损坏原因未核实（01/06）。',
'710类型关键区分字段全部空，425子类定义仅回指父类；玄幻直接表达适配为零（类型系统.txt:3095、20889；03）。',
'动态1824边中1341边派生自静态网，锚点实数1790；这些主要适合检索/提示，实测写作收益尚未证明（04）。',
'现存旧管道3888行，正文阶段只消费beat.prose；缺文时形成请求，未核实有当前自动生成入口（执行管道.py:2799–2817；05）。',
'启动模块使用main局部snapshot_path，存在静态可确定的作用域缺陷；本轮未运行复现（执行管道.py:1702–1704、3592；05）。',
'23份留存正文存在同文复用和标签泄漏；历史四类原因贡献比例无法估计，单次盲测不能证明规则无效（07）。',
'ACCOS、旧管道、v0是不同路线；v0可作可复核实验起点，但工程测试和单次冒烟不等于长篇商业质量（08/10）。'
]
s=['# 00 P0诊断总览','\n报告范围：现存仓库D:/搭建。源资料只读；仅00_资料说明.md按授权登记/补记。没有运行写作模型、Ollama、源项目或测试，也未下载、提交、推送。报告在D:/诊断报告_20261101；所有统计及生成脚本在scripts。','\n## 最重要的发现']
s += [f'{i}. {x}'for i,x in enumerate(findings,1)]
s+=['\n## 假设速览','|假设|判断|关键限制|','|---|---|---|','|H1偏薄|部分证实|有有效方法；独有字数是算法代理|','|H2用法不当|部分证实|现存实现和8月历史必须分开|','|H3缺关键资料|部分证实|并非所有文风/节奏规则都无|','|H4网络降级|部分证实|支持检索化；未证明整体无收益|','|H5治理重质量轻|部分证实|有审稿门，文学近似薄弱；v0已有修订|','|H6强模型最小材料够用|无法判断|一次非严格盲测不足|','|H7规划弱|部分证实|有卷方向与预算约束，生成能力不足|','|H8资料全面|部分证实|覆盖面广、深度与验证不足|','\n## 覆盖率总表','全量解析指结构/字段遍历；人工为本轮模型对原文片段审读，不是作者验收。未读比例按各自抽样分母计算，不是字节覆盖。','|资料|全量解析|人工核心审读|未逐条审读|','|---|---|---|',f'|资料库|1206出现/159板块、字段与运行JSON|{lib["reviewed"]}条片段，含随机20|{lib["unread_percent"]}%|','|类型系统|449 SOURCE；710本体/118适配/4200组合字段|20本体随机+定向窗口|本体97.18%；其他未量化|','|类型连接|36 SOURCE、四子库及子表字段|20静态总表随机+定向|静态总表99.36%；其他未量化|','|静态网络|1341边全量|20随机+生成/消费代码|98.51%|','|动态网络|1824边全量并比对派生|20随机+定向|98.90%|','|锚点网络|1790状态行全量|20随机+定向|98.88%|','|脚本|207文件，AST函数/调用索引|核心管道和关键脚本|其余未逐函数语义核验|','|历史|23正文全扫；23 Cline消息结构|64消息片段+定向|保守消息字符99.720%|','|源设计文档|标题/步骤结构全扫|创作搭建/改进资料定向窗口|字符99.296%/98.080%|','\n## 抽样与方案','120条评分全部有出处和理由；可用率指评分2占样本，资料库55%、类型系统0%、类型连接0%、静态40%、动态5%、锚点40%。这些是抽样可执行性判断，抽样单位不同、未做场景增益实测，不可推断全库效果。见09。','六层方案可作为组织框架，必须补上长篇状态提交、角色/读者知识差、跨章伏笔兑现、重规划、预算和恢复。建议依托v0验证作者认可的连续场景，再扩展资料规模；详见10。','\n## 文件目录与阅读顺序','先读本文件及01；然后02资料库、03类型与连接（含03a）、04三网、05管道、06设计、07历史、08框架；最后09抽样、10方案、11缺口。01a/b文件清单，02a错误候选，05A–F脚本/函数/参数/门/提示词/模块表，06A字段与完整性均为分段附录。','scripts为复算工具；tmp为大体积本地解析中间件，**不适合直接上传Claude**。根目录报告与JSONL每片不超过60KB，本文件不超过8KB。','\n## 未完成的核实','未逐条读完全部资料/全部Cline对话；未取得全部历史模型请求与对应代码版本；未恢复NUL；未核实本地小说与副本内容同一性、所有孤立文件和跨库引用；未运行复现或做真实质量实验。以上均明确保留，不将诊断交付完成称为源系统修复或商业质量达标。']
body='\n'.join(s)+'\n';assert len(body.encode())<=8000;(O/'00_总览.md').write_text(body,encoding='utf8')
# source integrity against initial snapshot except author-authorized map registration
changes=[]
for x in inv:
 if x['path']=='00_资料说明.md':continue
 p=R/x['path'];now=hashlib.sha256(p.read_bytes()).hexdigest()if p.exists()else'MISSING'
 if now!=x['sha256']:changes.append(x['path'])
assert not changes,changes
reports=sorted(p for p in O.iterdir()if p.is_file()and p.name!='进度.md');overs=[str(p)for p in reports if p.stat().st_size>60000];assert not overs,overs
required=['00_总览.md','01_仓库地图核对.md','02_资料库.md','03_类型系统与类型连接.md','04_三种网络.md','05_执行管道.md','06_创作设计资料.md','07_运行历史与失败归因.md','08_框架与源文档.md','09_抽样审计.md','09_抽样数据.jsonl','10_对作者方案的评价.md','11_缺口与待决问题.md'];assert all((O/n).exists()for n in required)
verification={'baseline_source_files_checked':len(inv)-1,'unexpected_source_changes':changes,'report_files':len(reports),'overview_bytes':(O/'00_总览.md').stat().st_size,'upload_files_over_60000':overs,'sample_rows':120,'limitations':'结构全扫及定向/随机片段审读；非全文语义审读，非真实模型运行验证'}
(O/'tmp/final_verification.json').write_text(json.dumps(verification,ensure_ascii=False,indent=2),encoding='utf8')
manifest='# 交付文件与大小\n\n|文件|字节|\n|---|---:|\n'+'\n'.join(f'|{p.name}|{p.stat().st_size}|'for p in reports)+'\n\n统计脚本见scripts，解析结果见tmp。\n'
(O/'交付清单.md').write_text(manifest,encoding='utf8')
# Replace noisy intermediate event log with concise resumable final status.
old=(O/'进度.md').read_text(encoding='utf8');(O/'tmp/进度历史.txt').write_text(old,encoding='utf8')
(O/'进度.md').write_text('# P0诊断进度\n\n状态：报告交付完成；全部要求的编号主报告已生成。\n\n已完成：源地图登记、目录及完整性基线、六大结构全量扫描、核心代码静态解析、历史结构与片段审读、120条随机评分、H1–H8及六层方案评价、文件大小及源哈希核对。\n\n核验：源基线意外变化为零（00说明授权补记除外）；00小于8KB；上传报告每片小于60KB。详见交付清单.md及tmp/final_verification.json。\n\n未完成的核实：逐条语义全读、NUL恢复、历史完整调用因果、所有跨库引用及孤立性、真实模型与运行复现、商业质量验证；具体边界见00/11。\n\n下一步：作者先阅读00及01，再按02–08和09–11分批交Claude。重构/修复须另立任务，本轮没有改源代码。\n',encoding='utf8')
with(R/'00_资料说明.md').open('a',encoding='utf8')as h:h.write('\n- P0诊断报告交付完成（2026-11-01）：D:\\诊断报告_20261101\\已生成00–11主报告、分片附录、120条抽样数据和scripts统计脚本；仅结构全量扫描及定向/随机审读，非全仓逐字阅读。未恢复NUL、未运行源项目/测试/模型、未下载/提交/推送；源基线哈希复核无非授权变化。详细覆盖与未核实项见00/11。桌面ZIP由报告收尾脚本生成并校验；本说明只记交付范围，不把诊断当源问题修复。\n')
# Desktop path explicit from OS inventory; user requested this exception to D-only reports.
desktop=Path(os.environ['USERPROFILE'])/'Desktop';z=desktop/'诊断报告_20261101.zip';assert not z.exists(),'目标zip已存在，禁止覆盖'
with zipfile.ZipFile(z,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6)as zz:
 for p in O.rglob('*'):
  if p.is_file():zz.write(p,arcname='诊断报告_20261101/'+p.relative_to(O).as_posix())
with zipfile.ZipFile(z)as zz:assert zz.testzip()is None
with(O/'进度.md').open('a',encoding='utf8')as h:h.write('\n打包：桌面诊断报告_20261101.zip已创建并通过ZIP完整性校验。\n')
print(json.dumps({'verification':verification,'zip':str(z),'zip_bytes':z.stat().st_size,'main_reports':[(n,(O/n).stat().st_size)for n in required]},ensure_ascii=False))
