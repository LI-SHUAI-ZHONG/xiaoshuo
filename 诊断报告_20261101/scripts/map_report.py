from pathlib import Path
import json,re,collections,statistics
O=Path('D:/诊断报告_20261101');R=Path('D:/搭建');iv=json.loads((O/'tmp/inventory.json').read_text(encoding='utf8'));allf=iv['files'];f=[x for x in allf if not any(a in x['path'].split('/') for a in ['.data','.next','.cache','dist','build'])];(O/'tmp/core_inventory.json').write_text(json.dumps(f,ensure_ascii=False,indent=2),encoding='utf8')
s=['# 01 仓库地图核对','\n## 口径与覆盖','全量枚举了分类目录中的文件，对未排除的文件读取字节、计算SHA256，并对可解码UTF-8文件扫描NUL和替换符。明确排除的目录见scripts/目录排除清单.txt。首轮还读到了ACCOS的本地基础设施依赖与前端构建文件，后续从正文统计中排除 .data/.next/.cache/dist/build；这些不是小说知识。没有遍历根目录的全部依赖和历史缓存，没有整体读取小说原工作目录。','本报告中的“人工”是模型逐条审读，不是作者人工验收。文件存在/哈希不等于已理解正文；全仓库语义覆盖率未核实。',f'首轮文件字节扫描 {len(allf)} 个；过滤后的资料/代码及配置文件 {len(f)} 个。git ls-files 返回 {iv["tracked_count"]} 个路径（含根下其他历史区域，不能等同本报告范围）。','\n## 索引与实际差异','- 当前00_资料说明.md:4、:24、:48已更新至2026-11-01并列出07新框架；用户提供的“10月29日、未登记07”已过时。','- 创作资料入口.md:14–19仍使用原始资料/与网络完整数据/相对路径；分类副本实际位于02_原版资料，运行脚本位于03_运行资料。不能在分类仓库根直接假定旧命令可运行。','- 入口声明是用途与规范，不能证明文件真实被运行读取。静态调用和历史证据分别见05、07；本次禁止运行管线，未取得新的运行文件访问追踪。','\n## 实际分类数量（字节）','|目录|文件数|字节|非零但全NUL|零字节|','|---|---:|---:|---:|---:|']
for k in sorted(set(x['path'].split('/')[0] for x in f)):
 a=[x for x in f if x['path'].split('/')[0]==k];s.append(f'|{k}|{len(a)}|{sum(x["bytes"] for x in a)}|{sum(x.get("nul",0)==x["bytes"] and x["bytes"]>0 for x in a)}|{sum(x["bytes"]==0 for x in a)}|')
s+=['\n## 空内容与损坏清单','“全零字节文件”需区分大小为零和文件内容全为0x00；后者有文件长度，但无法当作正常JSON/Markdown使用。','|路径|字节|判断|','|---|---:|---|']
for x in f:
 if x['bytes']==0 or x.get('nul',0)==x['bytes']:s.append(f'|{x["path"]}|{x["bytes"]}|'+('零长度' if not x['bytes'] else '全NUL损坏/占位；不能判定原文为何丢失')+'|')
d=collections.defaultdict(list)
for x in f:
 if x['bytes'] and x.get('nul',0)!=x['bytes']:d[x['sha256']].append(x['path'])
dups=[a for a in d.values() if len(a)>1];s+=['\n## 完全相同的文件（SHA256）',f'发现{len(dups)}组非空、非全NUL重复；同一LICENSE/占位配置的复用不必然是错误。']
for a in dups:s.append('- '+'；'.join(a))
s+=['\n## 乱码与孤立性','可解码UTF-8不保证文本无乱码；类型文件开头的损坏字符与字段残缺详见03，资料库错括号详见02。没有引用并不等于孤立：动态路径拼装、配置加载、CLI手动执行都会绕过字面引用检索。本次没有把“未找到字符串引用”冒充死文件证明；孤立文件的严格清单未核实。','\n## 本地小说目录：只做目录级核对','只枚举根目录及各一级子目录的直接子项和大小，不读文件正文、不做递归哈希。它具有.codegraph、资料版本、资料索引、验收等目录；分类副本有额外写作实验及框架目录。这说明不是同一个布局，不能据目录名认定内容等同或副本最新。','|原工作目录一级项|文件夹|直接文件数|直接子目录数|直接文件字节|','|---|---|---:|---:|---:|']
for x in json.loads((O/'tmp/local_directory.json').read_text(encoding='utf8')):s.append(f'|{x["name"]}|{x["directory"]}|{x.get("immediate_files","—")}|{x.get("immediate_dirs","—")}|{x.get("immediate_file_bytes",x.get("bytes","—"))}|')
s+=['\n## 文件清单与大小','附录01a起逐项列出过滤后文件名和字节数；脚本与tmp/inventory.json保存原始扫描证据。未扫描的根目录区域不纳入“无重复/无损坏”的判断。']
(O/'01_仓库地图核对.md').write_text('\n'.join(s),encoding='utf8')
chunks=[];part='# 文件清单（01附录）\n\n路径相对于D:/搭建；大小单位为字节。\n\n|路径|字节|\n|---|---:|\n'
for x in f:
 row=f'|{x["path"]}|{x["bytes"]}|\n'
 if len((part+row).encode())>55000:chunks.append(part);part='# 文件清单（续）\n\n|路径|字节|\n|---|---:|\n'
 part+=row
chunks.append(part)
for i,c in enumerate(chunks):(O/f'01{chr(97+i)}_文件清单.md').write_text(c,encoding='utf8')
(O/'scripts/文件清单.tsv').write_text('完整机器清单见 ../tmp/inventory.json；供上传的分段文件清单见 ../01a_文件清单.md 起。\n扫描脚本：inventory_library.py。\n',encoding='utf8')
(O/'scripts/目录排除清单.txt').write_text('\n'.join(iv['excluded'])+'\n报告另外过滤：.data/.next/.cache/dist/build\n根目录仅读取说明、README与Git属性/忽略配置。',encoding='utf8')
with (O/'进度.md').open('a',encoding='utf8')as h:h.write('\n已完成：01仓库地图及分段文件清单；目录扫描基线已保存。\n')
print({'core_files':len(f),'appendices':len(chunks),'report_bytes':(O/'01_仓库地图核对.md').stat().st_size})
