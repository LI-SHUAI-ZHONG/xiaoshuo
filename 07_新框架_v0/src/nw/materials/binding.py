"""Turn source reviews into explicitly adopted, scope-bound design inputs."""
import json
from hashlib import sha256
from pathlib import Path

from nw.materials.catalog import show_fragment
from nw.materials.route_catalog import route
from nw.materials.layer_workflow import has_layers, validate_application
from nw.materials.process_workflow import PROFILES as PROCESS, process_prompt, validate_processes
from nw.task_models import _sha256, _text, canonical

BOOK = {'type_identity', 'type_link', 'type_combination'}
DETAILS = {
    'type_identity': {'role', 'promise', 'boundary', 'payoff'},
    'type_link': {'types', 'trigger', 'choice', 'cost', 'failure'},
    'type_combination': {'constituents', 'mechanism', 'trigger', 'choice', 'cost', 'failure'},
    'static_binding': {'source_card', 'target_card', 'restriction', 'cost'},
    'dynamic_binding': {'static_rule', 'trigger', 'choice', 'cost', 'carry', 'state'},
    'anchor': {'observer', 'object', 'beat', 'timing', 'condition'},
    'editor': set(),
    'character_editor': {'character'},
    'scope_review': {'review_scope'},
    'type_transition': {'target_card', 'type_sources', 'trigger', 'choice', 'cost', 'failure', 'state', 'knowledge_boundary'},
    'static_relation': {'source_card', 'target_card', 'mechanism', 'restriction', 'cost', 'excludes'},
    'dynamic_relation': {'source_card', 'target_card', 'trigger', 'choice', 'cost', 'failure',
                         'carry', 'state', 'static_rule', 'knowledge_boundary'},
    **{profile: set() for profile in ('world', 'character', 'plot', 'opening', 'scene',
                                      'expression', 'knowledge', 'type_expression', 'prose_review')},
}
COMMON = {'function', 'parameter', 'observable', 'check'}
_STATUSES = {'current_heading', 'current_subheading', 'reviewed_alias', 'reviewed_component'}
_BLOCKERS = {'underbound_type_combination'}
_STATE = {'entity_id', 'predicate', 'holder', 'expected_old', 'new_value'}
_TYPE_IDS = ('type_id', 'hybrid_id', 'mechanism_id', 'structure_id', 'style_id', 'tone_id', 'tag_id')


def _original_json(value: object) -> object:
    if isinstance(value, dict):
        return {key: _original_json(item) for key, item in value.items()
                if key not in ('运行层升级', 'runtime_calling_layer')}
    if isinstance(value, list):
        return [_original_json(item) for item in value]
    return value


def _type_id(value: dict) -> str | None:
    return next((value[key] for key in _TYPE_IDS if _text(value.get(key))), None)


def resolve_materials(workspace: Path, rows: list[dict]) -> list[dict]:
    if not isinstance(rows, list):
        raise ValueError('MATERIAL_SCOPE: materials must be a list')
    if rows and not (workspace / 'materials' / 'catalog.db').is_file():
        raise ValueError('MATERIAL_CATALOG_REQUIRED: frozen catalog.db is missing')
    resolved = {}
    types = set()
    for row in rows:
        if (not isinstance(row, dict) or set(row) != {'id', 'file_sha256', 'sha256', 'disposition', 'reason'}
                or not all(_sha256(row[field]) for field in ('id', 'file_sha256', 'sha256'))
                or row['id'] in resolved or not _text(row['reason'])
                or row['disposition'] not in ('required', 'deferred', 'not_applicable')):
            raise ValueError('MATERIAL_SCOPE: each source needs unique version hashes, disposition and reason')
        item = route(workspace, row['id'])
        source = item['source']
        if any(row[key] != source[key] for key in ('file_sha256', 'sha256')):
            raise ValueError(f"STALE_MATERIAL: source hashes differ for {row['id']}")
        record = {'request': row, 'source': source, 'profile': item['profile']}
        if row['disposition'] == 'required':
            original = show_fragment(workspace, row['id'])
            profile = item['profile']
            decision = item.get('adjudication')
            if decision and decision['state'] == 'stale':
                raise ValueError('STALE_MATERIAL: rebuild source and runtime-layer adjudications')
            if (item['interpretation'] not in {'reviewed', 'adjudicated'} or item['eligibility'] != 'candidate'
                    or profile not in DETAILS.keys() | PROCESS
                    or any(issue['kind'] in _BLOCKERS for issue in item['issues'])):
                raise ValueError(f"MATERIAL_UNQUALIFIED: {source['key']} ({row['id']})")
            review = item['source_review']
            if review is None:
                review = {key: decision[key] for key in ('meaning', 'boundary', 'evidence_required', 'related',
                                                        'source_refs', 'conditions', 'contract')}
                review['adjudication_policy'] = 'material-adjudication-v1'
            if decision and decision.get('layer_contract', {}).get('execution'):
                review = {**review, 'layer_contract': decision['layer_contract']}
            record.update(review=review, endpoints=[])
            if profile == 'type_identity':
                fields = json.loads(original['text'])
                if decision:
                    fields = _original_json(fields)
                logical_id = _type_id(fields)
                expected = decision['contract'].get('scoped_id', {}).get('original_id', source['key']) if decision else source['key']
                if logical_id != expected or not _text(fields.get('canonical_name')):
                    raise ValueError(f"MATERIAL_UNQUALIFIED: unresolved type identity for {source['key']}")
                if logical_id in types:
                    raise ValueError(f"MATERIAL_CONFLICT: select one version of {logical_id}")
                types.add(logical_id)
                record['original'] = fields
            elif profile == 'type_combination':
                record['original'] = _original_json(json.loads(original['text']))
            elif profile == 'type_link':
                fields = json.loads(original['text'])
                if decision:
                    fields = _original_json(fields)
                if not _text(fields.get('source_id')) or not _text(fields.get('target_id')):
                    raise ValueError(f"MATERIAL_UNQUALIFIED: unresolved type endpoints for {source['key']}")
                record['original'] = fields
            elif profile in ('static_binding', 'dynamic_binding'):
                endpoints = item['network_identity']
                if {endpoint['side'] for endpoint in endpoints} != {'source', 'target'} or len(endpoints) != 2:
                    raise ValueError(f"MATERIAL_ENDPOINT: both source endpoints must be verified for {source['key']}")
                for endpoint in endpoints:
                    review = endpoint['review']
                    refs = [review['location']] if review and 'location' in review else [
                        ref for ref in endpoint['locations'] if ref['layer'] == 'baseline']
                    if endpoint['status'] not in _STATUSES or not refs:
                        raise ValueError(f"MATERIAL_ENDPOINT: unresolved {endpoint['label']}")
                    for ref in refs:
                        found = show_fragment(workspace, ref['fragment_id'])
                        data = found['text'].encode('utf-8')
                        left, right = ref['byte_start'] - found['byte_start'], ref['byte_end'] - found['byte_start']
                        if (found['source_id'] != ref['source_id'] or not 0 <= left < right <= len(data)
                                or sha256(data[left:right]).hexdigest() != ref['sha256']):
                            raise ValueError(f"STALE_MATERIAL: endpoint source changed for {endpoint['label']}")
                    record['endpoints'].append({'side': endpoint['side'], 'label': endpoint['label'],
                                                'status': endpoint['status'], 'locations': refs})
                fields = json.loads(original['text'])
                record['original'] = {k: v for k, v in fields.items() if k != '运行层升级'}
            elif profile in ('static_relation', 'dynamic_relation'):
                record['endpoints'] = decision['contract']['identities']
                record['original'] = _original_json(json.loads(original['text']))
            elif decision:
                record['original'] = (_original_json(json.loads(original['text']))
                                      if source['family'] in ('types', 'type_links') else decision['contract'])
            else:
                record['original'] = original['text']
            if decision and decision.get('contract', {}).get('effective_original'):
                record['original'] = decision['contract']['effective_original']
        resolved[row['id']] = record
    return list(resolved.values())


def verify_materials(workspace: Path, materials: list[dict]) -> None:
    if materials and canonical(materials) != canonical(resolve_materials(
            workspace, [record['request'] for record in materials])):
        raise ValueError('STALE_MATERIAL: source interpretation or endpoint identity changed')


def required_for(materials: list[dict], *, book: bool) -> dict[str, dict]:
    return {row['source']['id']: row for row in materials
            if row['request']['disposition'] == 'required' and (row['profile'] in BOOK) == book
            and row['profile'] not in PROCESS}


def scene_routes(materials: list[dict], deferrals: dict | None = None) -> dict[str, dict]:
    return {ident: row for book in (True, False) for ident, row in required_for(materials, book=book).items()
            if ident not in (deferrals or {})}


def material_prompt(materials: list[dict], *, book: bool, deferrals: dict | None = None) -> str:
    rows = required_for(materials, book=True) if book else scene_routes(materials, deferrals)
    process_text = process_prompt(materials, book=book)
    if not rows:
        return process_text
    fields = {}
    for ident, row in rows.items():
        required = {'disposition', 'reason'} | COMMON if not book and row['profile'] in BOOK else COMMON | DETAILS[row['profile']]
        if row['review'].get('adjudication_policy'):
            required |= {'source_scope'}
        if has_layers(row):
            required |= {'layer_application'}
        fields[ident] = sorted(required)
    shape = ('按资料 ID 键入本书绑定' if book else '按每个 scene 的本地 key 再按资料 ID 键入场景绑定')
    return process_text + (' 每个方案另加 material_bindings，' + shape + '。字段表：' + canonical(fields) +
            '。各字段填写具体内容。observable、check、restriction、cost、trigger、choice、object、'
            'beat、timing、condition 只填写该 POV 允许在本场观察或行动的内容。'
            'type_link 的 types 按原文起点到终点填写两个已采用的类型来源 ID。静态端点用现有或本案卡 key，'
            'type_combination 的 constituents 为原合同各组成项 root_ids 中选定的确切来源 ID，'
            '每个原始组成ID至少选择一份等义来源，并在 mechanism 说明各组成项如何协同。'
            '静态绑定两端分别是人物及悬念卡。动态 static_rule 是本场前置静态资料 ID。'
            '动态 state 给出至少一项 WORLD 事实和一项具体人物所知，每项含 entity_id（悬念卡 key/ID）、'
            'predicate、holder（WORLD 或人物卡 key/ID）、expected_old、new_value，'
            '值是 JSON，必须确实变化。锚点 observer 用该场 POV 的人物卡 key/ID。'
            '人物一致性 character 用该场出场人物的卡 key/ID。'
            'scope_review 的 review_scope 含 kind（chapter、cross_chapter 或 book）与 chapters（章号整数数组）。'
            'kind 必须符合原合同 evidence_scope；单章选本章，跨章至少两章且以本章为最后一章。'
            '原合同的 chapter_count 指定章数，consecutive 要求章号连续；scene_indices 指定需核对的场次。'
            '全书另填 expected_chapters，列出从第一章到总章数的完整范围；这是供作者确认的完稿范围，不能用局部章替代。'
            'type_transition 的 type_sources 是已采用类型来源ID数组，target_card 是变化目标卡。'
            'state 给出该目标的实际变化，须遵守原 allowed_fields、requires_rules、excludes_rules 及非保证边界。'
            'static_relation 和 dynamic_relation 的 source_card、target_card 使用本案或已有的项目卡 ID。'
            'dynamic_relation 的 static_rule 在原文为静态派生时填写对应已采用静态边的资料 ID，'
            '原始动态边填空字符串。state 至少写一项目标实体的 WORLD 事实变化，'
            '其他人物所知仅在正文有获取证据时填写，knowledge_boundary 说明知情范围。'
            '细化时可对某场标记 deferred 或 not_applicable，只填 disposition 和 reason。'
            '其余场按字段表提交，书级类型承诺另填 selected 和 reason。'
            '本方案中每条资料至少在一场落实，作者已按范围延后的条目不在字段表中。'
            '有 source_scope 时，以 review.contract.obligations 的每个来源字段 ID 为键，'
            '填写 disposition（required 或 not_applicable）和 reason，解释本场选择及条件边界。'
            '每个来源字段均需处置，至少采用一项具体的定义、动作或判据。'
            '有 layer_application 时填写 trigger、operation、result、verification，分别说明当前项目的'
            '激活条件、具体执行、应产生的效果及证据判据；每项至少八个非空白字符，不能复述条目名称或套用同一段话。'
            '按 review.layer_contract.execution 的 domain 和 evidence_kind 转化；拒绝字段仅作差异依据，'
            '静态关系核查约束，动态关系核查实际变化，锚点核查视角观察，叙述规则核查稿件范围。'
            '沿用已确认的书级类型承诺，缺适用依据时停止并明确说明缺口。')


def validate_bindings(candidate: dict, scope: str, members: dict, existing: dict, materials: list[dict],
                      deferrals: dict | None = None) -> None:
    validate_processes(candidate, scope, materials, deferrals, existing=existing)
    book = scope == 'book'
    required = required_for(materials, book=True) if book else scene_routes(materials, deferrals)
    if not required:
        if 'material_bindings' in candidate:
            raise ValueError('MATERIAL_DESIGN: no bindings were requested for this stage')
        return
    bindings = candidate.get('material_bindings')
    scenes = {key: row['body'] for key, row in members.items() if row['kind'] == 'scene'}
    if not isinstance(bindings, dict) or not book and bindings.keys() != scenes.keys():
        raise ValueError('MATERIAL_DESIGN: every planned scene requires its own bindings')
    kinds = {**existing, **{key: row['kind'] for key, row in members.items()}}
    used = set()
    for scene, mappings in ({None: bindings} if book else bindings).items():
        if not isinstance(mappings, dict) or mappings.keys() != required.keys():
            raise ValueError('MATERIAL_DESIGN: missing or unrequested material IDs')
        for ident, row in required.items():
            profile = row['profile']
            value = mappings[ident]
            if not book and isinstance(value, dict) and value.get('disposition') in ('deferred', 'not_applicable'):
                if value.keys() != {'disposition', 'reason'} or not _text(value['reason']):
                    raise ValueError('MATERIAL_DESIGN: record the reason for scene-specific exclusion')
                continue
            used.add(ident)
            source_fields = {'source_scope'} if row['review'].get('adjudication_policy') else set()
            if source_fields:
                _validate_source_scope(value, row['review']['contract'].get('obligations', []))
            if has_layers(row):
                validate_application(value, row)
                source_fields |= {'layer_application'}
            if not book and profile in BOOK:
                if not isinstance(value, dict) or value.get('disposition') != 'selected':
                    raise ValueError('MATERIAL_DESIGN: mark whether each scene serves the book commitment')
                fields = {'disposition', 'reason'} | COMMON | source_fields
                if value.keys() != fields or not all(_text(value[key]) for key in fields - source_fields):
                    raise ValueError('MATERIAL_DESIGN: incomplete book commitment in scene')
                continue
            fields = COMMON | DETAILS[profile] | source_fields
            if (not isinstance(value, dict) or value.keys() != fields or
                    not all(_text(value[key]) for key in fields - {'types', 'type_sources', 'constituents', 'state', 'static_rule', 'source_scope', 'layer_application', 'review_scope'})
                    or 'static_rule' in fields and not isinstance(value['static_rule'], str)):
                raise ValueError(f"MATERIAL_DESIGN: incomplete {profile} binding for {row['source']['key']}")
            if profile == 'scope_review':
                _validate_review_scope(value['review_scope'], row, candidate, scene)
            if profile == 'type_transition':
                _validate_type_transition(value, row, materials, kinds)
            if profile == 'type_link':
                selected = {key: _type_id(record['original']) for key, record in required.items()
                            if record['profile'] == 'type_identity'}
                types = value['types']
                if (not isinstance(types, list) or len(types) != 2 or not all(
                        _text(key) and key in selected and key in row['review']['related'] for key in types)
                        or [selected[key] for key in types] != [row['original']['source_id'], row['original']['target_id']]):
                    raise ValueError('MATERIAL_DESIGN: type link requires its two reviewed endpoints in source order')
            if profile == 'type_combination':
                members = value['constituents']
                groups = row['review']['contract']['constituents']
                allowed = {ident for group in groups for ident in group['root_ids']}
                if (not isinstance(members, list) or not members or not all(_text(ident) for ident in members)
                        or len(members) != len(set(members)) or not set(members) <= allowed
                        or any(not set(group['root_ids']).intersection(members) for group in groups)):
                    raise ValueError('MATERIAL_DESIGN: combination must bind every exact original constituent')
            if profile == 'static_binding' and (
                    kinds.get(value['source_card']) != 'character'
                    or kinds.get(value['target_card']) not in {'promise', 'plot'}):
                raise ValueError('MATERIAL_DESIGN: static edge needs real character and suspense cards')
            if profile == 'anchor' and value['observer'] != scenes[scene]['pov']:
                raise ValueError('MATERIAL_DESIGN: anchor observer must be the scene POV')
            if profile == 'character_editor' and value['character'] not in {
                    scenes[scene]['pov'], *scenes[scene]['characters']}:
                raise ValueError('MATERIAL_DESIGN: character review requires a character in this scene')
            if profile in ('static_relation', 'dynamic_relation'):
                if (value['source_card'] not in kinds or value['target_card'] not in kinds
                        or value['source_card'] == value['target_card']):
                    raise ValueError('MATERIAL_DESIGN: relation needs two distinct existing project cards')
                if profile == 'dynamic_relation':
                    static_id = value['static_rule']
                    source_contract = row['review']['contract']
                    valid_types = source_contract['valid_types']
                    chosen_types = {entry['original'].get('canonical_name') for entry
                                    in required_for(materials, book=True).values() if isinstance(entry['original'], dict)}
                    if valid_types and not chosen_types.intersection(valid_types):
                        raise ValueError('MATERIAL_DESIGN: dynamic relation requires an applicable adopted type')
                    if source_contract['generated_from_static']:
                        parent = required.get(static_id)
                        upstream = mappings.get(static_id, {})
                        if (static_id not in row['review']['related'] or parent is None
                                or parent['profile'] not in ('static_relation', 'static_binding')
                                or upstream.get('source_card') != value['source_card']
                                or upstream.get('target_card') != value['target_card']):
                            raise ValueError('MATERIAL_DESIGN: generated dynamic relation needs its exact project static relation')
                    elif static_id:
                        raise ValueError('MATERIAL_DESIGN: original dynamic relation has no asserted static derivation')
                    _validate_state(value['state'], value['target_card'], kinds, require_knowledge=False)
            if profile == 'dynamic_binding':
                valid_types = row['original'].get('valid_types', [])
                chosen_types = {entry['original']['canonical_name'] for entry in required_for(materials, book=True).values()
                                if entry['profile'] == 'type_identity'}
                if valid_types and not chosen_types.intersection(valid_types):
                    raise ValueError('MATERIAL_DESIGN: dynamic rule requires an applicable adopted type')
                parent = required.get(value['static_rule'])
                if (parent is None or parent['profile'] != 'static_binding'
                        or value['static_rule'] not in row['review']['related']
                        or parent['endpoints'] != row['endpoints']):
                    raise ValueError('MATERIAL_DESIGN: dynamic edge needs its exact adopted static dependency')
                static = mappings[value['static_rule']]
                if not isinstance(static, dict) or not _text(static.get('target_card')):
                    raise ValueError('MATERIAL_DESIGN: invalid dynamic target')
                scene_people = {scenes[scene]['pov'], *scenes[scene]['characters']}
                if not _text(static.get('source_card')) or static['source_card'] not in scene_people:
                    raise ValueError('MATERIAL_DESIGN: dynamic source character must take part in the scene')
                _validate_state(value['state'], static['target_card'], kinds)
    if used != required.keys():
        missing = ', '.join(required[key]['source']['key'] for key in sorted(required.keys() - used))
        raise ValueError(f'MATERIAL_DESIGN: assign a scene or record an explicit author deferral for {missing}')


def _validate_source_scope(value: object, obligations: list[dict]) -> None:
    scope = value.get('source_scope') if isinstance(value, dict) else None
    required = {item['id']: item for item in obligations}
    if not isinstance(scope, dict) or scope.keys() != required.keys():
        raise ValueError('MATERIAL_DESIGN: account for every original condition, exception and instruction')
    selected = []
    for ident, choice in scope.items():
        if (not isinstance(choice, dict) or set(choice) != {'disposition','reason'}
                or choice['disposition'] not in ('required','not_applicable') or not _text(choice['reason'])):
            raise ValueError('MATERIAL_DESIGN: source field applicability requires a disposition and reason')
        if choice['disposition'] == 'required':
            selected.append(required[ident]['kind'])
    if required and not any(kind in ('definition','instruction','check','condition','effect') for kind in selected):
        raise ValueError('MATERIAL_DESIGN: select an operative part of the original contract')


def _validate_state(state: object, target: str, kinds: dict, *, require_knowledge: bool = True) -> None:
    if not isinstance(state, list) or not state:
        raise ValueError('MATERIAL_DESIGN: dynamic transition requires state and knowledge changes')
    keys = set()
    for item in state:
        if (not isinstance(item, dict) or item.keys() != _STATE or item['entity_id'] != target
                or not _text(item['predicate']) or not _text(item['holder'])
                or item['holder'] != 'WORLD' and kinds.get(item['holder']) != 'character'
                or item['new_value'] is None or canonical(item['expected_old']) == canonical(item['new_value'])):
            raise ValueError('MATERIAL_DESIGN: invalid dynamic transition or knowledge holder')
        key = (item['holder'], item['predicate'])
        if key in keys:
            raise ValueError('MATERIAL_DESIGN: duplicate dynamic state target')
        keys.add(key)
    if not any(key[0] == 'WORLD' for key in keys) or require_knowledge and not any(key[0] != 'WORLD' for key in keys):
        raise ValueError('MATERIAL_DESIGN: dynamic transition requires both world and character evidence')


def _validate_review_scope(value: object, row: dict, candidate: dict, scene: str) -> None:
    scope = row['review']['contract']['evidence_scope']
    kind = scope['kind']
    keys = {'kind', 'chapters'} | ({'expected_chapters'} if kind == 'book' else set())
    if not isinstance(value, dict) or set(value) != keys or value['kind'] != kind:
        raise ValueError('MATERIAL_DESIGN: scope must match the complete original evidence range')
    chapters = value['chapters']
    current = next((chapter['index'] for chapter in candidate['chapters']
                    if any(item['card'] == scene for item in chapter['scenes'])), None)
    if (not isinstance(chapters, list) or not chapters
            or any(type(number) is not int or number < 1 for number in chapters)
            or chapters != sorted(set(chapters)) or current not in chapters
            or kind == 'chapter' and chapters != [current]
            or kind == 'cross_chapter' and (len(chapters) < 2 or chapters[-1] != current)
            or kind == 'book' and (type(value['expected_chapters']) is not int
                or value['expected_chapters'] < 1 or len(chapters) != value['expected_chapters']
                or chapters[0] != 1 or chapters[-1] != value['expected_chapters'])):
        raise ValueError('MATERIAL_DESIGN: chapter, cross-chapter and full-book scopes need their actual complete range')
    if scope.get('consecutive') and chapters[-1] - chapters[0] + 1 != len(chapters):
        raise ValueError('MATERIAL_DESIGN: original review scope needs consecutive chapters')
    if scope.get('chapter_count', len(chapters)) != len(chapters):
        raise ValueError('MATERIAL_DESIGN: chapter count must match the exact original review scope')


def _validate_type_transition(value: dict, row: dict, materials: list[dict], kinds: dict) -> None:
    contract = row['review']['contract']
    selected = {ident: record for ident, record in required_for(materials, book=True).items()
                if record['profile'] == 'type_identity'}
    sources = value['type_sources']
    if (not isinstance(sources, list) or not sources or not all(_text(ident) and ident in selected for ident in sources)
            or len(sources) != len(set(sources)) or contract.get('applicable_type_ids') and not any(
                _type_id(selected[ident]['original']) in contract['applicable_type_ids'] for ident in sources)):
        raise ValueError('MATERIAL_DESIGN: type method requires a matching adopted type')
    if kinds.get(value['target_card']) not in {'character', 'world', 'plot', 'promise'}:
        raise ValueError('MATERIAL_DESIGN: type transition requires a real project target')
    _validate_state(value['state'], value['target_card'], kinds, require_knowledge=False)
    if contract.get('allowed_fields') and any(item['predicate'] not in contract['allowed_fields'] for item in value['state']):
        raise ValueError('MATERIAL_DESIGN: state predicate is outside original allowed_fields')
    adopted = {record['review'].get('contract', {}).get('scoped_id', {}).get('original_id')
               for record in materials if record['request']['disposition'] == 'required'}
    if not set(contract['requires_rules']) <= adopted or set(contract['excludes_rules']) & adopted:
        raise ValueError('MATERIAL_DESIGN: original required or excluded type rule conflicts with this selection')


def translate_bindings(bindings: dict, ids: dict[str, str]) -> dict:
    result = {}
    for ident, row in bindings.items():
        value = dict(row)
        for field in ('source_card', 'target_card', 'observer', 'character'):
            if field in row:
                value[field] = ids[row[field]]
        if 'state' in row:
            value['state'] = [
                {**item, 'entity_id': ids[item['entity_id']], 'holder': ids.get(item['holder'], item['holder'])}
                for item in row['state']]
        result[ident] = value
    return result

