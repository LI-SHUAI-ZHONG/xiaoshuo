"""Match supplementary world-network relationships to independently produced project evidence."""
import re

from nw.materials.phase_routes import product_ref
from nw.materials.world_prerequisite_edges import EDGES
from nw.materials.world_prerequisite_fields import FIELDS

_UNRESOLVED: dict[str, str] = {}

# The static source of these two edges is only written into the action step.
_ACTION_ONLY = {'C00025', 'C00032'}
_TYPE_COMPARISONS = {'C00702', 'C00782'}

SPECS = {
    key: {'source': src, 'target': dst, 'relation': relation, 'condition': condition, 'operation': operation,
          'family': FIELDS[key][0], 'needs': FIELDS[key][1], 'check': FIELDS[key][2], 'consumers': FIELDS[key][6],
          'status': 'unresolved' if key in _UNRESOLVED else 'conditional',
          **({'blocked_reason': _UNRESOLVED[key]} if key in _UNRESOLVED else {})}
    for key, (src, dst, relation, condition, operation) in EDGES.items()
}

_CLAUSES = re.compile(r'[。；;！？!?\r\n]+')
_UNSET = re.compile(
    r'待定|待补|待确认|待核|未证实|尚未(?:核实|确认|决定|采用|建立|明确)|未(?:确认|决定|启用|采用|建立|能证明)|'
    r'可能|也许|或许|疑似|据说|传闻|假设|猜测|设想|暂拟|例如|举例|示例|模板|占位|未必|不能据此|尚无依据|'
    r'没有证据|缺乏依据|没有(?:建立|采用)|不(?:取决于|决定|影响|导致|适用|采用|涉及)|无关|并非由|不再按|取消了|'
    r'仅列|标签[:：]|关键词[:：]|概念清单|待设计')
_BOUND = re.compile(r'只有|仅|只在|只能|只准|限于|须|需经|不得|不能|无法|禁止|除非|以外|超出|超过|'
                    r'否则|缺少|不足|无效|失效|拒绝|上限|至多|最多|越界|不许|不可|范围|适用于|时才')
_LINK = re.compile(r'因|由|根据|依|使|令|导致|随|决定|影响|须|才|经|会|若|时|在|故|遂|后|按|'
                   r'不能|无法|不可|只|限制|维持|降低|增加|减少|形成|保持|失去|记录|测得|视为|变为|来自|归为|'
                   r'纳入|依据|比照|相比|类似|换成|源于|源自|得名|取自|规定|征收|授予|列为|意味着|体现|铭记|验证|构成|'
                   r'作为|仅可|仅能|印证|以.{1,12}为')
_REVERSE = re.compile(r'取决于|依赖于|受制于|须依|源自|来自')
_CAUSE = re.compile(r'决定|导致|造成|引起|使得|影响|限定|规定|授予|促成|带来|体现|验证|印证')
# These pairs have separately authored reverse edges. A rule, its visible consequence
# and an observation offered as proof of that rule are different design evidence.
_DIRECTED = {'C00051', 'C00115', 'C00727', 'C00827', 'C00751', 'C00776'}
_PHYSICAL_FLOW = {'C00109', 'C00110', 'C00412', 'C00413'}
_TERMS = {key: tuple(re.compile(pattern) for pattern in row[3:6]) for key, row in FIELDS.items()}


def _parts(text: object) -> list[str]:
    if not isinstance(text, str):
        return []
    return [part.strip() for part in _CLAUSES.split(text) if part.strip()]


def relevant(key: str, text: str) -> bool:
    """Identify a targeted design question. Availability still requires product evidence."""
    if key not in SPECS:
        return False
    left, right, _ = _TERMS[key]
    edge = SPECS[key]
    labels = [edge[k].partition('_')[-1] for k in ('source', 'target')]
    for clause in _parts(text):
        if _UNSET.search(clause):
            continue
        if (left.search(clause) or labels[0] in clause) and (right.search(clause) or labels[1] in clause):
            return True
    return False


def _direction(key: str, evidence: str) -> bool:
    left, right, _ = _TERMS[key]
    # “岗位由门第决定” reverses the grammatical order, “由巡署授予待遇” names an executor.
    for passive in re.finditer(r'由([^，,。]{1,18}?)(?:决定|影响|限定|支配)', evidence):
        origin, outcome = passive[1], evidence[:passive.start()]
        if left.search(origin) and right.search(outcome):
            return True
        if right.search(origin) and left.search(outcome):
            return False
    for words, reverse in ((_REVERSE, True), (_CAUSE, False)):
        for link in words.finditer(evidence):
            before, after = evidence[:link.start()], evidence[link.end():]
            if left.search(before) and right.search(after):
                return not reverse
            if right.search(before) and left.search(after):
                return reverse
    return key not in _DIRECTED or left.search(evidence).start() < right.search(evidence).start()


def _world_evidence(key: str, body: dict, *, strict: bool = False):
    from nw.materials.design_semantics import world_eligible, SPECIAL_WORLD
    left, right, detail = _TERMS[key]
    if strict and key in SPECIAL_WORLD:
        if any(_UNSET.search(s) and left.search(s) and right.search(s)
               for s in _parts(body.get('rule')) + _parts(body.get('limits'))):
            return
        for clause in _parts(body.get('rule')):
            if _UNSET.search(clause) or clause == SPECS[key]['condition']:
                continue
            for limit in _parts(body.get('limits')):
                if not _UNSET.search(limit) and world_eligible(key, clause, limit, body):
                    yield clause, limit
        return
    limits = [s for s in _parts(body.get('limits')) if not _UNSET.search(s) and _BOUND.search(s)]
    if not limits:
        return
    # An explicit rejection of this particular relationship cannot attest it elsewhere in the same card.
    if any(_UNSET.search(s) and left.search(s) and right.search(s)
           for s in _parts(body.get('rule')) + _parts(body.get('limits'))):
        return
    for clause in _parts(body.get('rule')):
        if len(clause) < 8 or _UNSET.search(clause) or SPECS[key]['condition'] == clause:
            continue
        if not (left.search(clause) and right.search(clause) and _LINK.search(clause) and _direction(key, clause)):
            continue
        if key in _PHYSICAL_FLOW and re.search(
                r'必定.{0,8}由高向低|任何.{0,10}必然扩散|永远.{0,12}(?:高浓度.{0,6}低浓度|由高.{0,6}低)|无条件.{0,8}(?:逆流|汇聚|吸引)',
                clause):
            continue
        for limit in limits:
            if detail.search(clause) or detail.search(limit):
                yield clause, limit
                break


_ACT = r'(?:使用|施展|施放|发动|运用|施用|启动|施以|施术|施|用)'


def _acts(value, ability, actor, cast, names):
    # Other participants can witness the same skill. Assign a group event only to
    # the person who actually uses it in the frozen event design.
    spell = re.escape(ability)
    negative = re.compile(r'(?:不再|不得|不会|不能|无法|拒绝|没有|未曾|未能|禁止|封禁)\w{0,5}' + spell
                          + '|' + spell + r'(?:已经|仍然|现已|已|仍)?(?:封禁|失效|禁用|无法使用|不能施展)')
    aliases = {who: [a for a in (who, names.get(who)) if a] for who in cast}
    labels = '|'.join(re.escape(a) for values in aliases.values() for a in values)
    for sentence in _parts(value):
        for clause in re.split('[，,]', sentence):
            if ability not in clause or _UNSET.search(clause) or negative.search(clause):
                continue
            if len(cast) == 1 and not re.search(r'(?:旁观|观摩|观看|目睹|见证|见到|防范|防备|听到|感到).{0,16}' + spell, clause):
                return True
            for alias in aliases[actor]:
                lead = re.escape(alias) + r'(?:必须|只能|须|需要|决定|亲自|负责|随即|先行|再次|尝试|将|正|会|要|可|来){0,3}'
                if re.search(lead + _ACT + r'(?:自己的|本人的)?' + spell, clause):
                    return True
            group = re.search(r'((?:' + labels + r')(?:(?:、|和|与|及)(?:' + labels + r'))+)(?:共同|联手|合力|一起)'
                              + _ACT + spell, clause)
            if group and set(re.split('、|和|与|及', group[1])) & set(aliases[actor]):
                return True
    return False


def _action_refs(key: str, products: dict, rule: str, context: dict):
    from nw.materials.design_network_catalog import POLICY
    character = products.get('character_design')
    if not character:
        return
    product_ref(character)
    names = {r['card_id']: r['body'].get('name', '') for r in context.get('approved_cards', []) if r['kind'] == 'character'}
    names.update({r['key']: r['body'].get('name', '') for r in character['products'].get('members', []) if r['kind'] == 'character'})
    name_refs = {c['card_id']: f"approved:{c['card_id']}:/body/name" for c in context.get('approved_cards', []) if c['kind'] == 'character'}
    name_refs.update({m['key']: f'input:character_design:/members/{i}/body/name'
                      for i, m in enumerate(character['products'].get('members', [])) if m['kind'] == 'character'})
    people = {m['key'] for m in character['products'].get('members', []) if m['kind'] == 'character'}
    people.update(c['entity'] for table in ('states', 'capabilities') for c in character['products'].get(table, []))
    current_names = [names[who].removeprefix('[FAKE]').strip() for who in people if names.get(who)]
    dimension = _TERMS[key][1 if key == 'C00025' else 0]
    events = []
    # The completion gate of a successor belongs to its predecessor. Its own
    # description must establish a new action before that successor can use the rule.
    for stage, field, fields in [('plot_design', 'event_nodes', ('goal', 'obstacle', 'completion_condition')),
                                 ('event_design', 'candidates', ('event',))]:
        if record := products.get(stage):
            product_ref(record)
            events.extend((stage, field, j, event, fields) for j, event in enumerate(record['products'].get(field, [])))
    for index, capability in enumerate(character['products'].get('capabilities', [])):
        if capability.get('can_act') is not True or not capability.get('entity'):
            continue
        actor = capability['entity']
        for pos, ability in enumerate(capability.get('abilities', [])):
            if not isinstance(ability, str) or _UNSET.search(ability):
                continue
            name = ability.removeprefix('[FAKE]').strip()
            if len(name) < 2 or name not in rule:
                continue
            # When several abilities exist, their respective energy limits must be distinguishable.
            evidence = next(((k, j) for k in ('limits', 'abilities') for j, t in enumerate(capability.get(k, []))
                             if isinstance(t, str) and not _UNSET.search(t) and dimension.search(t)
                             and (name in t or k == 'limits' and len(capability['abilities']) == 1)), None)
            if evidence is None:
                continue
            for stage, field, j, event, fields in events:
                cast = event.get('actors', [])
                if actor not in cast:
                    continue
                for item in fields:
                    if not _acts(event.get(item), name, actor, cast, names):
                        continue
                    refs = [f'input:character_design:/capabilities/{index}/abilities/{pos}',
                            f'input:character_design:/capabilities/{index}/{evidence[0]}/{evidence[1]}',
                            f'input:{stage}:/{field}/{j}/{item}']
                    if (context.get('design_network_policy') == POLICY and key == 'C00025' and names.get(actor)
                            and current_names.count(names[actor].removeprefix('[FAKE]').strip()) == 1):
                        refs.append(name_refs[actor])
                    yield list(dict.fromkeys(refs))
                    break


def _selected_type_ref(rule: str, products: dict) -> list[str]:
    record = products.get('type_selection')
    if not record:
        return []
    product_ref(record)
    return [f'input:type_selection:/selection/{index}/label'
            for index, row in enumerate(record['products'].get('selection', []))
            if isinstance(row.get('label'), str) and row['label'] and row['label'] in rule and row.get('basis')]


def matches(key: str, product: dict, *, products: dict, context: dict) -> list[dict]:
    """Return exact world-card evidence; persisted callers also recheck source and producer identity."""
    if key not in SPECS or key in _UNRESOLVED:
        return []
    result = []
    for i, card in enumerate(product.get('members', [])):
        if card.get('kind') != 'world' or not card.get('key') or not isinstance(card.get('body'), dict):
            continue
        seen = set()
        from nw.materials.design_network_catalog import POLICY
        for rule, limit in _world_evidence(key, card['body'], strict=context.get('design_network_policy') == POLICY):
            if key in _ACTION_ONLY:
                choices = _action_refs(key, products, rule, context)
            elif key in _TYPE_COMPARISONS:
                type_refs = _selected_type_ref(rule, products)
                choices = [type_refs] if type_refs else []
            else:
                choices = [[]]
            for refs in choices:
                if tuple(refs) in seen:
                    continue
                seen.add(tuple(refs))
                result.append({'member': card['key'], 'paths': [f'/members/{i}/body/rule', f'/members/{i}/body/limits'],
                               'rule_excerpt': rule, 'limits_excerpt': limit,
                               **({'upstream_refs': refs} if refs else {})})
    return result
