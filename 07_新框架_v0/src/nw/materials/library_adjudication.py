"""Source-pinned library and anchor contracts, distinct from manual approval.

Only a complete original owner can be offered. Its individual fields remain
context; a populated template, numbering match, or upgrade is not a contract.
This module reads the catalog connection and never writes to it.
"""
from collections import defaultdict
from bisect import bisect_right
from hashlib import sha256
import re
import sqlite3

from nw.materials.units import units_for_fragment
from nw.materials.stage_workflow import stage_profile


_PINNED = {
    'library': '1e4c7720fbc745ab952cd749c6faad03cff26c9a8e3f9bce5c4c5a6da91a36ed',
    'anchors': '9b7ea71e53613a453fe71fa0a862411f65f22328a38ee7b97db7fd5bab7be759',
}
# These checks name exact draft ranges. Match only the original subsection
# bytes so a same-named entry or a later edition cannot inherit the range.
_SCOPED_LIBRARY_CHECKS = {
    ('板块91 场景结构检查#场景篇幅', '70feedd2e38070e74ea5418fc5d582dd2f958b55a873ac067602b11ef609fee7'):
        {'kind': 'chapter', 'scene_indices': [1, 2, 3], 'metric': 'third_scene_length'},
    ('板块100 节奏与呼吸检查#连续节奏检查', 'ae16678de64a08e48e88889461d534e623422ab1cf0c21f2e9c2126e6dfe4c63'):
        {'kind': 'cross_chapter', 'consecutive': True, 'chapter_count': 3},
    ('板块100 节奏与呼吸检查#重章间隔', '2f815fa538b64d76e1d27e21c4054f17cbc1c41ef8b734a99f96e088a72dc957'):
        {'kind': 'cross_chapter', 'consecutive': True},
    ('板块100 节奏与呼吸检查#情绪承接', '54eb40da70b917c3b4d6166c8816141ea375c697f085c637d55501197304ad5f'):
        {'kind': 'cross_chapter', 'consecutive': True, 'chapter_count': 2, 'chapter_boundary_sentences': True},
}
_ROOTS = {'library_entry', 'library_block', 'anchor', 'embedded_entry', 'embedded_block'}
_CATEGORIES = {
    'definition': 'definition', 'instruction': 'directives', 'condition': 'conditions',
    'exception': 'exceptions', 'check': 'checks', 'prohibition': 'exclusions',
    'alternative': 'alternatives', 'correction': 'corrections', 'dependency': 'dependencies',
    'grade': 'grades', 'variation': 'variations', 'mapping': 'mappings', 'note': 'notes',
    'tag': 'tags', 'identity': 'identities',
}
_FIELD = re.compile(r'^\s*(?:[【\[（(][^】\]）)》\n]+[】\]）)》]|\*\*[^*\n]+\*\*[:：])')
_HEADING = re.compile(r'(?m)^#{2,6}[ \t]+([^\r\n]+)|^\*\*(\d+\.\d+[ \t]+[^*\r\n]+)\*\*')
_NUMBER = re.compile(r'^(?:板块\s*)?(\d+)(?=[. _：:]|$)')
_FOREIGN = re.compile(r'(?m)^-\s*\*\*板块\*\*[:：]\s*(\d+(?:\.\d+)?)')
_BOILERPLATE = re.compile(
    r'^(?:在设计阶段规划.+的应用方式和位置|在写作阶段按.+规则逐条执行|'
    r'如不合格，重新审视.+的运用是否到位，调整后重新检查|'
    r'.+是否在文中得到体现，读者能否感知到该技法的效果|'
    r'.+相关禁用表达|使用符合规则的替代描写方式|用动作或直接叙述替代|按流程执行)$')
_OPERATION = re.compile(r'必须|不能|不可|至少|不超过|须|要求|规则|检查方法|检查内容|'
                        r'检查频率|判定|每[一二三四五六七八九十\d章场]|\d+[.、]|[①②③④⑤⑥⑦⑧⑨]')
_VAGUE = re.compile(r'^(?:特殊(?:事件触发|条件满足|触发条件|事件|攻击)|升级条件满足|突破条件满足|无|未知)$')
_UNSUPPORTED = {'brief', 'preflight', 'continuity', 'legacy', 'example', 'type_identity'}
_EVIDENCE = {
    'world': '给出项目中的规则、起点、限制、代价及其行动后果；正文须能定位规则实际生效的表现。',
    'character': '给出具体人物、动机或关系前状态、行动选择和后果；用动作或台词解释原规则如何成立。',
    'plot': '给出章场目标、因果节拍、选择与代价、结果和后续承接；引用造成变化的正文。',
    'opening': '给出开篇位置、承诺和进入冲突的具体安排；引用首段或开篇行动证明承诺被建立。',
    'scene': '给出本场的空间、目标、阻力、行动与结果；引用相应节拍并解释因果。',
    'expression': '给出适用段落、视角权限和预期语言效果；引用足够完整的句段解释手法实际效果。',
    'knowledge': '列明人物、叙述者、读者各自在何时知道或误判什么；引用获取证据及披露边界的正文。',
    'type_expression': '明确作者采用的类型承诺和适用边界；引用场景如何兑现相应期待。',
    'prose_review': '冻结当前稿，逐条引用有意义的正文句段并解释判断；单稿无法证明的跨章要求须标未核。',
    'scope_review': '冻结原判据指定的整章、跨章或全书稿件范围，逐项引用各章实际稿件解释结果；任何缺场、缺章或未核字段均不算通过。',
    'anchor': '绑定具体对象或体验者、观察者、节拍和时机；给出原触发条件成立的前因与可观察正文。',
    'material_selection': '记录本次任务功能、选中板块与必需子项、未选原因以及作者采用决定。',
    'material_conversion': '把每项已选规则对应到项目参数、正文表现和可核验点，保留所依赖的选用清单。',
}


def _normal(text: str) -> str:
    return ' '.join(text.replace('\\', '').replace('*', '').split()).strip(' -')


def _present(text: str) -> bool:
    return _normal(text) not in {'', '无', '无。', '暂无', '不适用', '略'}


def _profile(key: str) -> str:
    if profile := stage_profile(key):
        return profile
    match = _NUMBER.match(key)
    number = int(match[1]) if match else 0
    if number == 108:
        return 'preflight' if key.startswith('108.1') else 'prose_review'
    for group, profile in (
        (range(1, 10), 'character'), (range(10, 41), 'world'), (range(41, 46), 'plot'),
        (range(46, 48), 'scene'), ({48}, 'plot'), (range(49, 61), 'expression'),
        (range(61, 67), 'plot'), (range(67, 87), 'character'), ({87}, 'scene'),
        ({88}, 'expression'), ({89}, 'prose_review'), ({90}, 'legacy'),
        (range(91, 108), 'prose_review'), ({109}, 'knowledge'), ({110}, 'anchor'),
        ({111, 113}, 'plot'), ({112}, 'opening'), ({114, 124}, 'type_expression'),
        ({115}, 'scene'), ({116, 117, 120, 140, 142, 158}, 'knowledge'),
        ({118, 133, 134}, 'continuity'), ({119, 136, 143, 152, 159}, 'scene'),
        ({121, 144, 146, 147, 149, 150, 151, 153}, 'character'),
        ({122, 123, 130, 138, 141, 145, 154, 155}, 'plot'), ({125, 129}, 'world'),
        ({126, 128}, 'material_selection'), ({127}, 'material_conversion'),
        ({131, 139}, 'example'), ({132}, 'brief'), ({135, 162}, 'prose_review'),
        ({137}, 'legacy'), ({148}, 'anchor'), ({156, 157, 160, 161}, 'expression'),
    ):
        if number in group:
            return profile
    return 'example'


class LibraryAdjudicator:
    """Review dictionaries selected by route_catalog._FRAGMENTS or _UNITS."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self._cache: dict[str, dict] = {}
        self._recognized: dict[str, set] = {}

    def _current_owner(self, root: dict) -> bool:
        if root['kind'] not in {'embedded_entry', 'embedded_block'}:
            return True
        suffix = (root['key'] or '').rsplit('#',1)
        if len(suffix)==2 and re.fullmatch(r'\d+_.+',suffix[1]) and self.connection.execute('''
            SELECT 1 FROM material_units WHERE fragment_id=? AND kind='embedded_block'
            AND key=? AND byte_start=? AND byte_end=? LIMIT 1''',
            (root['fragment_id'],suffix[1],root['byte_start'],root['byte_end'])).fetchone() is not None:
            return False
        return self._current_unit(root)

    def _current_unit(self, root: dict) -> bool:
        ident = root['fragment_id']
        if ident not in self._recognized:
            fragment = self.connection.execute('SELECT * FROM fragments WHERE id=?', (ident,)).fetchone()
            text = fragment['payload'].decode('utf-8')
            self._recognized[ident] = {
                (unit.kind, fragment['byte_start'] + len(text[:unit.start].encode('utf-8')),
                 fragment['byte_start'] + len(text[:unit.end].encode('utf-8')), unit.key)
                for unit in units_for_fragment(text, fragment['kind'], fragment['key'])}
        return (root['kind'], root['byte_start'], root['byte_end'], root['key']) in self._recognized[ident]

    def _owner(self, row: dict) -> dict:
        if row['kind'] in _ROOTS:
            return row
        found = self.connection.execute('''SELECT * FROM material_units WHERE fragment_id=?
            AND kind IN ('embedded_entry','embedded_block') AND byte_start<=? AND byte_end>=?
            ORDER BY byte_end-byte_start, instr(key,'#') LIMIT 1''',
            (row['fragment_id'], row['byte_start'], row['byte_end'])).fetchone()
        if found is not None:
            return {**row, **dict(found), 'level': 'unit', 'fragment_id': row['fragment_id']}
        root = self.connection.execute('SELECT * FROM fragments WHERE id=?', (row['fragment_id'],)).fetchone()
        return {**row, **dict(root), 'level': 'fragment', 'fragment_id': root['id'],
                'origin': 'source', 'label': None, 'locator': None}

    def _payload(self, row: dict) -> bytes:
        data = self.connection.execute('SELECT substr(payload,?-byte_start+1,?) FROM fragments WHERE id=?',
            (row['byte_start'],row['byte_end']-row['byte_start'],row['fragment_id'])).fetchone()[0]
        if sha256(data).hexdigest() != row['sha256']:
            raise ValueError('Material contract hash mismatch')
        return data

    @staticmethod
    def _ref(row: dict) -> dict:
        return {key: row[key] for key in ('id', 'fragment_id', 'source_id', 'path', 'file_sha256',
                                         'sha256', 'byte_start', 'byte_end', 'line_start', 'line_end')}

    def _fields(self, root: dict, text: str) -> list[dict]:
        headings = list(_HEADING.finditer(text))
        root_data = self._payload(root)
        heading_bytes, previous, byte_position = [], 0, 0
        for heading in headings:
            byte_position += len(text[previous:heading.start()].encode('utf-8'))
            heading_bytes.append(byte_position)
            previous = heading.start()
        raw = self.connection.execute('''SELECT * FROM material_units WHERE fragment_id=?
            AND origin='source' AND byte_start>=? AND byte_end<=? ORDER BY byte_start,byte_end,id''',
            (root['fragment_id'], root['byte_start'], root['byte_end'])).fetchall()
        fields, seen = [], set()
        for unit in raw:
            if unit['kind'] not in _CATEGORIES:
                continue
            if unit['key'] != root['key'] and '/chapter_checklist/' in unit['locator']:
                continue
            if not self._current_unit({**root, **dict(unit)}):
                continue
            marker = (unit['byte_start'], unit['byte_end'], unit['kind'])
            if marker in seen:
                continue
            seen.add(marker)
            row = {**root, **dict(unit), 'id': unit['id'], 'fragment_id': root['fragment_id']}
            left,right = unit['byte_start']-root['byte_start'],unit['byte_end']-root['byte_start']
            data = root_data[left:right]
            if sha256(data).hexdigest()!=unit['sha256']:
                raise ValueError('Material contract hash mismatch')
            body = data.decode('utf-8')
            body = _FIELD.sub('', body, count=1)
            body = re.split(r'(?m)^#{2,6}\s|^## 资料库原版条目补全', body, maxsplit=1)[0].strip()
            if not _present(body):
                continue
            index = bisect_right(heading_bytes,left)-1
            heading = headings[index] if index>=0 else None
            scope = (heading[1] or heading[2]).strip() if heading else root['key']
            fields.append({'category': _CATEGORIES[unit['kind']], 'label': unit['label'],
                           'scope': scope, 'text': body, 'ref': self._ref(row)})
        if not fields and (root['key'] or '').startswith('板块162 '):
            # This original uses a mapping table and checklist, without field labels.
            stop = text.find('## 资料库原版条目补全')
            stop = len(text) if stop < 0 else stop
            sections = [h for h in headings if h[2] and h.start() < stop]
            for index, heading in enumerate(sections):
                end = sections[index+1].start() if index+1 < len(sections) else stop
                body = text[heading.start():end].strip()
                data = text[heading.start():end].encode('utf-8')
                left = root['byte_start'] + len(text[:heading.start()].encode('utf-8'))
                ref = self._ref(root) | {'span': {
                    'byte_start': left, 'byte_end': left+len(data), 'sha256': sha256(data).hexdigest()}}
                fields.append({'category': 'checks' if '- [ ]' in body else 'definition',
                               'label': heading[2], 'scope': root['key'], 'text': body, 'ref': ref})
        return fields

    @staticmethod
    def _conflict(kind: str, reason: str, fields: list[dict]) -> dict:
        return {'kind': kind, 'reason': reason, 'source_refs': [f['ref'] for f in fields]}

    def _library(self, root: dict, text: str, fields: list[dict]) -> tuple[list, list]:
        missing, conflicts = [], []
        definitions = [f for f in fields if f['category'] == 'definition']
        foreign = [m[1] for m in _FOREIGN.finditer(text)
                   if not (root['key'] or '').startswith(m[1] + '_')]
        if foreign and root['kind'] == 'library_entry':
            conflicts.append(self._conflict('mixed_contract_scope',
                '此片段还包含其他原编号的合同，不能把不同对象都归到当前编号：' + '、'.join(dict.fromkeys(foreign)),
                definitions[:2]))
        for directive in (f for f in fields if f['category'] == 'directives'):
            value = _normal(directive['text'])
            number = _NUMBER.match(root['key'] or '')
            # A character's beliefs, costs and motives can drive choices. The
            # same wording about a reader effect, POV technique or authoring
            # procedure changes the subject of the original definition.
            procedural = number is not None and int(number[1]) in {
                *range(101, 116), 119, 120, 124, 126, 127, 128}
            domain_template = ('作为角色决策的深层驱动，通过行为而非旁白呈现' in value
                               and (procedural or value.startswith('将读者')))
            bodily_template = '在场景中触发角色的' in value and '身体信号' in value
            definition = next((f for f in definitions if f['scope'] == directive['scope']), None)
            if definition is not None and (domain_template or bodily_template):
                conflicts.append(self._conflict('semantic_domain_conflict',
                    '定义处理叙事、读者认知或创作规则，指令却把该对象改成角色动机或身体状态；两者不能作为同一合同执行。',
                    [definition, directive]))
                break
        if '五类信息' in text and all(token in text for token in
                ('自己知道什么', '自己不知道什么', '别人知道什么', '别人不知道什么', '读者知道什么', '读者不知道什么')):
            conflicts.append(self._conflict('declared_count_mismatch',
                '指令称“五类信息”，原文实际列出三组知情/未知，共六项；采用前应明确计数口径。',
                [f for f in fields if '五类信息' in f['text']]))
        by_scope: dict[str, list] = defaultdict(list)
        for field in fields:
            by_scope[field['scope']].append(field)
        checklist = (root['key'] == '162.2_审美检查清单'
                     and any(f['label'] == '每章编辑模式检查' for f in fields)
                     and any(f['category'] == 'checks' for f in fields))
        if not definitions and not checklist:
            missing.append('原位置未提供可独立解释的定义；空板块标题不承载子项合同。')
        for scope, members in by_scope.items():
            defs = [f for f in members if f['category'] == 'definition']
            operative = [f for f in members if f['category'] in {'directives', 'checks', 'exclusions'}
                         and not _BOILERPLATE.fullmatch(_normal(f['text']))
                         and (_OPERATION.search(_normal(f['text'])) or
                              all(_normal(f['text']) != _normal(d['text']) for d in defs))]
            explicit_workflow = stage_profile(root['key'] or '') and any(
                sum(term in f['text'] for term in ('写作前记录','写作后记录','单元复盘','时间线建立',
                    '伏笔埋设阶段','视角切换决策','开篇写作前')) >= 2 for f in defs)
            if defs and not operative and not explicit_workflow and not any(_OPERATION.search(_normal(f['text'])) for f in defs):
                missing.append(f'「{scope}」只有概念或复述模板，缺少具体操作、判据或明确的参数结构。')
            for field in members:
                if field['category'] not in {'definition', 'directives', 'checks', 'exclusions'}:
                    continue
                value = _normal(field['text'])
                if any(value.count(left) > value.count(right) for left, right in (('（', '）'), ('(', ')'))):
                    missing.append(f'「{scope}」{field["label"]}有未闭合的说明，原文边界或内容不完整。')
                    break
                if re.search(r'(?:三种核心特征|四种强度|三项原则|全部项目)[:：。]?$', value):
                    missing.append(f'「{scope}」宣称列举结构，但原文未列出具体成员。')
        return list(dict.fromkeys(missing)), conflicts

    def _anchor(self, fields: list[dict]) -> tuple[list, list]:
        by_label = {f['label']: f for f in fields}
        missing, conflicts = [], []
        for label in ('锚点名称', '具体内容', '触发条件'):
            if label not in by_label:
                missing.append(f'原锚点缺少{label}，不能建立完整状态与触发合同。')
        if missing:
            return missing, conflicts
        content, condition = by_label['具体内容'], by_label['触发条件']
        if _VAGUE.fullmatch(_normal(condition['text'])):
            missing.append('原触发条件仅为特殊条件或升级/突破占位，缺少可核验的前置机制。')
        value = _normal(content['text'])
        test = _normal(condition['text']).replace(' ', '')
        if ('完全用完' in value or '资源耗尽' in value) and re.search(r'(?:储备|资源量)>0', test):
            conflicts.append(self._conflict('state_condition_conflict',
                '“耗尽”的定义与“储备大于零”的触发条件直接矛盾。', [content, condition]))
        return missing, conflicts

    def _review_owner(self, root: dict) -> dict:
        text = self._payload(root).decode('utf-8')
        fields = self._fields(root, text)
        profile = 'anchor' if root['family'] == 'anchors' else _profile(root['key'] or '')
        missing, conflicts = self._anchor(fields) if root['family'] == 'anchors' else self._library(root, text, fields)
        operative = '\n'.join(field['text'] for field in fields if field['category'] in {'directives', 'checks'})
        evidence_scope = None
        if profile in {'prose_review', 'expression', 'continuity'}:
            if re.search(r'通读全书|全书完成后|全书|全篇|终章前全部', operative):
                evidence_scope = 'book'
            elif re.search(r'章节之间|不同章节|各章节|跨章|重章后必须|每3章检查', operative):
                evidence_scope = 'cross_chapter'
            elif (re.search(r'每章|本章|章末|整章|全章', operative)
                  or any(f['category'] == 'conditions' and _normal(f['text']) in
                         {'每章编辑模式检查：', '每章写作完成后统计。'} for f in fields)):
                evidence_scope = 'chapter'
        exact_scope = _SCOPED_LIBRARY_CHECKS.get((root['key'], root['sha256']), {})
        evidence_scope = exact_scope.get('kind', evidence_scope)
        if evidence_scope:
            profile = 'scope_review'
        if not self._current_owner(root):
            missing.append('此旧索引视图不符合当前原文子项边界；保留回读，但不能单独采用。')
        if profile in _UNSUPPORTED or root['key'].startswith('板块135'):
            missing.append('本条包含立项、写前、接受后或外部反馈流程，当前正文设计绑定尚不能完成该阶段合同。')
        if self.connection.execute("""SELECT 1 FROM material_units WHERE fragment_id=?
                AND kind IN ('embedded_entry','embedded_block') AND id<>?
                AND byte_start>=? AND byte_end<=? LIMIT 1""",
                (root['fragment_id'], root['id'], root['byte_start'], root['byte_end'])).fetchone() is not None:
            missing.append('上层包含独立子项，应选择确切子项合同，不能整体替代每个子项的适用判断。')
        if root['layer'] != 'baseline' or root['file_sha256'] != _PINNED[root['family']]:
            missing.append('此版本未包含在本次原版语义裁定中；需与已钉定来源核对。')
        state = 'blocked' if conflicts else 'reference' if missing else 'design_ready'
        contract = {'owner_id': root['id'], 'key': root['key'], **{c: [] for c in _CATEGORIES.values()}}
        if evidence_scope:
            contract['evidence_scope'] = {
                'kind': evidence_scope, 'complete_chapters_required': 'scene_indices' not in exact_scope,
                'author_scope_required': True, **exact_scope,
            }
        for field in fields:
            contract[field['category']].append({k: v for k, v in field.items() if k != 'category'})
        conditions = [f['text'] for f in fields if f['category'] == 'conditions']
        definitions = [f['text'] for f in fields if f['category'] == 'definition']
        meaning = _normal(definitions[0])[:300] if definitions else (
            '逐项核对已采用的审美检查清单，取证范围为完整章稿。'
            if conditions and any(f['category'] == 'checks' for f in fields) and evidence_scope == 'chapter'
            else '原位置只提供标题或不完整的语义结构。')
        boundary = ('按完整原义及各小节的适用条件分别选用；例外、禁止和核验点均属于合同。'
                    '原文未给定的项目对象、情境与数值须由作者明确，不能据标签推定效果。')
        refs = [self._ref(root), *(f['ref'] for f in fields)]
        evidence = _EVIDENCE.get(profile, '提供该阶段真实输入、决策、产物和验证记录。')
        if 'scene_indices' in exact_scope:
            evidence = '冻结同章批准的前三场实稿，逐场引用版本一致的正文。程序分别核验第三场与前两场的篇幅比例。'
        return {'state': state, 'can_offer_for_design': state == 'design_ready', 'profile': profile,
                'meaning': meaning, 'boundary': boundary,
                'evidence_required': evidence +
                    '逐条对照完整contract中的定义、指令、条件、例外、检查和禁止，不能只核关键词。',
                'owner_id': root['id'], 'contract': contract, 'source_refs': refs,
                'conditions': conditions, 'missing': list(dict.fromkeys(missing)), 'conflicts': conflicts}

    def review(self, row: dict) -> dict | None:
        """Return an evidence-backed owner disposition or contextual child view."""
        if (row['family'] not in _PINNED or row['origin'] in {'upgrade', 'supplement', 'residual'}
                or row['kind'] in {'library_upgrade', 'anchor_upgrade', 'upgrade'}):
            return None
        root = self._owner(row)
        if root['kind'] not in _ROOTS:
            return None
        if root['kind'] == 'anchor' and not self._payload(root).lstrip().startswith(b'|'):
            if self.connection.execute("SELECT 1 FROM material_units WHERE fragment_id=? AND origin='upgrade' LIMIT 1",
                                       (root['fragment_id'],)).fetchone() is not None:
                return {'state': 'reference', 'can_offer_for_design': False, 'profile': 'upgrade_review',
                        'meaning': '此位置只有后附运行层升级，同编号原始锚点表项另有独立来源。',
                        'boundary': '不能将补全段当作原始锚点，也不并入同编号原表合同。',
                        'evidence_required': '分别回读原始表项与追加段，再核对语义和出处。',
                        'owner_id': root['id'], 'contract': {'upgrade_only': True},
                        'source_refs': [self._ref(root)], 'conditions': [], 'conflicts': [],
                        'missing': ['后附升级尚未作为独立原版规则采用。']}
        cache_key = root['id'] + ':' + root['file_sha256']
        if cache_key not in self._cache:
            self._cache[cache_key] = self._review_owner(root)
        result = dict(self._cache[cache_key])
        if row['id'] != root['id']:
            result.update(state='context', owner_state=result['state'], can_offer_for_design=False,
                          related=[root['id']], meaning=f'完整原义「{root["key"]}」的{row["label"] or row["kind"]}字段。' + result['meaning'],
                          boundary='此字段须随完整拥有者合同解释，不能独立选用。' + result['boundary'])
        return result
