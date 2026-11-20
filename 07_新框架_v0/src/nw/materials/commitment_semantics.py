"""Ground responsibility in an attributable promise, its beneficiary and the actual promised act."""
import re

from nw.materials.design_network_catalog import POLICY

KEYS = {'C00655', 'C01153', 'C01573', 'C01585'}
_OATH = re.compile(r'亲口答应|答应|许诺|承诺|应允|允诺|立誓|发誓|约定|保证|保证过')
_UNCERTAIN = re.compile(r'据说|传闻|尚待|待定|待核|假设|如果他答应|若她答应|未曾|未向|尚未|没有答应|没有承诺|拒绝承诺|拒绝答应|不肯答应|未答应|并未|假称|谎称|并非')
_FAMILIES = {
    '归还': ('物归原主', '交还', '还给', '还回', '退还', '归还', '送回', '奉还', '交回', '返还', '还船', '还钱'),
    '照料': ('照顾', '照看', '照料', '奉养', '赡养', '看护', '照护'),
    '护送': ('护送', '接回', '送上岸', '平安送到', '送回家', '接应', '接上岸', '接出'),
    '交付': ('送交', '送达', '送到', '交付', '递交', '送给', '运送', '送药', '寄给', '递给', '交给', '送'),
    '保护': ('守护', '保护', '保全', '护住', '庇护'),
    '营救': ('营救', '救回', '救出', '救助', '解救'),
    '偿还': ('代偿', '清偿', '偿付', '偿还', '还清', '偿清', '还债'),
    '修复': ('修理', '修复', '修好', '修补', '修缮'),
    '作证': ('出庭作证', '出面指认', '当庭作证', '作证', '指证'),
    '保密': ('保守秘密', '守口如瓶', '守密', '保密', '隐瞒'),
    '找回': ('寻回', '找回', '寻访', '寻找', '找出'),
}
_VERBS = {v: group for group, terms in _FAMILIES.items() for v in terms}
_ACT = re.compile('|'.join(sorted(_VERBS, key=len, reverse=True)))
_PERSON_ACTS = {'照料', '护送', '保护', '营救'}
_ROLE = re.compile(r'老船工|老渔夫|祖母|奶奶|祖父|爷爷|外婆|外祖母|外公|外祖父|母亲|父亲|阿娘|爹爹|妹妹|弟弟|哥哥|姐姐|雇主|东家|雇工|船主|船工|船长|老师|师父|村长|叔父|姑母|债主|债权人|邻居|病人|遗属|伙计')
_SYNONYMS = {'奶奶': '祖母', '爷爷': '祖父', '外祖母': '外婆', '外祖父': '外公', '阿娘': '母亲',
             '爹爹': '父亲', '东家': '雇主'}
_TRIGGER = re.compile(r'((?:在|等到|待|只有|一旦)?[^，,。；;！？]{1,18}?(?:之前|以后|之后|之时|前|后|时))|((?:每当|一旦|只要|收到|听见|见到)[^，,。；;！？]{2,18})')
_TIME = re.compile(r'冬至|夏至|中秋|除夕|正月|端午|天明|天亮|日落|入夜|涨潮|退潮|收工|退水|洪水退|春汛|钟响|鸣钟')
_BREACH = re.compile(r'违[约诺]|失信|失约|食言|背弃|毁约|未能履约|未能践诺|没有履约|没能如约|未能如约|拒绝履行|未履行')
_FULFIL = re.compile(r'履约|履行|兑现|践诺|守约|守信|遵守.{0,3}(?:承诺|约定)|如约|依约|按约')
_DENIAL = re.compile(r'拒绝|未能|尚未|没能|没有|不肯|并未|不再|未按|未履|没履|并非|不算|无法|不会|绝不|不打算|不准备|不能|无须|无需|无意|不愿|拒不')
_COST = re.compile(r'(?:因此|于是|结果|致使|导致|以致|因而|只得|只好|不得不|从此|再也|失去|错过|追讨|索赔|断绝|决裂|撤回|收回|不再信任|取消|扣除|处罚|赔偿|承担了|被迫|另请|只能)([^，,。；;！？]{2,})')
_DUTY = re.compile(r'义务|契约|族规|职责|职务|奉命|契据|合同|受托')
_ACCEPT = re.compile(r'自愿|自认|良心|责任|立意|亲口|愿意承担|愧疚|有愧|欠.{1,8}(?:人情|恩情|债)')
_REDIRECT = re.compile(r'改为|改把|改交|改送|改还|转给|转交|冒充|充作|就算|算作|算是|算做|当作|抵作|顶替|代替|取代')
_ITEM_SPLIT = re.compile(r'也算|作为|充作|算作|当作|因此|才会|作为|以免|交差|以便|借此|之前|之后|以前|以后|交给|送给|还给|归还给|送到|交到|带回|送回|归还|退还|寄给|递给|放回|归回|归于|履约|的承诺|的约定|的义务|的责任|还[给回]|[给至把将]|并|以履|了')
_SINGLE = {'药', '钱', '船', '舟', '书', '印', '信', '债', '粮'}
_FILLER = re.compile(r'^(?:自己|本人|全部|这份|那份|那一|这一|这本|那本|一批|那艘|这艘|那条|这条|那包|这包|那本|这本|一份|一本|一封|一艘|的一艘|的|过|了|的那艘|的那本|的那包)+')


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r'[。；;！？!?\r\n]+', text.replace('[FAKE]', '')) if s.strip()]


def _normalize(text: str) -> str:
    for old, new in _SYNONYMS.items():
        text = text.replace(old, new)
    return text


def _persons(text: str, names: list[str]) -> list[str]:
    choices = sorted(set(names) | set(_ROLE.findall(text)), key=len, reverse=True)
    if not choices:
        return []
    return list(dict.fromkeys(_normalize(n) for n in re.findall('|'.join(map(re.escape, choices)), text)))


def _receiver(text: str, names: list[str]) -> str:
    oath = _OATH.search(text)
    if not oath:
        return ''
    before, after = text[:oath.start()], text[oath.end():]
    prior = re.search(r'[向对跟与和]([^，,]{1,10}?)(?:郑重|亲口|正式)?$', before)
    leading = re.split(r'[在于把将替为给，,]|一定|必须|要|会', after, maxsplit=1)[0]
    act = _ACT.search(leading)
    if act:
        leading = leading[:act.start()]
    for item in (prior[1] if prior else '', leading):
        matches = _persons(item, names)
        if matches:
            return matches[-1]
        if re.fullmatch(r'[\u3400-\u9fff]{2,4}', item) and not _TIME.search(item):
            return item
    return ''


def _directed_people(text: str, names: list[str]) -> set[str]:
    labels = sorted(set(names) | set(_ROLE.findall(text)), key=len, reverse=True)
    if not labels:
        return set()
    targets = re.findall(r'(?:交到|送往|送到|归还给|转交给|交给|还给|送给|留给|交还|归还|偿还|奉还|退还|为了|替|为|给|向|护送|照顾|照看|接回|营救|照料|赡养|救助)('
                         + '|'.join(map(re.escape, labels)) + ')', text)
    for explicit in re.finditer(r'(?:还给|交给|转交给|留给|送给|递给)([\u3400-\u9fff]{1,12})', text):
        recipient = re.split(r'手里|手中|保管|收下|带走|代收|验收|签收|的|并|才|后|再', explicit[1])[0]
        recognisable = _persons(recipient, names)
        if not recognisable and 2 <= len(recipient) <= 5:
            targets.append(recipient)
    return set(map(_normalize, targets))


def _subject(phrase: str, act: re.Match, names: list[str]) -> str:
    before, after = phrase[:act.start()], phrase[act.end():]
    obj = re.search(r'(?:把|将)([^，,]{1,24})$', before)
    word = obj[1] if obj else after
    word = re.split('[，,。；;]', word)[0]
    surname = _persons(word, names)
    if surname and '的' in word:
        # Its owner can also be the promisee (“归还祖母的旧船”).
        word = word.rsplit('的', 1)[-1]
    word = _FILLER.sub('', _ITEM_SPLIT.split(word)[0]).strip()
    if word in surname or word in ('来', '去', '它', '那件事', '此事', '这件事', '约定', '承诺', '责任', '义务'):
        word = ''
    if not word and act[0] in ('送药', '还船', '还钱', '还债'):
        word = act[0][-1]
    return word if (2 <= len(word) <= 14 or word in _SINGLE) else ''


def _actor_ok(prefix: str, actor: str, names: list[str]) -> bool:
    prefix = re.split('[，,]', prefix)[-1]
    prefix = re.sub(r'[向对跟与和][^，,]{1,8}(?:郑重|亲口|正式)?$', '', prefix)
    people = _persons(prefix, names)
    if people:
        return people[-1] == actor
    return not prefix.strip() or bool(re.search(r'我|她|他|本人|自己|亲口|主动|当面|当众|郑重|决定|愿意', prefix))


def _promises(statement: str, actor: str, names: list[str]):
    oath = _OATH.search(statement)
    if not oath or _UNCERTAIN.search(statement) or not _actor_ok(statement[:oath.start()], actor, names):
        return
    receiver = _receiver(statement, names)
    clause = statement[oath.end():]
    verbs = list(_ACT.finditer(clause))
    if not verbs:
        return
    # Multiple distinct acts in one promise need separate, unambiguous project evidence.
    if len({_VERBS[a[0]] for a in verbs}) > 1:
        return
    act = verbs[0]
    action = _VERBS[act[0]]
    people = [p for p in _persons(clause, names) if p != actor]
    target = _directed_people(clause, names)
    if len(target) > 1:
        return
    beneficiary = next(iter(target), receiver or (people[0] if len(people) == 1 else ''))
    receiver = receiver or beneficiary
    subject = '' if action in _PERSON_ACTS else _subject(clause, act, names)
    if beneficiary and receiver and (subject or action in _PERSON_ACTS):
        yield {'actor': actor, 'promisee': receiver, 'beneficiary': beneficiary, 'action': action, 'subject': subject}


def _consequence(text: str, proof: dict) -> bool:
    if proof['beneficiary'] not in text:
        return False
    breach = _BREACH.search(text)
    if not breach:
        breach = next((a for a in _ACT.finditer(text) if _VERBS[a[0]] == proof['action']
                       and _DENIAL.search(text[max(0, a.start()-5):a.start()])), None)
    if not breach:
        return False
    tail = text[breach.end():]
    cost = _COST.search(tail)
    if not cost:
        return False
    # The consequence must happen to this promisor or beneficiary. A bystander's loss is independent.
    outcome = tail[:cost.start()].rsplit('。', 1)[-1] + tail[cost.start():]
    participants = _persons(outcome, [proof['actor'], proof['beneficiary'], proof['promisee']])
    if set(participants) - {proof['actor'], proof['beneficiary'], proof['promisee']} and not (
            proof['actor'] in outcome or proof['beneficiary'] in outcome):
        return False
    return bool(re.search(r'失去|丢失|错过|追讨|索赔|决裂|断绝|撤回|收回|不再(?:信任|借|许)|取消|扣除|处罚|赔偿|被迫|无船|无法|只得|只好|不得不|只能|另请|另雇|另租|被困|受阻|断药|延误|推迟|逾期|受罚|受伤|滞留|损失|被逐|毁损', tail))


def _claims_completion(text: str) -> bool:
    return any(not re.search(r'未能|不肯|不是|不能|不算|不曾|没能|没有|拒绝|并未|未$|没$|并非|本想|本应|本要|原想|原要|原定|打算|准备|本来要',
                             text[max(0, m.start()-5):m.start()]) for m in _FULFIL.finditer(text))


def _same_act(proof: dict, text: str) -> bool:
    beneficiary, subject = proof['beneficiary'], proof['subject']
    names = [proof['actor'], proof['promisee'], beneficiary]
    for sentence in _sentences(_normalize(text)):
        for part in re.split('[，,]', sentence):
            # A claimed fulfilment can repeat the original obligation verbatim after an unrelated act.
            part = re.split(r'(?:这(?:件事|件差事|次差事)?|便|就)?(?:也?算作|算做|当作|充作|抵作|算是|冒充|自称|声称)', part, maxsplit=1)[0]
            verbs = [v for v in _ACT.finditer(part) if _VERBS[v[0]] == proof['action']]
            if not verbs or subject and subject not in part:
                continue
            prefix = re.split(r'把|将|替|为了|为|向|对于|给', part[:verbs[0].start()])[0]
            agents = _persons(prefix, names)
            if agents and agents[-1] != proof['actor']:
                continue
            targets = _directed_people(part, names)
            if targets - {beneficiary}:
                continue
            if beneficiary not in part and (not subject or _persons(part, names) and beneficiary not in targets
                    and set(_persons(part, names)) - {proof['actor'], proof['promisee']}):
                continue
            if any(re.search(r'不$', part[:v.start()]) or _DENIAL.search(part[max(0, v.start()-5):v.start()]) for v in verbs):
                continue
            others = set(_persons(part[:verbs[0].start()], names)) - {proof['actor'], beneficiary, proof['promisee']}
            if others and not targets:
                continue
            return True
    return False


def _trigger(pledge: str, fields: dict, proof: dict):
    deadline = _TIME.search(pledge)
    if deadline:
        end = re.match(r'(?:之)?[前后时]', pledge[deadline.end():])
        return deadline[0] + (end[0] if end else ''), None
    anchors = [proof['subject'], proof['beneficiary']]
    for kind in ('change_conditions', 'boundaries', 'behavior'):
        for path, text in fields.get(kind, []):
            for part in _sentences(_normalize(text)):
                m = _TRIGGER.search(part)
                if m and (any(a and a in part for a in anchors) or _same_act(proof, part)):
                    return m[1] or m[2], path
    return '', None


def match_promises(key: str, fields: dict, actor: str, names: list[str], *, relative: str = ''):
    names = list(dict.fromkeys(_normalize(n) for n in [actor, *names] if n))
    for origin in ('relationship', 'background', 'behavior'):
        for path, text in fields.get(origin, []):
            for statement in _sentences(_normalize(text)):
                for proof in _promises(statement, _normalize(actor), names):
                    if relative and (proof['beneficiary'] != _normalize(relative) or proof['promisee'] != _normalize(relative)):
                        continue
                    goal_fields = ('want', 'independent_goal') if key in ('C00655', 'C01153') else (
                        'want', 'independent_goal', 'behavior', 'scene_function')
                    for goal_field in goal_fields:
                        for goal_path, goal in fields.get(goal_field, []):
                            if (goal_path == path or _UNCERTAIN.search(goal) or not (_same_act(proof, goal)
                                    or _consequence(_normalize(goal), proof) and not _claims_completion(goal)
                                    and (proof['subject'] in goal if proof['subject'] else proof['beneficiary'] in _normalize(goal)))):
                                continue
                            paths = [path, goal_path]
                            trigger, trigger_path = _trigger(statement, fields, proof)
                            if key == 'C00655':
                                if not trigger:
                                    continue
                                if trigger_path:
                                    paths.append(trigger_path)
                            if key in ('C01573', 'C01585'):
                                support = [(p, v) for f in ('need', 'core_conflict', 'want') for p, v in fields.get(f, [])
                                           if _ACCEPT.search(v) and (_same_act(proof, v) or proof['beneficiary'] in _normalize(v)
                                               and not _directed_people(_normalize(v), names) - {proof['beneficiary']})]
                                if not support:
                                    continue
                                paths.append(support[0][0])
                            if key == 'C01573':
                                steps = [(p, v) for f in ('behavior', 'scene_function') for p, v in fields.get(f, [])
                                         if _same_act(proof, v) and not _UNCERTAIN.search(v)]
                                if not steps:
                                    continue
                                paths.append(steps[0][0])
                            if key == 'C01585':
                                duties = [(p, s) for f in ('relationship', 'background') for p, v in fields.get(f, [])
                                          for s in _sentences(_normalize(v)) if _DUTY.search(s)
                                          and not re.search(r'另[外行]|另[一有]|与.{1,12}无关|同时又', s)
                                          and (_same_act(proof, s) or s == statement)]
                                if not duties:
                                    continue
                                paths.append(duties[0][0])
                            yield list(dict.fromkeys(paths)), {**proof, 'trigger': trigger if key == 'C00655' else ''}


def check_conflict(row: dict, text: str, *, stage: str) -> None:
    proof = row.get('commitment')
    if not proof or not isinstance(text, str):
        return
    value = _normalize(text)
    names = [proof['beneficiary'], proof['promisee'], proof['actor']]
    outcome = _normalize(row.get('commitment_aftermath', ''))
    with_result = value + ('。' + outcome if outcome and outcome != value else '')
    for sentence in _sentences(value):
        mentions = (proof['beneficiary'] in sentence or proof['promisee'] in sentence
                    or proof['subject'] and proof['subject'] in sentence)
        if not mentions:
            continue
        claimed_act = any(_VERBS[a[0]] == proof['action'] for a in _ACT.finditer(sentence))
        diverted = _REDIRECT.search(sentence) or (claimed_act or _FULFIL.search(sentence)) and (
            _directed_people(sentence, names) - {proof['beneficiary']})
        broken = _BREACH.search(sentence) or any(_DENIAL.search(sentence[max(0, a.start()-5):a.start()])
                                                 for a in _ACT.finditer(sentence) if _VERBS[a[0]] == proof['action'])
        opposed_time = False
        if (timing := re.fullmatch(r'(.+?)(?:之)?([前后])', proof.get('trigger', ''))) and claimed_act:
            opposite = '后' if timing[2] == '前' else '前'
            opposed_time = bool(re.search(re.escape(timing[1]) + '(?:之)?' + opposite, sentence))
        if ((broken or opposed_time) and (not _consequence(with_result, proof) or _claims_completion(sentence))
                or diverted and not _same_act(proof, sentence) and (proof['subject'] and proof['subject'] in sentence
                                                                   or _FULFIL.search(sentence)) and (not _consequence(with_result, proof) or _claims_completion(sentence))):
            raise ValueError('MATERIAL_STAGE: 承诺采用与本项目约定的对象、事项或违约事实矛盾')


def validate_use(row: dict, text: str, *, operation: str, stage: str) -> None:
    proof = row.get('commitment')
    if not proof:
        return
    value = _normalize(text)
    check_conflict(row, value, stage=stage)
    if _same_act(proof, value) and (proof['beneficiary'] in value or proof['beneficiary'] == proof['promisee'] and _FULFIL.search(value)):
        trigger = proof.get('trigger', '')
        if trigger and trigger not in _normalize(operation + ' ' + value):
            raise ValueError('MATERIAL_STAGE: 履责设计须保存启动同一义务的实际前置或期限')
        return
    op = _normalize(operation)
    outcome = _normalize(row.get('commitment_aftermath', ''))
    with_result = value + ('。' + outcome if outcome and outcome != value else '')
    asserts_done = _claims_completion(op) or _same_act(proof, op) and re.search(r'已经|已然|实际完成|确实完成|业已|已把|已将', op)
    if (_consequence(with_result, proof) and not _claims_completion(with_result) and not asserts_done
            and (proof['subject'] in value if proof['subject'] else any(_VERBS[m[0]] == proof['action'] for m in _ACT.finditer(value)))):
        return
    raise ValueError('MATERIAL_STAGE: 承诺采用须说明同一对象与约定事项的履约行动，或明确违约及其后果')
