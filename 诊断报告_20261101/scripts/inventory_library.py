from pathlib import Path
import os,re,json,hashlib,subprocess,collections,statistics,random
R=Path('D:/搭建'); O=Path('D:/诊断报告_20261101'); os.environ['TEMP']=os.environ['TMP']=str(O/'tmp')
def save(p,x): (O/p).write_text(x,encoding='utf-8')
def js(p,x): save(p,json.dumps(x,ensure_ascii=False,indent=2))
tracked=subprocess.check_output(['git','-C',str(R),'ls-files','-z']).decode('utf-8').split('\0'); tracked=[x for x in tracked if x]
files=[]; ignored=[]
for name in ['01_搭建框架_ACCOS','02_原版资料','03_运行资料','04_参考资料','05_Cline聊天记录','06_其他','07_新框架_v0']:
 for root,dirs,names in os.walk(R/name):
  for d in list(dirs):
   if d in {'.venv','node_modules','.git','__pycache__','.pytest_cache','.mypy_cache','.ruff_cache','workspace'} or d.startswith('.tmp'):
    ignored.append(str((Path(root)/d).relative_to(R))); dirs.remove(d)
  for n in names:
   p=Path(root)/n; rel=p.relative_to(R).as_posix(); b=p.read_bytes(); row={'path':rel,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'tracked':rel in tracked}
   try:
    t=b.decode('utf-8-sig'); row.update(lines=len(t.splitlines()),replacement=t.count('\ufffd'),nul=t.count('\0'))
   except UnicodeDecodeError: row['utf8']=False
   files.append(row)
for n in ['00_资料说明.md','README.md','.gitignore','.gitattributes']:
 p=R/n; b=p.read_bytes();files.append({'path':n,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'tracked':n in tracked})
js('tmp/inventory.json',{'files':files,'excluded':ignored,'tracked_count':len(tracked),'root_entries':[{'name':p.name,'directory':p.is_dir()} for p in R.iterdir()]})
save('scripts/文件清单.tsv','路径\t字节\tSHA256\tGit跟踪\n'+'\n'.join(f"{x['path']}\t{x['bytes']}\t{x['sha256']}\t{x['tracked']}" for x in files))
# local directory metadata only; no file body reads
local=[]
for p in (R/'小说').iterdir():
 row={'name':p.name,'directory':p.is_dir()}
 if p.is_dir():
  try:
   children=list(p.iterdir());row['immediate_files']=sum(x.is_file() for x in children);row['immediate_dirs']=sum(x.is_dir() for x in children);row['immediate_file_bytes']=sum(x.stat().st_size for x in children if x.is_file())
  except OSError as e: row['error']=str(e)
 else:row['bytes']=p.stat().st_size
 local.append(row)
js('tmp/local_directory.json',local)
p=R/'02_原版资料/原始资料/资料库.txt';text=p.read_text(encoding='utf-8-sig');lines=text.splitlines();heads=list(re.finditer(r'^###\s+(.+)$',text,re.M)); sections=list(re.finditer(r'^##\s+(.+)$',text,re.M)); entries=[]
for i,m in enumerate(heads):
 end=heads[i+1].start() if i+1<len(heads) else len(text); raw=text[m.end():end];base=raw.split('【运行层升级】')[0]; fields={}
 for f in re.finditer(r'【([^】]+)】\s*([\s\S]*?)(?=【[^】]+】|\Z)',base):fields[f.group(1)]=f.group(2).strip()
 sec=next((s.group(1) for s in reversed(sections) if s.start()<m.start()),'未识别'); rt=[]
 for j in re.finditer(r'```json\s*([\s\S]*?)```',raw):
  try:rt.append(json.loads(j.group(1)))
  except Exception:pass
 entries.append({'id':m.group(1).strip(),'line':text.count('\n',0,m.start())+1,'section':sec,'fields':fields,'base':base.strip(),'base_length':len(re.sub(r'\s','',base)),'raw_length':len(raw),'runtime':rt})
js('tmp/library_entries.json',entries)
counts=collections.Counter(x['section'] for x in entries); print(json.dumps({'files':len(files),'tracked':len(tracked),'library_heads':len(entries),'sections':len(counts),'heading_examples':list(counts.items())[:12],'runtime_jsons':sum(len(x['runtime']) for x in entries),'base_chars':sum(x['base_length'] for x in entries),'all_chars':len(text)},ensure_ascii=False))
js('tmp/library_stats.json',{'bytes':p.stat().st_size,'chars':len(text),'lines':len(lines),'entries':len(entries),'sections':len(counts),'section_counts':counts,'jsons':sum(len(x['runtime']) for x in entries)})
