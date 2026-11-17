"""Compare frozen network labels with source headings and legacy migrations."""
from collections import Counter, defaultdict
from contextlib import closing
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
import sqlite3
from typing import Iterator

from nw.materials.catalog import _connect
from nw.materials.endpoint_reviews import ENDPOINT_REVIEWS


POLICY = 'material-identity-v1'
_NUMBER = r'\d+(?:\.\d+)*'
_KEY = re.compile(rf'^({_NUMBER})[ _：:]+(.+)$')
_BLOCK = re.compile(r'^板块\s*(\d+)[ _：:]+(.+)$')
_BOLD = re.compile(rf'^\*\*({_NUMBER})[ _：:]+([^*]+)\*\*[ \t]*$')
_HEADING = re.compile(r'^#{3,6}[ \t]+(.+?)[ \t]*#*[ \t]*$')
_FENCE = re.compile(r'^\s*([`~]{3,})')
_EDGE_FIELDS = ('source','target','type')


@dataclass(frozen=True)
class Location:
    fragment_id: str
    path: str
    source_id: str
    file_sha256: str
    layer: str
    byte_start: int
    byte_end: int
    line_start: int
    line_end: int
    sha256: str
    form: str

    def to_dict(self) -> dict:
        return vars(self).copy()


def _structured_key(text: str) -> tuple[str,str] | None:
    match = _KEY.fullmatch(text)
    return (match[1],match[2].strip()) if match else None


def _position(row: sqlite3.Row, form: str, left: int = 0, right: int | None = None,
              first: int = 0, last: int | None = None) -> Location:
    if right is None:
        right = len(row['payload'])
    if last is None:
        last = row['line_end']-row['line_start']
    return Location(
        row['id'],row['path'],row['source_id'],row['file_sha256'],row['layer'],
        row['byte_start']+left,row['byte_start']+right,row['line_start']+first,row['line_start']+last,
        sha256(row['payload'][left:right]).hexdigest(),form,
    )


def _subheadings(row: sqlite3.Row, board: str) -> Iterator[tuple[str,str,Location]]:
    data = row['payload']
    offset = 0
    fence = None
    marks = []
    lines = data.splitlines(keepends=True)
    for i,line in enumerate(lines):
        text = line.decode('utf-8').rstrip('\r\n')
        if marker := _FENCE.match(text):
            marker_char = marker[1][0]
            if fence is None:
                fence = marker_char
            elif fence == marker_char:
                fence = None
        elif fence is None:
            if match := _BOLD.fullmatch(text):
                number,title,form = match[1],match[2].strip(),'bold_subheading'
            elif match := _HEADING.fullmatch(text):
                title = match[1].strip()
                key = _structured_key(title)
                number,title = key if key else ('',title)
                form = 'numbered_subheading' if key else 'unnumbered_subheading'
                if _BLOCK.fullmatch(title):
                    offset += len(line)
                    continue
            else:
                offset += len(line)
                continue
            if not number or number.startswith(board+'.'):
                marks.append((offset,i,number,title,form))
        offset += len(line)
    for i,(left,start,number,title,form) in enumerate(marks):
        right,stop = marks[i+1][:2] if i+1 < len(marks) else (len(data),len(lines))
        yield number,title,_position(row,form,left,right,start,stop-1)


def _library(connection: sqlite3.Connection) -> tuple[dict,dict,dict,dict]:
    labels: dict = defaultdict(list)
    numbers: dict = defaultdict(list)
    boards: dict = defaultdict(list)
    fragments = {}
    section_names = set()
    query = """
        SELECT f.*, s.path, s.layer, s.file_sha256 FROM fragments f JOIN sources s ON s.id=f.source_id
        WHERE s.family='library' AND s.layer IN ('baseline','historical')
        AND f.kind IN ('library_entry','library_block') ORDER BY s.path,f.byte_start
    """
    for row in connection.execute(query):
        if sha256(row['payload']).hexdigest() != row['sha256']:
            raise ValueError(f"Material fragment hash mismatch: {row['id']}")
        if row['kind']=='library_block' and (match := _BLOCK.fullmatch(row['key'] or '')):
            key = (match[1],match[2].strip())
            location = _position(row,'board_heading')
            if row['layer']=='baseline':
                boards[key[0]].append(row)
                fragments[location.fragment_id] = location
            labels[key].append(location)
            numbers[key[0]].append((key[1],location))
            for number,title,sub in _subheadings(row,key[0]):
                if row['layer']=='baseline':
                    fragments[f'{sub.fragment_id}@{sub.line_start}'] = sub
                    named = f'{sub.fragment_id}#{title}'
                    if named in section_names:
                        fragments.pop(named,None)
                    else:
                        fragments[named] = sub
                        section_names.add(named)
                if number:
                    labels[number,title].append(sub)
                    numbers[number].append((title,sub))
        elif key := _structured_key(row['key'] or ''):
            location = _position(row,'entry_heading')
            if row['layer']=='baseline':
                fragments[location.fragment_id] = location
            labels[key].append(location)
            numbers[key[0]].append((key[1],location))
    return labels,numbers,boards,fragments


def _read_contract(path: Path) -> tuple[dict,dict]:
    data = path.read_bytes()
    content = json.loads(data.decode('utf-8-sig'))
    if not isinstance(content,dict):
        raise ValueError(f'Expected identity contract object: {path.name}')
    return content,{'file':path.name,'sha256':sha256(data).hexdigest()}


def _aliases(document: dict) -> dict:
    aliases: dict = defaultdict(set)
    exact = document.get('exact_alias',{})
    similar = document.get('unresolved_similar',[])
    if not isinstance(exact,dict) or not isinstance(similar,list):
        raise ValueError('Invalid legacy alias sections')
    for key,value in exact.items():
        if not isinstance(value,str):
            raise ValueError('Legacy exact_alias must map labels to labels')
        aliases[key].add(value)
        aliases[value].add(key)
    for group in similar:
        if not isinstance(group,dict):
            raise ValueError('Invalid legacy similarity group')
        names = group.get('names')
        if not isinstance(names,list) or not all(isinstance(x,str) for x in names):
            raise ValueError('Legacy similarity group requires names')
        for key in names:
            aliases[key].update(name for name in names if name != key)
    return aliases


def _network(connection: sqlite3.Connection) -> tuple[dict,dict]:
    endpoints: dict = defaultdict(list)
    dynamic: dict = defaultdict(list)
    query = """
        SELECT f.*,s.family,s.path,s.layer,s.file_sha256 FROM fragments f JOIN sources s ON s.id=f.source_id
        WHERE s.layer='baseline' AND s.family IN ('static','dynamic') AND f.kind='network_edge'
        ORDER BY s.path,f.byte_start
    """
    for row in connection.execute(query):
        if sha256(row['payload']).hexdigest() != row['sha256']:
            raise ValueError(f"Material fragment hash mismatch: {row['id']}")
        edge = json.loads(row['payload'])
        ref = {'fragment_id':row['id'],'key':row['key'],'path':row['path'],
               'source_id':row['source_id'],'file_sha256':row['file_sha256'],
               'sha256':row['sha256'],'line_start':row['line_start'],'family':row['family']}
        for side in ('source','target'):
            if isinstance(edge.get(side),str) and edge[side]:
                endpoints[edge[side]].append(dict(ref,side=side))
        if row['family']=='dynamic' and isinstance(edge.get('id'),str):
            signature = tuple(edge.get(field) for field in _EDGE_FIELDS)
            dynamic[edge['id']].append((signature,ref))
    return endpoints,dynamic


def _context_hits(label: tuple[str,str], boards: dict) -> list[dict]:
    number,title = label
    board = number.split('.')[0]
    if len(title) < 2:
        return []
    term = title.encode('utf-8')
    hits = []
    for row in boards.get(board,[]):
        offset = 0
        for i,line in enumerate(row['payload'].splitlines(keepends=True)):
            if term in line:
                hit = _position(row,'same_board_text',offset,offset+len(line),i,i)
                hits.append(hit.to_dict())
                if len(hits)==4:
                    return hits
            offset += len(line)
    return hits


def _endpoint(label: str, edges: list, labels: dict, numbers: dict, boards: dict, aliases: dict,
              fragments: dict) -> dict:
    key = _structured_key(label)
    matching = labels.get(key,[])
    current = [x for x in matching if x.layer=='baseline']
    previous = [x for x in matching if x.layer=='historical']
    related = sorted(aliases.get(label,[]))
    alias_locations = [{'label':other,'locations':[ref.to_dict() for ref in labels.get(_structured_key(other),[])]}
                       for other in related]
    number = key[0] if key else ''
    comparable = [{'label':number+'_'+name,'location':ref.to_dict()}
                  for name,ref in numbers.get(number,[]) if ref.layer=='baseline' and (number,name)!=key]
    context = _context_hits(key,boards) if key and not current else []
    if current:
        hashes = {x.sha256 for x in current}
        if len(hashes)>1:
            state = 'ambiguous_heading'
        elif all(x.form in {'bold_subheading','numbered_subheading'} for x in current):
            state = 'current_subheading'
        else:
            state = 'current_heading'
    elif previous:
        state = 'historical_heading'
    elif related:
        state = 'alias_review'
    elif comparable:
        state = 'number_review'
    elif context:
        state = 'context_review'
    else:
        state = 'missing'
    review = None
    decision = ENDPOINT_REVIEWS.get(label)
    if decision is not None:
        target = fragments.get(decision.target)
        if target is not None and target.sha256==decision.sha256:
            if decision.heading is not None:
                target = fragments.get(f'{decision.target}#{decision.heading}')
            if target is not None:
                review = {'status':decision.status,'reason':decision.reason,'location':target.to_dict()}
                state = decision.status
        if review is None:
            review = {'status':'source_changed','reason':'核读位置或片段哈希已变化，重新裁定。'}
    return {'label':label,'status':state,'locations':[x.to_dict() for x in current+previous],
            'same_number':comparable,'legacy_aliases':alias_locations,'same_board_occurrences':context,
            'review':review,'edge_references':edges,'execution_allowed':False}


def _migrations(document: dict, dynamic: dict) -> list[dict]:
    rows = document.get('migrations')
    if not isinstance(rows,list):
        raise ValueError('Invalid dynamic migration section')
    fields = ('old_id','new_id',*_EDGE_FIELDS)
    for row in rows:
        if not isinstance(row,dict) or not all(isinstance(row.get(k),str) and row[k] for k in fields):
            raise ValueError('Invalid dynamic migration row')
    old_counts = Counter(row['old_id'] for row in rows)
    new_counts = Counter(row['new_id'] for row in rows)
    result = []
    for i,row in enumerate(rows):
        old,new = row['old_id'],row['new_id']
        signature = tuple(row[field] for field in _EDGE_FIELDS)
        targets = dynamic.get(new,[])
        occupants = dynamic.get(old,[])
        if old_counts[old]>1 or new_counts[new]>1 or len(targets)>1:
            state = 'ambiguous'
        elif not targets:
            state = 'target_missing'
        elif targets[0][0] != signature:
            state = 'signature_conflict'
        else:
            state = 'target_verified'
        result.append({
            'legacy_locator':f'/migrations/{i}',**{k:row[k] for k in fields},'status':state,
            'current_targets':[r for _,r in targets],
            'old_id_reused':any(current != signature for current,_ in occupants),
            'current_old_id_occupants':[r for _,r in occupants],
        })
    return result


def audit_identities(workspace: Path, alias_file: Path, migration_file: Path) -> dict:
    aliases,alias_ref = _read_contract(alias_file)
    migrations,migration_ref = _read_contract(migration_file)
    alias_links = _aliases(aliases)
    with closing(_connect(workspace,write=False)) as connection:
        connection.execute('BEGIN')
        labels,numbers,boards,fragments = _library(connection)
        endpoints,dynamic = _network(connection)
    nodes = [_endpoint(label,refs,labels,numbers,boards,alias_links,fragments) for label,refs in sorted(endpoints.items())]
    moves = _migrations(migrations,dynamic)
    return {'policy':POLICY,'legacy_alias_file':alias_ref,'legacy_migration_file':migration_ref,
            'endpoint_counts':dict(Counter(x['status'] for x in nodes)),
            'migration_counts':dict(Counter(x['status'] for x in moves)),
            'old_ids_reused':sum(x['old_id_reused'] for x in moves),'endpoints':nodes,'migrations':moves}


def edge_identity(workspace: Path, source: dict) -> list[dict]:
    if source['family'] not in {'static','dynamic'} or source['layer']!='baseline':
        return []
    path = workspace/'materials'/'F2_网络身份对账.json'
    if not path.is_file():
        return []
    report = json.loads(path.read_text(encoding='utf-8-sig'))
    if report.get('policy') != POLICY:
        raise ValueError('Unsupported network identity report')
    result = []
    for endpoint in report['endpoints']:
        for ref in endpoint['edge_references']:
            if (ref['fragment_id'],ref['sha256'],ref['file_sha256']) == (
                source['fragment_id'],source['fragment_sha256'],source['file_sha256']
            ):
                result.append({'side':ref['side'],'label':endpoint['label'],'status':endpoint['status'],
                               'locations':endpoint['locations'],'review':endpoint['review']})
    return sorted(result,key=lambda item:item['side'])
