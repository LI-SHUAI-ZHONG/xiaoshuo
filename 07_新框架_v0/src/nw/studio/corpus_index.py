"""Literal source boundaries and explicit coverage, independent of model opinions."""
import re

from nw.studio.corpus_catalog import OVERVIEW


def source_units(content: str) -> list[dict]:
    headings = []
    pattern = r'(?m)^[ \t]*(?:#{1,6}[ \t]+[^\r\n]+|第[〇零一二三四五六七八九十百千万两\d]+[卷部篇章回节][^\r\n]*)'
    for match in re.finditer(pattern, content):
        title = match[0].strip()
        plain = title.lstrip('#').strip()
        level = 'volume' if re.match(r'^第[〇零一二三四五六七八九十百千万两\d]+[卷部篇]', plain) else 'chapter'
        headings.append({'start': match.start(), 'title': title, 'level': level})
    root = {'id': 'book', 'level': 'book', 'title': '全书 / 已导入文本', 'parent_id': None,
            'start': 0, 'end': len(content), 'boundary_basis': 'source_file', 'summary': ''}
    rows = [root]
    volumes = [h for h in headings if h['level'] == 'volume']
    for index, heading in enumerate(volumes):
        rows.append({'id': f'v{index+1:04}', 'level': 'volume', 'title': heading['title'], 'parent_id': 'book',
            'start': heading['start'], 'end': volumes[index+1]['start'] if index+1<len(volumes) else len(content),
            'boundary_basis': 'source_heading', 'summary': ''})
    containers = ([{'id':'book','start':0,'end':volumes[0]['start']}] if volumes and volumes[0]['start'] else [])
    containers += [row for row in rows if row['level']=='volume'] if volumes else [root]
    count = 0
    for parent in containers:
        children = [h for h in headings if h['level']=='chapter' and parent['start']<=h['start']<parent['end']]
        if not children or children[0]['start']>parent['start']:
            children.insert(0, {'start':parent['start'],'title':'未标章文本（边界待核）','level':'chapter'})
        for index, heading in enumerate(children):
            end = children[index+1]['start'] if index+1<len(children) else parent['end']
            if end<=heading['start']: continue
            count += 1
            rows.append({'id':f'c{count:05}','level':'chapter','title':heading['title'],'parent_id':parent['id'],
                'start':heading['start'],'end':end,'boundary_basis':'analyst_inference' if '边界待核' in heading['title'] else 'source_heading',
                'summary':''})
    return rows


def empty_document(content: str, extent: str = 'unknown', note: str = '') -> dict:
    return {'schema_version':1, 'source_extent':{'status':extent,'note':note},
        'overview':{key:'' for key in OVERVIEW}, 'units':source_units(content),
        'characters':[],'events':[],'threads':[],'links':[],'evidence':[],'domains':[],'uncertainties':[]}


def source_spans(units: list[dict], chunk_chars: int) -> list[dict]:
    return [{'unit_id':unit['id'],'start':start,'end':min(start+chunk_chars,unit['end'])}
            for unit in sorted(units,key=lambda r:r['start']) if unit['level']=='chapter'
            for start in range(unit['start'],unit['end'],chunk_chars)]


def range_coverage(ranges: list[dict], length: int) -> dict:
    merged = []
    for start,end in sorted((r['start'],r['end']) for r in ranges):
        if not 0<=start<end<=length: raise ValueError('阅读范围越界')
        if merged and start<=merged[-1][1]: merged[-1][1]=max(end,merged[-1][1])
        else: merged.append([start,end])
    covered = sum(end-start for start,end in merged)
    return {'characters':covered,'total':length,'fraction':covered/length if length else 0,
            'ranges':merged,'complete_imported_text':covered==length and length>0}
