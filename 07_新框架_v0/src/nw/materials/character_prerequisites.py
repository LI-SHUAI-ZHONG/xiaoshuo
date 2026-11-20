"""Locate character-rule prerequisites in frozen project fields, keeping actor and world rule together."""
import re
from functools import lru_cache

from nw.materials.character_prerequisite_rules import SPECS
from nw.materials.phase_routes import product_ref


# Each group must be evidenced for the same character. '&' requires both concepts in
# one field. World requirements must hold on a single world card. These are conservative
# retrieval cues for a subsequent project-specific decision, not a source of story facts.
_CAP = 'ability basis'
_MIND = 'need core_conflict independent_goal want'
_TARGET = 'want independent_goal'
_ORIGIN = 'background relationship basis'
_BEHAVIOR = 'behavior voice'
_TALENT = '天赋|禀赋|资质'
_RANK = '品阶|层级|级别|等级|分级|评级|阶位'
_LIMIT = '上限|极限|瓶颈|至多|最多|顶点|承受阈值'
_RATE = '每息|每时|每刻|每秒|单位时间|速率|速度|一息|一刻'
_STORE = '储备|入储|储量|储能'
_EFF = '效率|比例|成数|百分|[%％]'
_SENSE = '察觉|感知|感应|辨识|辨认|感测|侦测'
_ENERGY = '灵气|灵力|能量|灵能|真气'
_PRESS = '压力|受压|危急|危机|威逼|逼迫|重压|威胁|高压|拷问'
_OATH = '答应|承诺|立誓|发誓|担保|誓约|应允|允诺|约定|许诺|宣誓'
_AMBITION = '渴望|野心|想要|力争|谋求|争取|决心|企图|立志'
_PROMOTE = '升迁|晋升|升任|升职|擢升|晋级|提拔|选拔'
_ELIGIBLE = '资格|条件|符合|任命|获准|核验|复验|考核|门槛|凭证|须|取得|持有|才能|方可|仅限|考中'
_RACE = '种族|族群|族裔|血脉|族人|族属|生为|生有'
_LOAD = '负荷|承受|重压|负重|过载|载重|耐受'
_CLASS = '阶层|士族|贵族|平民|贱籍|商籍|奴籍|世家|上户|下户|良籍|军籍'
_SOCIAL = '权限|职权|资格|放行|准许|允许|义务|领取|通行|签发|签放|查阅|免于|入内|无权|有权|获准|领用|扣留|受权|授权|须核验|须比对|须核对|负有'
_ETHIC = '善恶|对错|善待|行善|不义|作恶|无辜|良善|正直|道义|公正|宽仁'
_PERSIST = '坚持|执着|执念|不肯放弃|不愿放手|放不下|不改|未改|仍要|不肯放手|始终'
_NONEMPTY = '.'
_RULES = {
    'C00022': (('role', '证人|主角|对手|搭档|叙述者|侦探|配角|调查者|反派|守门人|嫌疑人'),
               ('scene_function', _NONEMPTY)),
    'C00023': (('role', '配角|辅助角色|次要人物'), ('scene_function', _NONEMPTY), ('relationship', _NONEMPTY)),
    'C00041': (('basis background', _TALENT + '&' + _RANK), ('ability', _NONEMPTY)),
    'C00044': (('basis background', _TALENT), ('cap_limit', _LIMIT)),
    'C00053': (('basis', '游离态|游离能|游离灵'), (_CAP, '吸收|汲取'), ('ability cap_limit basis', _RATE)),
    'C00069': (('basis', _STORE + '&' + _EFF), ('ability', '吸收|转化|入储'), ('cap_limit', _NONEMPTY)),
    'C00127': ((_CAP, _ENERGY), ('ability', _SENSE), ('cap_limit', _NONEMPTY)),
    'C00158': (('role', '反派|对立者|对手|敌手|反面人物'), ('independent_goal', _NONEMPTY),
               ('ability', _NONEMPTY), ('core_conflict scene_function', _NONEMPTY)),
    'C00193': (('basis', _TALENT + '&' + _RANK), (_CAP, '吸收|汲取'), ('ability basis cap_limit', _RATE)),
    'C00194': (('basis background', _TALENT + '&' + _RANK), ('cap_limit', _LIMIT)),
    'C00205': (('basis', _STORE + '&' + _EFF), ('ability', '吸收|转化|入储'), ('cap_limit', _NONEMPTY)),
    'C00206': (('basis background', '瓶颈|受阻|停滞'), ('basis background cap_limit', '训练|环境|负荷'),
               ('basis background', _TALENT)),
    'C00209': (('ability', _NONEMPTY), ('cap_limit', _LIMIT), ('change_conditions basis cap_limit', '突破|晋阶|越过|提升上限')),
    'C00269': (('role', '主要配角|重要配角|核心配角|次要配角|边缘配角|辅助配角|临时配角'),
               ('relationship', _NONEMPTY), ('scene_function', _NONEMPTY)),
    'C00270': (('role', '重要配角|主要配角|核心配角'), ('relationship', _NONEMPTY), ('independent_goal', _NONEMPTY),
               ('scene_function', _NONEMPTY)),
    'C00275': (('need', _NONEMPTY), ('want', _NONEMPTY)),
    'C00291': ((_BEHAVIOR, '社交|公开场合|人前|外人面前|当众|见客'), (_BEHAVIOR, '习惯|独处|日常|放松|私下'),
               (_BEHAVIOR, _PRESS)),
    'C00292': ((_BEHAVIOR, '社交|人前|公开场合|当众|见客'), (_BEHAVIOR, '日常|放松|私下|独处|习惯'),
               (_BEHAVIOR, _PRESS), ('scene_function change_conditions', _NONEMPTY)),
    'C00345': (('role background', '表层身份|公开身份|表面身份|对外身份'), ('background boundaries', '隐藏身份|真实身份|暗中身份|秘密身份'),
               ('background boundaries', '被动身份'), ('boundaries', '知情|只知|可见|公开|隐藏|保密|披露|不知')),
    'C00347': (('role', _NONEMPTY), ('boundaries background scene_function', _SOCIAL)),
    'C00451': (('role', _NONEMPTY), ('background behavior', '服饰|衣饰|制服|印记|徽记|徽章|袖章|刺青|标记|腰牌|服色'),
               ('boundaries', '可见|公开|掩饰|隐藏|辨认|知情|认出|识别|保密|猜测')),
    'C00457': (('strength flaw', _NONEMPTY), (_BEHAVIOR, _NONEMPTY), ('behavior change_conditions', '遇|每当|面对|受|时|一旦')),
    'C00459': (('strength behavior', '坚韧|韧性|不屈|坚忍|不服输'), ('behavior', _PRESS), ('behavior', _PERSIST)),
    'C00460': (('ability basis', _ENERGY), ('state', _STORE + '|能量总量|余量|剩余能量'), ('cap_limit', _NONEMPTY)),
    'C00461': (('basis background', '感知期|感应阶段'), ('ability', _SENSE), ('cap_limit', _NONEMPTY)),
    'C00462': (('state', '伤|骨折|体力|脱水|呼吸|体温|体能|出血|疲劳|体虚|中毒|疼痛|眩晕|步态|身体|颤抖'),
               ('cap_limit behavior boundaries', _NONEMPTY)),
    'C00463': (('state', '注意|精神|情绪|焦虑|惊恐|恐惧|失眠|恍惚|警觉|镇定|躁动|悲伤|忧郁|分神|惊惧'),
               ('behavior change_conditions', _NONEMPTY)),
    'C00649': ((_MIND, _AMBITION + '&' + _PROMOTE), ('background boundaries scene_function', _ELIGIBLE)),
    'C00655': (('relationship background', _OATH), ('want independent_goal', '履行|照顾|偿还|保护|履约|守护|承担|送达|替|护送'),
               ('change_conditions boundaries behavior', _NONEMPTY)),
    'C00726': (('background role', _CLASS), ('role', _NONEMPTY), ('boundaries background', _SOCIAL)),
    'C00734': ((_MIND, _AMBITION + '&' + _PROMOTE), ('background boundaries scene_function', _ELIGIBLE)),
    'C00787': (('background basis', _RACE + '&' + _TALENT), ('basis', _RANK), ('ability', _NONEMPTY)),
    'C00790': (('background basis', _RACE), ('basis cap_limit', _LOAD), ('cap_limit', _NONEMPTY)),
    'C00793': (('role background', _RACE), ('relationship background', '身份|登记|户籍|族籍|居留|迁居|族约'), ('boundaries', _SOCIAL)),
    'C00804': (('basis background', '构造|骨架|外壳|肉身|骨骼|义肢|机械体|甲壳'), ('cap_limit', _LOAD), ('ability', _NONEMPTY)),
    'C00830': (('role', _NONEMPTY), ('boundaries scene_function', _SOCIAL)),
    'C00832': (('role', _NONEMPTY), ('background relationship', '职位|职务|任职|登记|授予|受聘|任命|受命|编制|雇用'),
               ('boundaries', _SOCIAL)),
    'C00835': (('role', _NONEMPTY), ('basis', _NONEMPTY), ('ability', _NONEMPTY), ('cap_limit', _NONEMPTY)),
    'C00876': (('basis background', '感知期|感应阶段'), (_CAP, '学习|练习|训练|制作|习得'), ('cap_limit', _NONEMPTY)),
    'C01153': (('relationship background', _OATH), ('want independent_goal', '照顾|救|守|护|承担|照料|奉养|赡养|接回|送|履行')),
    'C01521': ((_TARGET, _NONEMPTY), ('strength behavior', '坚定|不动摇|坚守|不改初衷'),
               ('behavior', '干扰|劝阻|阻挠|诱惑|仍|动摇|威胁|压力')),
    'C01527': ((_TARGET, _NONEMPTY), ('need behavior', _PERSIST), ('behavior', '始终|每次|反复|多年|每天|连续|一次次|屡次')),
    'C01532': (('strength basis', '意志|坚韧'), ('behavior', _PRESS), ('change_conditions cap_limit', '恢复|休息|耗尽|疲劳|消耗|补充')),
    'C01566': (('need core_conflict background', _ETHIC), ('independent_goal want', '善待|恤|宽容|仁慈|怜悯|保护|守护|救助|公正|诚实|守信'),
               ('behavior', _NONEMPTY)),
    'C01568': (('background', _CLASS + '&经历|受过|遭|亲见|目睹|亲历|待遇'), ('need core_conflict want', '正义|公正|不公|公道|公平')),
    'C01573': (('relationship background', _OATH), ('need want', '责任|承担|履行|守护|赡养|偿还'),
               ('behavior scene_function', _NONEMPTY)),
    'C01585': (('relationship background', '义务|契约|族规|职责|职务|奉命|契据'), ('need core_conflict', '责任|自愿|自认|愧疚|良心'),
               ('behavior relationship', _OATH)),
}


_WORLD = {
    'C00041': _TALENT + '&' + _RANK, 'C00044': _TALENT + '&' + _LIMIT,
    'C00053': '游离态|游离能|游离灵&吸收|汲取', 'C00069': '转化|转存&' + _EFF,
    'C00127': _ENERGY + '&' + _SENSE, 'C00193': _TALENT + '&吸收|汲取&' + _RANK,
    'C00194': _TALENT + '&' + _RANK + '&' + _LIMIT, 'C00205': '转化|转存&' + _EFF,
    'C00206': _TALENT + '&瓶颈|受阻', 'C00209': '能力|术法|技艺|操作&' + _LIMIT,
    'C00460': _ENERGY + '&' + _STORE + '|总量|余量', 'C00461': '感知期|感应阶段',
    'C00649': _PROMOTE + '&' + _ELIGIBLE, 'C00726': _CLASS + '&' + _SOCIAL,
    'C00734': _PROMOTE + '&' + _ELIGIBLE, 'C00787': _RACE + '&' + _TALENT,
    'C00790': _RACE + '&' + _LOAD, 'C00793': _RACE + '&身份|户籍|族籍|登记|居留',
    'C00804': '构造|骨架|义肢|外壳|血肉|甲壳&' + _LOAD, 'C00830': _SOCIAL,
    'C00832': _SOCIAL, 'C00835': _ELIGIBLE, 'C00876': '感知期|感应阶段&学|练|制作',
    'C01532': '意志|坚韧&量表|刻度|级|档|阶|计量', 'C01568': _CLASS + '&' + _SOCIAL,
}
_EMPLOYMENT = {'C00830', 'C00832', 'C00835'}
_UNCERTAIN = re.compile(r'待定|待确认|待补|待设计|尚待|传闻|假设|据说|未经证实|可能是|仅为示例|仅作示例|尚不确定|未知|<填写')
_NEGATED = re.compile(r'不(?:再)?(?:采用|决定|影响|要求|需要|代表|表示|证明|属于|具备)|无需|无须|无关|毫无关系|并非|不是|未(?:曾)?(?:承诺|任职|获得|观测|观察|担任|习得)|没有(?:能力|资格|承诺|该规则)|假扮|冒充')
_KIN = re.compile(r'亲缘|血亲|母子|母女|父女|父子|胞兄|胞妹|姐弟|姐妹|兄弟|兄妹|祖孙|姑侄|舅甥|生母|生父|亲生')
_UNSPECIFIC = frozenset(('待定', '未知', '不详', '无', '没有', '无明显限制', '无特殊限制', '无任何限制', '由作者决定', '无所不能'))


@lru_cache(maxsize=256)
def _patterns(test: str) -> tuple:
    return tuple(re.compile(s, re.I) for s in test.split('&'))


def _statements(text: str):
    if isinstance(text, str):
        for part in re.split(r'[。；;！？!?\n]+', text):
            statement = part.replace('[FAKE]', '').strip()
            if len(statement) >= 2 and statement not in _UNSPECIFIC and not _UNCERTAIN.search(statement):
                yield statement


def _evidenced(text: str, test: str, *, limit: bool = False) -> bool:
    return any((limit or not _NEGATED.search(statement)) and all(p.search(statement) for p in _patterns(test))
               for statement in _statements(text))


def relevant(key: str, text: str) -> bool:
    """Suggest a design question from the actual demand. Suggestions confer no evidence."""
    if key not in SPECS or not isinstance(text, str):
        return False
    if key in _EMPLOYMENT:
        return bool(re.search(r'任职|职业|权限|履职|授权|职务|岗位|渡吏|职位|签放', text))
    if key == 'C01153':
        return bool(_KIN.search(text) and re.search(_OATH, text))
    tests = ([_WORLD[key]] if key in _WORLD else
             [test for _, test in _RULES[key] if test != _NONEMPTY])
    if not tests:
        tests = [r'深层欲望|内在需要|眼前目标|欲望.*目标|目标.*欲望']
    return any(all(pattern.search(text) for pattern in _patterns(test)) for test in tests)


def _fields(product: dict, person: dict, prefix: str) -> dict:
    fields = {field: [(f'{prefix}/{field}', value)]
              for field, value in person['body'].items() if isinstance(value, str)}
    for i, row in enumerate(product.get('capabilities', [])):
        if row['entity'] != person['key']:
            continue
        fields.setdefault('basis', []).append((f'/capabilities/{i}/basis', row['basis']))
        if row.get('can_act') is True:
            fields.setdefault('ability', []).extend((f'/capabilities/{i}/abilities/{j}', x) for j, x in enumerate(row['abilities']))
        fields.setdefault('cap_limit', []).extend((f'/capabilities/{i}/limits/{j}', x) for j, x in enumerate(row['limits']))
    for i, row in enumerate(product.get('states', [])):
        if row['entity'] == person['key'] and row['status'] == 'candidate':
            for field, value in row['state'].items():
                if isinstance(value, (int, float)) and not isinstance(value, bool) or isinstance(value, str) and value.strip():
                    escaped = field.replace('~', '~0').replace('/', '~1')
                    fields.setdefault('state', []).append((f'/states/{i}/state/{escaped}', f'{field} {value}'))
    return fields


def _occupation(role: str, rule: str) -> bool:
    # Also recognises occupations invented for this particular story. A common
    # particle or the presence of words like “职务” is insufficient to join cards.
    for part in re.findall(r'[\u3400-\u9fff]{2,}', role):
        if part in rule:
            return True
        for match in re.finditer(r'(?=([\u3400-\u9fff][官吏师医工匠员长探卫警丞卒使兵侍役农商僧尉]))', part):
            if match[1] in rule:
                return True
    return False


def _same_category(key: str, fields: dict, rule: str) -> bool:
    if key in {'C00726', 'C01568'}:
        categories = re.findall(_CLASS, rule)
    elif key in {'C00787', 'C00790', 'C00793'}:
        # A named fictional people (e.g. 青羽族) cannot stand in for another.
        categories = re.findall(r'([\u3400-\u9fff]{2}族)(?!群|裔|属)', rule)
        categories = [name for name in categories if name not in ('本种族', '该种族', '各种族', '的种族')]
    else:
        return True
    concrete = set(categories) - {'阶层', '种族'}
    names = [value for field in ('role', 'background', 'basis') for _, value in fields.get(field, ())]
    return not concrete or any(category in value for category in concrete for value in names)


def _duty_clauses(role: str, rule: str, requirement: str):
    # A subject after a comma can be a different office with different permissions.
    for sentence in _statements(rule):
        for clause in re.split('[，,]', sentence):
            if _occupation(role, clause) and _evidenced(clause, requirement):
                yield clause


def _job_skills(rule: str, role: str, fields: dict) -> set[str]:
    # A job title alone cannot turn an unrelated individual skill into a qualification.
    def phrases(text):
        cleaned = re.sub(r'任职|职业|岗位|职务|负责|通过|需要|必须|能够|可以|获准|受权|核验|考核|验核', ' ', text)
        return {run[i:i+2] for run in re.findall(r'[\u3400-\u9fff]+', cleaned) for i in range(len(run)-1)}

    title_words = {m[0] for m in re.finditer(r'[\u3400-\u9fff][官吏师医工匠员长探卫警丞卒使兵侍役农商僧尉]', role)}
    duties = {word for clause in _duty_clauses(role, rule, _ELIGIBLE) for word in phrases(clause)} - title_words
    result = set()
    for path, ability in fields.get('ability', ()):
        skill = ability.replace('[FAKE]', '').strip()
        if not _evidenced(skill, _NONEMPTY):
            continue
        for basis_path, basis in fields.get('basis', ()):
            clauses = [clause for clause in _statements(basis) if _evidenced(clause, _NONEMPTY)]
            if any(skill in clause and phrases(clause) & duties for clause in clauses):
                result.update((path, basis_path))
    return result


def _external(key: str, member: dict, fields: dict, products: dict, context: dict):
    if key == 'C00022':
        result = []
        for i, row in enumerate(products.get('type_selection', {}).get('products', {}).get('selection', [])):
            if (isinstance(row.get('label'), str) and row['label'] and row['label'] in member['body'].get('scene_function', '')
                    and _evidenced(row.get('basis'), '.')):
                result.append(([f'input:type_selection:/selection/{i}/label', f'input:type_selection:/selection/{i}/basis'], None))
        return result
    if key == 'C01153':
        relatives = {r['card_id']: (r['body']['name'], f"approved:{r['card_id']}:/body/name")
                     for r in context.get('approved_cards', []) if r['kind'] == 'character'}
        for index, person in enumerate(products.get('character_design', {}).get('products', {}).get('members', [])):
            if person['kind'] == 'character':
                relatives[person['key']] = person['body']['name'], f'input:character_design:/members/{index}/body/name'
        normalized = {ident: value[0].replace('[FAKE]', '').strip() for ident, value in relatives.items()}
        commitments = [clause for field in ('relationship', 'background') for _, value in fields.get(field, [])
                       for clause in _statements(value) if _evidenced(clause, _OATH)]
        result = []
        for i, rel in enumerate(products.get('static_relations', {}).get('products', {}).get('relations', [])):
            pair = (rel['source'], rel['target'])
            denied = re.search(r'(?:非|并无|无|假作|假称|假扮|冒充|如同|疑似|疑为)(?:亲缘|血亲|亲人|兄弟|兄妹|姐弟|姐妹|亲生)', rel['relation'] + rel['condition'])
            if (member['key'] not in pair or pair[0] == pair[1] or not _evidenced(rel['relation'], _KIN.pattern)
                    or denied or _UNCERTAIN.search(rel['condition']) or _NEGATED.search(rel['condition'])):
                continue
            other = pair[1] if pair[0] == member['key'] else pair[0]
            name = normalized.get(other, '')
            if (name and list(normalized.values()).count(name) == 1 and any(name in text for text in commitments)
                    and _evidenced(rel['condition'], '.')):
                result.append(([relatives[other][1], *(f'input:static_relations:/relations/{i}/{field}'
                               for field in ('source', 'target', 'relation', 'condition'))], None))
        return result
    if key not in _WORLD:
        return [([], None)]
    result = []
    world_stage = products.get('world_design')
    if not world_stage:
        return result
    worlds = [(c['body'], f'input:world_design:/members/{i}/body')
              for i, c in enumerate(world_stage['products'].get('members', [])) if c['kind'] == 'world']
    if not worlds:
        worlds = [(c['body'], f"approved:{c['card_id']}:/body") for c in context.get('approved_cards', []) if c['kind'] == 'world']
    for body, prefix in worlds:
        rule, limits = body.get('rule', ''), body.get('limits', '')
        if (not _evidenced(rule, _WORLD[key]) or not isinstance(limits, str) or not limits.strip()
                or _UNCERTAIN.search(limits) or limits.strip() in _UNSPECIFIC):
            continue
        if not _same_category(key, fields, rule):
            continue
        if key in _EMPLOYMENT and not any(_duty_clauses(member['body']['role'], rule, _WORLD[key])):
            continue
        skills = _job_skills(rule, member['body']['role'], fields) if key == 'C00835' else None
        if skills is None or skills:
            result.append(([f'{prefix}/rule', f'{prefix}/limits'], skills))
    return result


def matches(key: str, product: dict, *, products: dict, context: dict) -> list[dict]:
    if key not in SPECS:
        return []
    stage = 'world_design' if key in _WORLD else {'C00022': 'type_selection', 'C01153': 'static_relations'}.get(key)
    if stage is not None and stage in products:
        product_ref(products[stage])
    people = [(row, f'/members/{i}/body') for i, row in enumerate(product.get('members', [])) if row.get('kind') == 'character']
    created = {row['key'] for row, _ in people}
    located = {row['entity'] for table in ('states', 'capabilities') for row in product.get(table, [])}
    for card in context.get('approved_cards', []):
        if card['kind'] == 'character' and card['card_id'] in located and card['card_id'] not in created:
            people.append(({'key': card['card_id'], 'body': card['body']}, f"approved:{card['card_id']}:/body"))
    results = []
    for member, prefix in people:
        name = member['body'].get('name', '').replace('[FAKE]', '').strip()
        if not name or _UNCERTAIN.search(name) or name in _UNSPECIFIC:
            continue
        fields = _fields(product, member, prefix)
        paths = []
        for options, test in _RULES[key]:
            matching = [path for field in options.split() for path, text in fields.get(field, ())
                        if _evidenced(text, test, limit=field == 'cap_limit')]
            if not matching:
                break
            paths.extend(matching)
        else:
            if key == 'C00275' and member['body']['want'].strip() == member['body']['need'].strip():
                continue
            for refs, skills in _external(key, member, fields, products, context):
                selected = [p for p in dict.fromkeys(paths) if skills is None or
                            ('/abilities/' not in p and not p.endswith('/basis')) or p in skills]
                if any(p.startswith('/') for p in selected):
                    selected.append(f'{prefix}/name')
                    results.append({'member': member['key'], 'paths': [p for p in selected if p.startswith('/')],
                                    'upstream_refs': [p for p in selected if p.startswith('approved:')] + refs})
    return results
