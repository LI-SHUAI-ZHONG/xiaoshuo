"""Source-specific workflow procedures, kept separate from scene action rules."""
import math

from nw.task_models import _text, canonical

STAGE_KEYS = {'126.9': 'timeline_process', '126.10': 'promise_process', '126.11': 'pov_process',
              '126.12': 'preflight_process', '126.16': 'usage_process'}
PROFILES = set(STAGE_KEYS.values())
COMMON = {'function', 'parameter', 'observable', 'check'}
FIELDS = {
    'timeline_process': {'anchor','unit','events'},
    'promise_process': {'entries','review_interval','payoff_min','closing'},
    'pov_process': {'protagonist','switches','review_interval','min_share','reset_sentences','opening_chars'},
    'preflight_process': {'checks'},
    'usage_process': {'records','review_interval','unit_start','unit_end'},
}
INSTRUCTIONS = {
    'timeline_process': 'anchor、unit 为具体时间锚点和单位；events 逐场含 scene、start、end、season、expected_old。'
        '时间是候选计划，start/end 为有限数字；不可倒置，按story_order核对；expected_old 为已存timeline_span或null。',
    'promise_process': 'entries 每项含 scene、promise（真实伏笔卡key/ID）、phase（plant/sleep/wake/payoff）、'
        'before、after、observable；阶段状态用 planted/sleeping/awake/paid_off，首次before为null。'
        '另填review_interval=3、payoff_min=0.8和closing布尔值；正文未核验前不提交状态。',
    'pov_process': 'protagonist 使用实际人物key/ID；switches 逐场含 scene、from_pov（首场可为null）、to_pov、reason。'
        'to_pov 须与场景相同。review_interval=5、min_share=0.7、reset_sentences=3、opening_chars=500。'
        '周期审查使用完整五章的真实字数和视角，不能用计划占比替代。',
    'preflight_process': 'checks 针对本案新建人物、世界和首场开篇逐项返回kind'
        '（character_creation/world_creation/opening/ending）、target（成员key）、artifact（相应成员完整body）。'
        '只核实际触发的前置环节，不把人物候选当作已接受事实。',
    'usage_process': 'records 逐一记录本次采用的其他资料及流程的id、planned_use；review_interval为3到5整数，'
        'unit_start为实际故事单元的起始章号，unit_end为布尔。单元结束时核对从unit_start到本章的全部实际稿件。'
        '写后效果以独立审稿的逐来源status、reason、evidence记录，后续设计读取已接受任务的效果记录。',
}


def stage_profile(key: str) -> str | None:
    return STAGE_KEYS.get(key.split('_', 1)[0])


def stage_prompt(profile: str) -> str:
    return '另填 ' + '、'.join(sorted(COMMON | FIELDS[profile])) + '。' + INSTRUCTIONS[profile]


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError('MATERIAL_PROCESS: ' + reason)


def validate_stage(output: dict, candidate: dict, profile: str, materials: list[dict],
                   existing: dict | None = None) -> None:
    _require(all(_text(output[k]) for k in COMMON), 'explain the actual workflow function and observable check')
    members = {r['key']: r for r in candidate.get('members', [])}
    kinds = {**(existing or {}), **{key: r['kind'] for key, r in members.items()}}
    scenes = {r['card']: (chapter['index'], r['story_order']) for chapter in candidate.get('chapters', [])
              for r in chapter['scenes']}
    if profile == 'timeline_process':
        _require(_text(output['anchor']) and _text(output['unit']) and isinstance(output['events'], list), 'time anchor, unit and events required')
        _require(len(output['events']) == len(scenes), 'every actual scene needs its timeline span')
        seen, ordered = set(), []
        for event in output['events']:
            _require(isinstance(event, dict) and set(event) == {'scene','start','end','season','expected_old'}, 'invalid timeline event')
            _require(_text(event['scene']) and event['scene'] in scenes and event['scene'] not in seen, 'timeline scene is missing or duplicated')
            seen.add(event['scene'])
            _require(all(type(event[k]) in (int,float) and math.isfinite(event[k]) for k in ('start','end'))
                     and event['end'] >= event['start'] and _text(event['season']), 'invalid story time or duration')
            ordered.append((scenes[event['scene']][1], event['start']))
        ordered.sort()
        _require(all(a[1] <= b[1] for a,b in zip(ordered, ordered[1:])), 'story chronology conflicts with timeline; presentation may still use flashbacks')
    elif profile == 'promise_process':
        _require(type(output['closing']) is bool and type(output['review_interval']) is int
                 and output['review_interval'] == 3 and output['payoff_min'] == .8
                 and isinstance(output['entries'], list) and bool(output['entries']), 'promise lifecycle and original review policy required')
        allowed = {'plant': ({None}, 'planted'), 'sleep': ({'planted','sleeping'}, 'sleeping'),
                   'wake': ({'planted','sleeping'}, 'awake'), 'payoff': ({'planted','sleeping','awake'}, 'paid_off')}
        seen = set()
        for event in output['entries']:
            _require(isinstance(event, dict) and set(event) == {'scene','promise','phase','before','after','observable'}, 'invalid promise event')
            _require(_text(event['scene']) and event['scene'] in scenes and _text(event['promise'])
                     and kinds.get(event['promise']) == 'promise' and _text(event['phase']) and event['phase'] in allowed
                     and _text(event['observable']), 'promise event must target a real scene and promise card')
            before, after = allowed[event['phase']]
            _require((event['before'] is None or isinstance(event['before'], str)) and event['before'] in before
                     and event['after'] == after, 'promise cannot skip its supported lifecycle')
            key = event['scene'], event['promise']
            _require(key not in seen, 'duplicate promise transition in one scene'); seen.add(key)
    elif profile == 'pov_process':
        _require(_text(output['protagonist']) and kinds.get(output['protagonist']) == 'character', 'protagonist must be a real character')
        _require(type(output['review_interval']) is int and output['review_interval'] == 5 and output['min_share'] == .7
                 and type(output['reset_sentences']) is int and output['reset_sentences'] == 3
                 and type(output['opening_chars']) is int and output['opening_chars'] == 500 and isinstance(output['switches'], list)
                 and len(output['switches']) == len(scenes), 'preserve the original POV review policy')
        seen = set()
        for switch in output['switches']:
            _require(isinstance(switch, dict) and set(switch) == {'scene','from_pov','to_pov','reason'}, 'invalid POV switch')
            _require(_text(switch['scene']) and switch['scene'] in scenes and switch['scene'] not in seen
                     and _text(switch['to_pov']) and switch['to_pov'] == members[switch['scene']]['body']['pov']
                     and (switch['from_pov'] is None or _text(switch['from_pov']) and kinds.get(switch['from_pov']) == 'character')
                     and _text(switch['reason']), 'switch must follow the actual scene viewpoint')
            seen.add(switch['scene'])
    elif profile == 'preflight_process':
        _require(isinstance(output['checks'], list), 'preflight records required')
        expected = {('character_creation' if r['kind'] == 'character' else 'world_creation', key)
                    for key,r in members.items() if r['kind'] in {'character','world'}}
        expected |= {('opening', r['card']) for ch in candidate.get('chapters', []) if ch['index'] == 1
                     for r in ch['scenes'] if r['index'] == 1}
        expected |= {('ending', key) for key,r in members.items() if r['kind'] == 'scene'
                     and any(word in str(r['body'].get('title','')) for word in ('终章','收尾'))}
        found = set()
        for check in output['checks']:
            _require(isinstance(check, dict) and set(check) == {'kind','target','artifact'} and _text(check['kind'])
                     and _text(check['target']), 'invalid preflight target')
            key = check['kind'], check['target']
            _require(key in expected and key not in found and canonical(check['artifact']) == canonical(members[check['target']]['body']),
                     'preflight must reference the actual new design artifact')
            found.add(key)
        _require(found == expected, 'every triggered creation or opening needs its own preflight record')
    elif profile == 'usage_process':
        _require(type(output['review_interval']) is int and 3 <= output['review_interval'] <= 5
                 and type(output['unit_start']) is int and 1 <= output['unit_start'] <= min(
                     (r['index'] for r in candidate.get('chapters',[])),default=1)
                 and type(output['unit_end']) is bool and isinstance(output['records'], list), 'invalid usage review period')
        expected = {r['source']['id'] for r in materials if r['request']['disposition'] == 'required'
                    and r['profile'] != 'usage_process'}
        found = set()
        for record in output['records']:
            _require(isinstance(record, dict) and set(record) == {'id','planned_use'} and _text(record['id'])
                     and record['id'] in expected and record['id'] not in found and _text(record['planned_use']), 'usage record must identify an adopted source')
            found.add(record['id'])
        _require(found == expected, 'every actual adopted method needs a pre-writing usage record')


def stage_checks(design: dict, *, scoped: bool) -> list[dict]:
    result = []
    outputs = design.get('process_bindings', {})
    scene = design.get('material_key')
    chapter = design.get('chapter_index', 1)
    ids = design.get('process_ids', {})
    for material in design.get('materials', []):
        profile, ident = material['profile'], material['source']['id']
        if profile not in PROFILES or material['request']['disposition'] != 'required':
            continue
        output = outputs.get(ident)
        _require(isinstance(output, dict), 'approved procedural artifact is missing; redesign before writing')
        value = {k: output[k] for k in COMMON}
        value['source_scope'] = output.get('source_scope', {})
        if 'layer_application' in output:
            value['layer_application'] = output['layer_application']
        artifact = output
        if not scoped:
            if profile == 'timeline_process':
                event = next(r for r in output['events'] if r['scene'] == scene)
                span = {k: event[k] for k in ('start','end','season')} | {k: output[k] for k in ('anchor','unit')}
                value['state'] = [{'entity_id': design['scene_card_id'], 'predicate': 'timeline_span', 'holder': 'WORLD',
                                   'expected_old': event['expected_old'], 'new_value': span}]
                value['observable'] = '本场时间跨度与季节：' + canonical({k:span[k] for k in ('start','end','season','unit')})
                value['check'] = '核对本场已批准时间跨度、事件顺序与季节；整体时间锚点的幕后含义留给独立审稿。'
                artifact = event
            elif profile == 'promise_process':
                events = [r for r in output['entries'] if r['scene'] == scene]
                if not events:
                    continue
                value['state'] = [{'entity_id': ids.get(r['promise'], r['promise']), 'predicate': 'promise_stage',
                    'holder': 'WORLD', 'expected_old': r['before'], 'new_value': r['after']}
                    for r in events if r['before'] != r['after']]
                value['observable'] = '；'.join(r['observable'] for r in events)
                value['check'] = '只核对本场可见的伏笔表现；后续用途和回收计划留给独立审稿。'
                artifact = events
            elif profile == 'pov_process':
                artifact = next(r for r in output['switches'] if r['scene'] == scene)
            else:
                continue
        else:
            period = output.get('review_interval', 1)
            periodic = chapter % period == 0
            chapters = list(range(max(1,chapter-period+1),chapter+1)) if periodic else [chapter]
            if profile == 'promise_process' and output['closing']:
                chapters = list(range(1,chapter+1))
            if profile == 'usage_process':
                start = output['unit_start']
                if output['unit_end'] or (chapter-start+1) % period == 0:
                    chapters = list(range(start,chapter+1))
            value['review_scope'] = {'kind': 'cross_chapter' if len(chapters)>1 else 'chapter', 'chapters': chapters}
        review = material['review']
        result.append({'id': ident + (':scope' if scoped else ':stage'), 'profile': profile,
            'source_id': ident, 'binding': value, 'process_artifact': artifact,
            'process_ids': ids, 'source_contract': review['contract'], 'source_refs': review.get('source_refs', []),
            **({'layer_contract': review['layer_contract']} if review.get('layer_contract', {}).get('execution') else {}),
            'evidence_required': review['evidence_required'] + '；核对该流程实际激活的阶段、原文数值边界和效果，不以计划代替正文。'})
    return result
