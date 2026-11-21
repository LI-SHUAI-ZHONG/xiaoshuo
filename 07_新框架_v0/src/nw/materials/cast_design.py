"""Bind a character's entrance to an actual scene and an observable disclosure."""
from collections.abc import Iterable
import json
import re

from nw.models import Draft
from nw.story_models import Fact
from nw.store import Store
from nw.task_models import _text, canonical, content_sha256
from nw.story_state import IDENTITY_STATUS_PREFIX


STANDINGS = ('protagonist', 'antagonist', 'major', 'supporting', 'ordinary')
ENTRIES = ('opening', 'self', 'other', 'visible', 'withheld')
PERSON_FIELDS = ('creation_reason', 'scene_function', 'independent_goal', 'background', 'behavior', 'voice', 'boundaries')
CHARACTER_INSTRUCTION = (
    '新增每位有独立行动或交接的人物前先查已批准人物能否承担本步需求；不因角色名额造人。'
    '人物卡必须包含creation_reason（何种前置需求造成交集）、scene_function（本书需要他具体做什么）、'
    'independent_goal（他自己为什么来、离场后要做什么）、background（影响当前判断的一段记忆）、'
    'behavior（立场及压力下的决定）、voice（本人的用词与交流习惯）、boundaries（知情边界和不愿透露什么）。'
    'casting.need_ref从cast_needs选择，need_quote摘录该条中促成本次造人的具体前置。name/role只放能安全露面的称呼及表面身份。'
    '另填casting:{standing:protagonist/antagonist/major/supporting/ordinary,entry:opening/self/other/visible/withheld,'
    'public_identity:出场可见的身份或称呼}。主角开端用opening或留下隐身伏笔。重要角色与配角选择自报、'
    '他人介绍或有意隐瞒；普通功能人物可用可见行动出场。other另填introducer:实际人物key、'
    'introducer_source:prior/on_scene与introducer_basis。prior摘其卡片的经历、关系或已确证由他持有的该人事实。'
    'on_scene填他将怎样在场认出此人的可见凭据，须在介绍前安排他确实见证。'
    'withheld另填clue:读者可见线索、secret:真实身份、trigger:具体揭晓凭据。'
    '真身份及未来揭晓凭据只能写在这两个私有字段。人物地位、剧情任务和他自己的目的分别决定。'
)
EXPRESSION_INSTRUCTION = (
    '本场narration_bases里kind=cast_entry的每个人各有一次首登，必须用对应cast:人物:entry为依据写一拍，'
    '完整引用text并使实际表现包含该称呼或线索。opening交代主角此刻是谁、身在何处、眼下为何而动；'
    'self/other用指定介绍者的发言，本场真正听见者列为witnesses；说出某身份只证明有人这样介绍。'
    'withheld仅显露线索。只有已批准触发凭据由本视角实际见证或已确认，才可另用cast:人物:reveal，'
    '写本人当场表明身份或本视角直接辨认。接下来的选择要和这次相遇及角色自身目的相符。'
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError('MATERIAL_STAGE: 人物设计' + message)


def validate_card(body: dict) -> None:
    profile = body.get('casting')
    require(isinstance(profile, dict) and all(_text(body.get(k)) for k in PERSON_FIELDS),
            '须交付造人原因、剧情作用、个人目标、经历、判断习惯和声线')
    entry = profile.get('entry')
    standing = profile.get('standing')
    fields = {'standing', 'entry', 'public_identity', 'need_ref', 'need_quote'}
    if entry == 'withheld':
        fields |= {'clue', 'secret', 'trigger'}
    elif entry == 'other':
        fields |= {'introducer', 'introducer_basis', 'introducer_source'}
    require(standing in STANDINGS and entry in ENTRIES and fields == profile.keys()
            and all(_text(profile[k]) for k in fields), '身份及本次出场方式缺必需依据')
    require(entry != 'opening' or standing == 'protagonist', '主角开场必须属于主角')
    require(standing != 'protagonist' or entry in ('opening', 'withheld'), '主角开局须介绍其处境或有意保留身份伏笔')
    require(body['scene_function'].strip() != body['independent_goal'].strip(),
            '剧情作用和人物自己的目的需要分别说明')
    require(entry != 'visible' or standing == 'ordinary', '重要人物须有可追溯的身份介绍或留作伏笔')
    if entry == 'other':
        require(profile['introducer_source'] in ('prior', 'on_scene'), '他人介绍须区分此前已知或当场取得的凭据')
    if entry == 'withheld':
        secret = profile['secret']
        public = {k: v for k, v in body.items() if k != 'casting'}
        require(secret not in canonical(public) and secret not in profile['public_identity']
                and secret not in profile['clue'] and secret != profile['trigger'],
                '暗身份泄露到人物公开字段或线索与揭晓依据相同')


def need_sources(context: dict, products: dict) -> dict:
    result = {f'brief:{key}': value for key, value in context.get('brief', {}).items()
              if key in ('text', 'constraints') and _text(value)}
    for row in context.get('approved_cards', []):
        if row['kind'] not in ('chapter', 'plot', 'volume', 'promise', 'world'):
            continue
        for key in ('goal', 'conflict', 'choice', 'consequence', 'setup', 'rule', 'turn'):
            if _text(value := row['body'].get(key)):
                result[f'approved:{row["card_id"]}:{key}'] = value
    for row in products.get('world_design', {}).get('products', {}).get('members', []):
        if _text(value := row['body'].get('rule')):
            result[f'world:{row["key"]}:rule'] = value
    return result


def writer_card(body: dict, *, own: bool) -> dict:
    """Writer receives the current face, never the designer's reveal schedule or motive for casting."""
    keys = ('name', 'role', 'voice')
    if own:
        keys += ('want', 'background', 'behavior', 'need', 'wound', 'strength', 'flaw', 'boundaries',
                 'core_conflict', 'relationship', 'ability_cost', 'change_conditions', 'independent_goal')
    return {k: body[k] for k in keys if k in body}


def writer_brief(brief: dict, cards: list[dict]) -> dict:
    """Send the public clauses of the brief; identity and reveal terms travel through their approved beat."""
    protected = set()
    for card in cards:
        profile = card['body'].get('casting', {})
        if profile.get('entry') == 'withheld':
            protected.update((profile['secret'], profile['trigger']))
    if not protected:
        return brief
    visible = dict(brief)
    for field in ('text', 'constraints'):
        value = visible.get(field)
        if value:
            private = [m.span() for word in protected for m in re.finditer(re.escape(word), value)]
            if private:
                sentences = re.finditer(r'[^。！？.!?\n]*[。！？.!?\n]+|[^。！？.!?\n]+', value)
                visible[field] = ''.join(s.group() for s in sentences
                    if all(s.end() <= start or s.start() >= end for start, end in private)).strip()
    return visible


def guard_writer_package(cards: list[dict], facts: list[dict], checks: list[dict], package: dict) -> None:
    """Catch a concealed name accidentally repeated in another visible card, instruction or excerpt."""
    allowed = {(f['entity_id'], name) for f in facts if (name := confirmed_identity(f))}
    asides = {}
    for row in checks:
        if row['id'].startswith('work:narration:'):
            text = json.loads(row['observable'])
            if text['basis_claim'] == 'cast_reveal':
                allowed.add((text['cast_subject'], text['basis_quote']))
            if text.get('reader_identity') and text.get('audience') == 'reader_only':
                asides.setdefault((text['cast_subject'], text['reader_identity']), set()).add('material:' + row['id'])
    for card in cards:
        profile = card['body'].get('casting') or {}
        if profile.get('entry') == 'withheld' and (card['card_id'], profile['secret']) not in allowed:
            exempt = asides.get((card['card_id'], profile['secret']), set())
            material = [item for item in package['items'] if item.get('source') not in exempt] if exempt else package
            require(profile['secret'] not in canonical(material), '场景写作包包含尚未授权揭示的真实身份，请修正披露落点')


def confirmed_identity(fact: dict) -> str | None:
    value = fact.get('value')
    if (fact.get('claim') == 'fact' and fact.get('entity_id') and
            (fact.get('predicate') or '').startswith(IDENTITY_STATUS_PREFIX) and isinstance(value, dict)
            and _text(value.get('identity'))):
        return value['identity']
    return None


def reader_aside(guide: dict, basis: dict) -> bool:
    secret = basis.get('confirmed_identity')
    beat = guide['narration']
    return bool(secret and basis.get('audience') == 'READER' and beat['owner'] is None
                and secret in beat['basis_quote'] and secret in guide['observable'])


def previous_appearances(store: Store, cards: list[dict], *, accepted: dict | None = None,
                         occupied: set[str] | None = None) -> dict:
    """Use the accepted draft in occupied slots, and schedule only unwritten scenes."""
    first = dict(accepted or {})
    scenes = {(c['card_id'], c['version']): c['body'] for c in cards if c['kind'] == 'scene'}
    if not scenes:
        return first
    chapters = {ch.id: ch.index for ch in store.list('chapter')}
    for scene in store.list('scene'):
        if occupied and scene.id in occupied:
            continue
        ref = json.loads(scene.card_json).get('story', {}).get('scene_ref', {})
        body = scenes.get((ref.get('card_id'), ref.get('version')))
        if not body:
            continue
        pos = [chapters[scene.chapter_id], scene.index]
        for person in {body['pov'], *body.get('characters', [])}:
            first[person] = min(first.get(person, pos), pos)
    return first


def entry_bases(scene_product: dict, cards: list[tuple[str, str, dict]], prior: dict,
                facts: Iterable[dict] = (), *, new_people: set[str] | None = None,
                unverified_chapters: Iterable[int] = ()) -> dict:
    characters = {key: body for key, kind, body in cards if kind == 'character'}
    cast = {key: body['casting'] for key, body in characters.items() if 'casting' in body}
    places = {s['card']: [c['index'], s['index']] for c in scene_product['chapters'] for s in c['scenes']}
    times = {s['card']: s['story_order'] for c in scene_product['chapters'] for s in c['scenes']}
    first = dict(prior)
    scenes = {r['key']: r['body'] for r in scene_product['members']}
    for key, body in scenes.items():
        for person in {body['pov'], *body.get('characters', [])} & cast.keys():
            first[person] = min(first.get(person, places[key]), places[key])
    result = {k: {} for k in scenes}
    for key, body in scenes.items():
        people = {body['pov'], *body.get('characters', [])}
        for person in sorted(people & cast.keys()):
            profile = cast[person]
            unknown_history = person not in (new_people or ()) and any(index < places[key][0] for index in unverified_chapters)
            if first[person] == places[key] and not unknown_history:
                source = None
                if profile['entry'] == 'other':
                    require(profile['introducer'] in people - {person}, '首次出场缺少已设计的实际介绍者')
                    previous = [f for f in facts if f.get('story_order', times[key]+1) <= times[key] and
                                tuple(f.get('disclosure_order', ())) < (*places[key], 0)]
                    if profile['introducer_source'] == 'prior':
                        if new_people and ({person, profile['introducer']} & new_people):
                            previous = []
                        source = validate_introducer(profile, characters[profile['introducer']], person, previous)
                result[key][f'cast:{person}:entry'] = {
                    'kind': 'cast_entry', 'subject': person, 'entry': profile['entry'],
                    'text': profile.get('clue', profile['public_identity']), 'speaker': profile.get('introducer', person)}
                if profile.get('introducer_source') == 'on_scene':
                    result[key][f'cast:{person}:entry']['recognition_cue'] = profile['introducer_basis']
                if new_people is not None and source and Fact.__dataclass_fields__.keys() <= source.keys():
                    result[key][f'cast:{person}:entry']['state_sha256'] = content_sha256(source)
            if profile['entry'] == 'withheld':
                result[key][f'cast:{person}:reveal'] = {
                    'kind': 'cast_reveal', 'subject': person, 'text': profile['secret'], 'trigger': profile['trigger']}
    return result


def validate_introducer(profile: dict, speaker: dict, subject: str, facts: Iterable[dict]) -> dict | None:
    if any(profile['introducer_basis'] in (speaker.get(field) or '') for field in ('background', 'relationship')):
        return None
    for fact in facts:
        if fact.get('holder') == profile['introducer'] and fact.get('entity_id') == subject and fact.get('claim') == 'fact':
            value = confirmed_identity(fact) or fact.get('value')
            if _text(value) and profile['introducer_basis'] in value:
                return fact
    raise ValueError('MATERIAL_STAGE: 他人介绍身份须有该介绍人已定的经历或关系依据')


def validate_expression(rows: list[dict], scenes: dict, bases: dict, *, witnessed_entries: bool = False) -> None:
    for scene, scene_bases in bases.items():
        entries = {key for key, b in scene_bases.items() if b['kind'] == 'cast_entry'}
        secrets = {(b['subject'], b['text']) for b in scene_bases.values() if b['kind'] == 'cast_reveal'}
        pov = scenes[scene]['body']['pov']
        known = {(b.get('subject'), b['text']) for b in scene_bases.values() if b['kind'] == 'state'
                 and b.get('claim') == 'fact' and b.get('audience') == pov}
        disclosed = {(b.get('subject'), b['confirmed_identity']) for b in scene_bases.values()
                     if b.get('confirmed_identity') and b.get('audience') == pov}
        observed = []
        for guide in (row for row in rows if row['scene'] == scene):
            beat = guide['narration']
            basis = scene_bases[beat['basis_ref']]
            mode, owner = beat['mode'], beat['owner']
            if basis['kind'] in ('cast_entry', 'cast_reveal'):
                require(beat['time'] == 'current' and beat['basis_quote'] == basis['text']
                        and basis['text'] in guide['observable'], '出场或揭晓须实际呈现相应身份或线索')
            if basis['kind'] == 'cast_entry':
                require(beat['basis_ref'] in entries, '本场首登重复')
                entries.remove(beat['basis_ref'])
                entry = basis['entry']
                if entry in ('self', 'other'):
                    require(mode == 'speech' and owner == basis['speaker'], '身份介绍须由实际自述人或事先有依据的介绍者说出')
                    if witnessed_entries:
                        require(bool(beat['witnesses']), '身份介绍须有至少一名实际听见的在场者')
                    if cue := basis.get('recognition_cue'):
                        require(any(owner in witnesses and _seen_trigger(text, cue) for text, witnesses in observed),
                                '介绍人须先当场见证辨认对方的依据')
                elif entry in ('visible', 'withheld'):
                    require((mode == 'perception' and owner == pov) or
                            (mode in ('speech', 'action') and owner == basis['subject']), '人物出场线索须可直接见闻')
                else:
                    require((mode in ('speech', 'action', 'thought', 'perception') and owner == basis['subject']) or
                            (mode == 'summary' and owner is None), '主角开局须呈现其处境或自身行动')
            if basis['kind'] == 'cast_reveal':
                trigger = basis['trigger']
                require(f"cast:{basis['subject']}:entry" not in entries and
                        ((mode == 'speech' and owner == basis['subject']) or (mode == 'perception' and owner == pov))
                        and ((basis['subject'], trigger) in known or
                             any(pov in witnesses and _seen_trigger(text, trigger) for text, witnesses in observed)),
                        '身份揭晓需要先完成首登，并由本视角已确认或刚见证的具体凭据触发')
                disclosed.add((basis['subject'], basis['text']))
            readers = {(basis['subject'], basis['confirmed_identity'])} if reader_aside(guide, basis) else set()
            require(all(secret not in canonical(guide) for _, secret in secrets - disclosed - readers),
                    '在揭晓凭据之前泄露了暗身份')
            if beat['time'] == 'current' and (mode == 'action' or mode == 'perception' and owner == pov):
                observed.append((guide['observable'], {owner, *beat.get('witnesses', [])}))
        require(not entries, '本场略过人物首次出场的身份、来源或可见伏笔')


def _seen_trigger(text: str, trigger: str) -> bool:
    return _trigger_end(text, trigger) is not None


def _trigger_end(text: str, trigger: str) -> int | None:
    from nw.materials.world_history import factual_history_claim
    for segment in re.finditer(r'[^。！？!?\n]+[。！？!?]?', text):
        sentence = segment.group()
        for match in re.finditer(re.escape(trigger), sentence):
            prefix = re.split(r'[，,；;]', sentence[:match.start()])[-1]
            if not re.search(r'(?:不|没|未|无法|难以|不曾)(?:能|敢|曾|能再)?(?:确认|证明|看见|见到|证实|看到)?\s*$', prefix
                             ) and factual_history_claim(sentence, match.start(), match.end()):
                return segment.start() + match.end()
    return None


def review_checks(scene: str, pov: str, bases: dict, guides: list[dict], *, trace_trigger: bool = False) -> list[dict]:
    """The reviewer may see the secret; the writer and reviser receive only approved beats."""
    result = []
    for ref, item in bases.items():
        if item['kind'] != 'cast_reveal':
            continue
        known = next((b for b in bases.values() if b.get('confirmed_identity') == item['text']
                      and b.get('subject') == item['subject'] and b.get('audience') == pov), None)
        reveal_index = next((i for i, guide in enumerate(guides) if guide['scene'] == scene
                             and guide['narration']['basis_ref'] == ref), None)
        reveal = f'work:narration:{scene}:{reveal_index}' if reveal_index is not None else None
        trigger_checks = {}
        prerequisites = set()
        if trace_trigger and known and 'state_sha256' in known:
            prerequisites.add(known['state_sha256'])
        if trace_trigger and reveal_index is not None:
            prior = next((b for b in bases.values() if b.get('kind') == 'state' and b.get('claim') == 'fact'
                          and b.get('subject') == item['subject'] and b.get('audience') == pov
                          and b['text'] == item['trigger']), None)
            witnessed = []
            for index, guide in enumerate(guides[:reveal_index]):
                beat = guide['narration']
                if (guide['scene'] == scene and beat['time'] == 'current' and beat['mode'] in ('action','perception')
                        and pov in (beat['owner'], *beat.get('witnesses', ())) and _seen_trigger(guide['observable'], item['trigger'])):
                    witnessed.append(f'work:narration:{scene}:{index}')
            if witnessed or prior is None:
                trigger_checks['trigger_checks'] = witnessed
            elif 'state_sha256' in prior:
                prerequisites.add(prior['state_sha256'])
        asides = []
        for index, guide in enumerate(guides):
            beat = guide['narration']
            if guide['scene'] != scene or beat['owner'] is not None:
                continue
            source = bases.get(beat['basis_ref'], {})
            if reader_aside(guide, source) and source['subject'] == item['subject'] and source['confirmed_identity'] == item['text']:
                asides.append(f'work:narration:{scene}:{index}')
        result.append({'id': f'work:cast-identity:{scene}:{item["subject"]}', 'profile': 'prose_review',
            **({'narration_state_refs': sorted(prerequisites)} if prerequisites else {}),
            'binding': {'observable': '核对本稿里谁见到哪项线索，是否已到揭晓位置',
                        'check': '尚未揭晓时找出暗示的正文并检查有无同义泄露。揭晓时引证凭据、身份与获知途径。'},
            'method_artifact': {'secret': item['text'], 'trigger': item['trigger'], 'reveal': reveal,
                                'previously_known': known is not None, 'reader_asides': asides, **trigger_checks}})
    return result


def assess_hidden(checks: list[dict], rows: list[dict], draft: Draft) -> None:
    by_id = {r['id']: r for r in rows}
    for check in checks:
        if not check['id'].startswith('work:cast-identity:'):
            continue
        item = check['method_artifact']
        if item['previously_known']:
            continue
        reveal = by_id.get(item['reveal'])
        spans = [e for e in (reveal['evidence'] if reveal and reveal['status'] == 'pass' else []) if e['id'] == draft.id]
        allowed = [(e['start'], len(draft.text)) for e in spans]
        if 'trigger_checks' in item and spans:
            confirmed = []
            for key in item['trigger_checks']:
                proof = by_id.get(key)
                if proof and proof['status'] == 'pass':
                    for citation in proof['evidence']:
                        if citation['id'] != draft.id:
                            continue
                        cue = _trigger_end(citation['quote'], item['trigger'])
                        if cue is not None:
                            confirmed.append(citation['start'] + cue)
                        elif item['trigger'] not in citation['quote']:
                            confirmed.append(citation['end'])
            first_confirmation = min(confirmed, default=len(draft.text))
            allowed = [(max(e['start'], first_confirmation), len(draft.text)) for e in spans
                       if first_confirmation < e['end']]
            if not allowed:
                by_id[check['id']].update(status='failed', reason='本稿未能引证视角人物在揭晓之前实际见证的触发凭据。')
        allowed.extend((e['start'], e['end']) for key in item['reader_asides'] if by_id[key]['status'] == 'pass'
                       for e in by_id[key]['evidence'] if e['id'] == draft.id)
        for match in re.finditer(re.escape(item['secret']), draft.text):
            if not any(start <= match.start() and match.end() <= end for start, end in allowed):
                by_id[check['id']].update(status='failed', reason='本稿在获准揭晓前明写了隐藏身份。')
                break
