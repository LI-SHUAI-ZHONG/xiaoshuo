"""Project cast observations from independent review of the accepted scene text."""
from collections import defaultdict

from nw.models import Draft
from nw.store import Store
from nw.story_models import StateHead
from nw.task_models import canonical


PREFIX = 'work:cast-presence:'
ONSTAGE = {'action', 'speech', 'perception', 'visible'}
PROMPT = (
    'work:cast-presence: 另回 people 数组，每个该场 roster 人物各一项 '
    '{actor,mode,span,cue,reason}。按正文判断其在场行动(action)、发言(speech)、亲历(perception)、'
    '在场被看见(visible)、仅被提及或回忆(mentioned)、没有写到(absent)。'
    'span 为本项 evidence 的零基下标，cue 为原句中呈现其动作、话语、在场细节或提及的精确片段，reason 解释为何属于此人及此处的实际作用。'
    'absent 用 span=null、cue=""。他人谈起他或转述过去行为只计 mentioned。'
    'must_appear 中的人须在本稿实际登场；roster 外另列 other_named，为本稿出现名字的其他已知角色，逐人核对是否仅提及或同名误匹配。'
    '若承诺的角色缺写，或另有可辨认的未排期人物实际登场，给 failed 并解释。仅作环境描写的匿名人群不计作一个角色。'
)


def review_check(records: dict, scene: str, ids: dict, context: dict) -> dict:
    products = records['scene_design']['products']
    body = next(r['body'] for r in products['members'] if r['key'] == scene)
    names = {r['card_id']: r['body']['name'] for r in context.get('approved_cards', ()) if r['kind'] == 'character'}
    names.update({r['key']: r['body']['name'] for r in records['character_design']['products'].get('members', ())})
    people = {body['pov'], *body.get('characters', ())}
    promised = {r['actor'] for chapter in products['cast_distribution_plan'] for r in chapter['people']
                if r['scene'] == scene}
    required = sorted(ids.get(k, k) for k in promised)
    return {'id': PREFIX + scene, 'profile': 'cast_presence_review',
            'binding': {'observable': canonical({'onstage': required}),
                        'check': '用本场视角可见的行动、发言或反应呈现已安排在此出场的人物。'},
            'roster': {ids.get(k, k): names.get(k, k) for k in sorted(people)},
            'must_appear': required,
            'evidence_required': '同一场中的人物可以共享原句；逐人指出能识别其行动或发言的原文。'}


def other_named_characters(store: Store, head: StateHead, draft: Draft, roster: dict) -> dict:
    rows = store.connection.execute("""
        SELECT c.card_id, json_extract(c.body_json, '$.name') AS name
        FROM story_commits AS s JOIN json_each(s.state_json, '$.settings') AS ref
        JOIN cards AS c ON c.card_id=json_extract(ref.value, '$.card_id')
                        AND c.version=json_extract(ref.value, '$.version')
        WHERE s.branch_id=? AND s.revision=? AND c.kind='character'
          AND length(json_extract(c.body_json, '$.name'))>0 AND instr(?,json_extract(c.body_json,'$.name'))>0
        """, (head.branch_id, head.revision, draft.text))
    return {actor: name for actor, name in rows if actor not in roster}


def check_people(rule: dict, row: dict, draft: Draft) -> None:
    def require(condition: bool) -> None:
        if not condition:
            raise ValueError('MATERIAL_EVIDENCE: 人物出场核验须逐人区分实际登场、提及、缺席，并引用当前稿中属于该人的原文')

    seen = set()
    known = {**rule['roster'], **rule.get('other_named', {})}
    require(isinstance(row['people'], list))
    for person in row['people']:
        require(isinstance(person, dict) and person.keys() == {'actor', 'mode', 'span', 'cue', 'reason'})
        actor, mode, index, cue, reason = (person[k] for k in ('actor','mode','span','cue','reason'))
        require(isinstance(actor, str) and actor in known and actor not in seen
                and isinstance(mode, str) and mode in ONSTAGE | {'mentioned','absent'}
                and isinstance(reason, str) and bool(reason.strip()) and isinstance(cue, str))
        seen.add(actor)
        if mode == 'absent':
            require(index is None and cue == '')
        else:
            require(type(index) is int and 0 <= index < len(row['evidence']))
            span = row['evidence'][index]
            require(span['id'] == draft.id and len(''.join(span['quote'].split())) >= 8
                    and bool(cue.strip()) and cue in span['quote'] and reason.strip() != span['quote'].strip())
            if mode in ONSTAGE:
                require(len(cue.strip()) >= 2 and cue.strip() not in (actor, known[actor]))
                require(row['status'] != 'pass' or actor in rule['roster'])
        if row['status'] == 'pass' and actor in rule['must_appear']:
            require(mode in ONSTAGE)
    require(seen == known.keys())


def checked_people(rule: dict, row: dict) -> list[dict]:
    result = []
    known = {**rule['roster'], **rule.get('other_named', {})}
    for person in row['people']:
        if person['mode'] == 'absent':
            continue
        span = row['evidence'][person['span']]
        result.append({'actor': person['actor'], 'name': known[person['actor']],
                       'presence': 'onstage' if person['mode'] in ONSTAGE else 'mentioned',
                       'mode': person['mode'], 'reason': person['reason'], 'cue': person['cue'],
                       **{k: span[k] for k in ('start','end','quote')}})
    return result


def accepted_scene(store: Store, scene_id: str, slot: dict) -> dict:
    from nw.materials.identity_evidence import accepted_scene_checks
    from nw.story_delta import read_delta

    draft = store.get('draft', slot['draft_id'])
    if draft.scene_id != scene_id:
        raise ValueError('Accepted cast evidence points to a different scene')
    result = {'scene_id': scene_id, 'draft_id': draft.id, 'complete': False, 'people': []}
    if slot['delta_id'] is not None:
        delta = read_delta(store, slot['delta_id'])
        if delta.draft_id != draft.id:
            raise ValueError('Accepted cast evidence points to a different draft')
        accepted_scene_checks(store, draft, delta, identity=False, appearances=result)
    return result


def _planning_observation(person: dict) -> dict:
    """Keep an exact, locatable part of the passage; the review retains its full span."""
    passage = person['quote']
    offset = max(0, passage.find(person.get('cue', '')) - 28)
    start = person['start'] + offset
    excerpt = passage[offset:offset + 160]
    return {'actor': person['actor'], 'presence': person['presence'], 'mode': person['mode'],
            'reason': person['reason'][:180], 'start': start, 'end': start + len(excerpt), 'quote': excerpt}


def planning_history(store: Store, snapshot: dict, *, head: StateHead | None = None) -> dict:
    """Use the accepted slot on this branch. Reopen full review evidence only for the latest chapter or old slots."""
    slots = snapshot.get('slots', {})
    retired = set(snapshot.get('stale_plan_scenes', ()))
    pending = set()
    if head and head.branch_id != 'main':
        from nw.acceptance import promotion_impacts
        from nw.story_state import branch_row, revision_state
        branch = branch_row(store, head.branch_id)
        parent = StateHead(branch['parent_branch_id'], branch['parent_at_fork'])
        pending.update(promotion_impacts(store, revision_state(store, parent), snapshot))
    chapters = {c.id: c.index for c in store.list('chapter')}
    scheduled = sorted((chapters[s.chapter_id], s.index, s.id) for s in store.list('scene')
                       if s.id in slots and s.id not in retired and s.id not in pending)
    from nw.story_state import approved_scene_positions

    first, recent = {}, []
    uncertain = {position[0] for scene, position in approved_scene_positions(store, snapshot).items()
                 if scene not in slots or scene in pending}
    latest = scheduled[-1][0] if scheduled else None
    chapter_firsts = defaultdict(set)
    for chapter, index, scene in scheduled:
        slot = slots[scene]
        summary = slot.get('reviewed_cast')
        if chapter == latest or summary is None:
            actual = accepted_scene(store, scene, slot)
            actors = {p['actor'] for p in actual['people'] if p['presence'] == 'onstage'}
            complete = actual['complete']
            if chapter == latest:
                actual['people'] = [_planning_observation(p) for p in actual['people']]
                for person in actual['people']:
                    actor = person['actor']
                    if person['presence'] == 'mentioned':
                        person['appearance'] = 'mentioned'
                        continue
                    if actor in first and first[actor][0] < chapter:
                        appearance = 'returning'
                    else:
                        appearance = 'first_observed' if any(c < chapter for c in uncertain) else 'first'
                    person['appearance'] = appearance
                    chapter_firsts[appearance].add(actor)
                recent.append(actual)
        else:
            actors, complete = summary['onstage'], summary['complete']
        if not complete:
            uncertain.add(chapter)
        for actor in actors:
            first.setdefault(actor, [chapter, index])
    return {'first_positions': first, 'unverified_chapters': sorted(uncertain), 'chapter': latest, 'scenes': recent,
            'first': sorted(chapter_firsts['first']), 'first_observed': sorted(chapter_firsts['first_observed']),
            'returning': sorted(chapter_firsts['returning'])}
