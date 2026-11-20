"""Stage-sized model inputs backed by complete immutable source snapshots."""
from collections.abc import Iterable
from functools import lru_cache
import re

from nw.materials.binding import BOOK
from nw.task_models import canonical, content_sha256

POLICY='stage-material-input-v1'
LEGACY_STEP_SOURCE_POLICY = 'step-material-selection-v1'
STEP_SOURCE_POLICY = 'step-material-selection-v2'
_STEP_HEADING = re.compile(r'^#{2,6}\s+(.+?)\s*$')
_ASCII_HEAD_PREFIX = re.compile(r'^([A-Z][A-Z0-9_.-]+)\s+\S')
_STEP_INTRO = re.compile(r'^【[^】\r\n]+的资料】$')
_DYN_ROW = re.compile(r'^\d+｜\{"id"\s*:\s*"(C\d{5})"')
_COMBO_ROW = re.compile(r'^\d+｜(?:design_ready|blocked|reference)｜\{"[a-z_]*id"\s*:\s*"([^"]+)"')
_ANCHOR_ROW = re.compile(r'^\d+｜\|\s*([A-Z]+\d+\.\d+)\s*\|')
_ORIG_JSON_ROW = re.compile(r'^【原文行\s*\d+】\{"[a-z_]*id"\s*:\s*"([^"]+)"')
_JSON_BLOCK_ID = re.compile(r'^\s*"(?:stable_id|filter_id|rule_id)"\s*:\s*"([^"]+)"')
_STEP_SOURCE_LINE = re.compile(r'^【原文位置】[^\n]*?第\s*(\d+)(?:\s*[–—-]\s*\d+)?\s*行\s*$')


def _add_usage(excerpts: dict[str, list[tuple[int | None, list[str]]]], key: str, lines: list[str],
               source_line: int | None = None) -> None:
    cleaned = [ln.rstrip() for ln in lines if ln.strip()]
    if not cleaned:
        return
    if cleaned[0] in ('【本步用法】', '【本条用法】'):
        body = cleaned[1:]
    elif cleaned[0].startswith(('【本步用法】', '【本条用法】')):
        head_rest = cleaned[0][6:].strip()
        body = ([head_rest] if head_rest else []) + cleaned[1:]
    else:
        body = cleaned
    if body:
        excerpts.setdefault(key, []).append((source_line, body))


def step_material_prompt(prompt: str, material: str, keys: Iterable[str]) -> str:
    """Add current-step instructions for the source keys in the work package."""
    if not material:
        return prompt
    material = material.lstrip()
    first, _, rest = material.partition('\n')
    if _STEP_INTRO.fullmatch(first):
        intro = rest.split('\n\n', 1)[0].strip()
        if intro and not intro.startswith(('#', '【')):
            prompt += '\n\n' + first + '\n' + intro

    wanted = {key for key in keys if isinstance(key, str) and key}
    if not wanted:
        return prompt

    uses = _step_uses(material, wanted)
    if uses:
        sections = '\n\n'.join(f'### {key}\n【本步用法】\n{use}' for key, use in uses.items())
        prompt += '\n\n按当前步骤和已给来源执行下列用法。\n' + sections
    return prompt


def _connection_uses(material: str, wanted: set[str] | None = None) -> dict[str, str]:
    if '《类型连接》原条按需要读取' not in material:
        return {}
    from nw.materials.steps import type_connections
    stages = {stage for stage in type_connections.STEPS if (instructions := type_connections.step_instructions(stage))
              and instructions in material}
    records = type_connections.records()
    return {key: type_connections.record_use(entry[1]['original'])[1]
            for key in (records if wanted is None else wanted)
            if (entry := records.get(key)) is not None and entry[0] in stages}


def _step_excerpts(material: str, wanted: set[str], *, connections: dict[str, str] | None = None
                   ) -> dict[str, list[tuple[int | None, list[str]]]]:
    excerpts: dict[str, list[tuple[int | None, list[str]]]] = {}
    titles: list[str] = []
    instructions: list[str] | None = None
    instruction_targets: list[str] = []
    group_defs: dict[str, str] = {}
    source_line: int | None = None

    def flush(*, next_source: bool = False) -> None:
        nonlocal instructions, instruction_targets, source_line
        if instructions is not None and instruction_targets:
            for target in instruction_targets:
                if target in group_defs:
                    _add_usage(excerpts, target, [f'原表定义：{group_defs[target]}', *instructions], source_line)
                else:
                    _add_usage(excerpts, target, instructions, source_line)
        instructions = None
        instruction_targets = []
        if next_source:
            source_line = None

    for line in material.splitlines():
        if match := _STEP_HEADING.fullmatch(line):
            flush(next_source=True)
            head = match[1]
            titles = [head]
            if m_ascii := _ASCII_HEAD_PREFIX.match(head):
                titles.append(m_ascii[1])
            group_defs = {}
            continue
        if match := _ORIG_JSON_ROW.match(line):
            flush(next_source=True)
            titles = [match[1]]
            group_defs = {}
            continue
        if match := _DYN_ROW.match(line):
            flush(next_source=True)
            titles = [match[1]]
            continue
        if match := _COMBO_ROW.match(line):
            flush(next_source=True)
            titles = [match[1]]
            continue
        if match := _ANCHOR_ROW.match(line):
            flush(next_source=True)
            titles = [match[1]]
            continue
        if line.startswith('【原文位置】'):
            flush(next_source=True)
            if match := _STEP_SOURCE_LINE.fullmatch(line):
                source_line = int(match[1])
            continue
        if instructions is None and (match := _JSON_BLOCK_ID.match(line)):
            if match[1] in wanted and match[1] not in titles:
                titles.append(match[1])
            continue
        if line[:1].isdigit() and '｜' in line and not line.startswith('【'):
            parts = line.split('｜')
            if len(parts) >= 9 and parts[0].isdigit() and parts[1].isdigit():
                flush(next_source=True)
                edge_key = f'{parts[2].strip()} / {parts[3].strip()} / {parts[4].strip()}'
                if len(parts) >= 10 and parts[9].strip():
                    titles = []
                    if edge_key in wanted:
                        _add_usage(excerpts, edge_key, [parts[9].strip()])
                else:
                    titles = [edge_key]
                continue
        if line[:1].isdigit() and '|' in line and '｜' not in line:
            cols = [c.strip() for c in line.split('|')]
            if cols[0].isdigit() and len(cols) >= 3:
                flush(next_source=True)
                if len(cols) == 3:
                    if cols[1] in wanted:
                        group_defs[cols[1]] = cols[2]
                    continue
                idx = 2 if cols[1] in ('design_ready', 'blocked', 'reference') and len(cols) >= 5 else 1
                row_id, row_use = cols[idx], cols[-1]
                if row_use and not row_use.startswith('{'):
                    if row_id in wanted:
                        _add_usage(excerpts, row_id, [row_use])
                    if len(cols) == 4 and cols[2] in wanted and cols[2] != row_id:
                        _add_usage(excerpts, cols[2], [row_use])
                continue
        if line.startswith(('【本步用法】', '【本条用法】')):
            flush()
            targets = [t for t in titles if t in wanted]
            for gid in group_defs:
                if gid in wanted and gid not in targets:
                    targets.append(gid)
            if targets:
                instructions = [line]
                instruction_targets = targets
        elif instructions is not None:
            if line.startswith('【'):
                flush()
            elif line.strip():
                instructions.append(line)
    flush()

    connections = _connection_uses(material, wanted) if connections is None else connections
    for key in wanted:
        if key not in excerpts and key in connections:
            _add_usage(excerpts, key, [connections[key]])

    return excerpts


def _step_uses(material: str, wanted: set[str], *, connections: dict[str, str] | None = None) -> dict[str, str]:
    return {key: '\n'.join(dict.fromkeys(line for _, lines in groups for line in lines))
            for key, groups in _step_excerpts(material, wanted, connections=connections).items()}


def extract_step_keys(material: str) -> set[str]:
    """Return all source keys that have explicit in-step usage in material."""
    if not material:
        return set()
    found: set[str] = set()
    titles: list[str] = []
    group_defs: set[str] = set()
    for line in material.splitlines():
        if match := _STEP_HEADING.fullmatch(line):
            head = match[1]
            titles = [head]
            if m_ascii := _ASCII_HEAD_PREFIX.match(head):
                titles.append(m_ascii[1])
            group_defs = set()
            continue
        if match := _ORIG_JSON_ROW.match(line):
            titles = [match[1]]
            group_defs = set()
            continue
        if match := _DYN_ROW.match(line):
            titles = [match[1]]
            continue
        if match := _COMBO_ROW.match(line):
            titles = [match[1]]
            continue
        if match := _ANCHOR_ROW.match(line):
            titles = [match[1]]
            continue
        if match := _JSON_BLOCK_ID.match(line):
            if match[1] not in titles:
                titles.append(match[1])
            continue
        if line[:1].isdigit() and '｜' in line and not line.startswith('【'):
            parts = line.split('｜')
            if len(parts) >= 9 and parts[0].isdigit() and parts[1].isdigit():
                edge_key = f'{parts[2].strip()} / {parts[3].strip()} / {parts[4].strip()}'
                if len(parts) >= 10 and parts[9].strip():
                    titles = []
                    found.add(edge_key)
                else:
                    titles = [edge_key]
                continue
        if line[:1].isdigit() and '|' in line and '｜' not in line:
            cols = [c.strip() for c in line.split('|')]
            if cols[0].isdigit() and len(cols) >= 3:
                if len(cols) == 3:
                    if cols[1]:
                        group_defs.add(cols[1])
                    continue
                idx = 2 if cols[1] in ('design_ready', 'blocked', 'reference') and len(cols) >= 5 else 1
                row_id, row_use = cols[idx], cols[-1]
                if row_use and not row_use.startswith('{'):
                    if row_id:
                        found.add(row_id)
                    if len(cols) == 4 and cols[2] and cols[2] != row_id:
                        found.add(cols[2])
                continue
        if line.startswith(('【本步用法】', '【本条用法】')):
            found.update(titles)
            found.update(group_defs)
    return found


@lru_cache(maxsize=32)
def step_uses(material: str) -> dict[str, str]:
    """Read the authored step uses, including its bundled type connection data."""
    connections = _connection_uses(material)
    return _step_uses(material, extract_step_keys(material) | connections.keys(), connections=connections)


@lru_cache(maxsize=32)
def step_uses_by_line(material: str) -> dict[str, dict[int | None, str]]:
    """Keep instructions attached to their explicitly authored source positions."""
    connections = _connection_uses(material)
    result = {}
    for key, groups in _step_excerpts(material, extract_step_keys(material) | connections.keys(),
                                      connections=connections).items():
        by_line: dict[int | None, list[str]] = {}
        for source_line, lines in groups:
            by_line.setdefault(source_line, []).extend(lines)
        result[key] = {source_line: '\n'.join(dict.fromkeys(lines)) for source_line, lines in by_line.items()}
    return result


def check_source_keys(checks: Iterable[dict]) -> set[str]:
    keys = set()
    for check in checks:
        if key := check.get('source_contract', {}).get('key'):
            keys.add(key)
        refs = [*check.get('source_refs', ()),
                *(method['source'] for method in check.get('method_sources', ()))]
        keys.update(key for ref in refs if (key := ref.get('key') or ref.get('fragment_key')))
    return keys


def _reference(value: dict) -> dict:
    return {k:v for k,v in value.items() if k in {'id','key','original_id','locator','span'}}


def _compact(value: object) -> object:
    if isinstance(value,list):
        return [_compact(v) for v in value]
    if not isinstance(value,dict):
        return value
    result={}
    obligations={v['id'] for v in value.get('obligations',[]) if isinstance(v,dict) and 'id' in v}
    for key,item in value.items():
        if key in {'ref','source_ref','source_pin','replacement_ref','original_reference'} and isinstance(item,dict):
            result[key]=_reference(item)
        elif key=='source_refs' and isinstance(item,list):
            result[key]=[_reference(v) if isinstance(v,dict) else v for v in item]
        elif key=='original_fields_sha256':
            continue
        elif key!='obligations' and obligations and isinstance(item,list) and item and all(
                isinstance(v,dict) and isinstance(v.get('ref'),dict) and v['ref'].get('id') in obligations for v in item):
            # Exact field text remains once, in obligations, with its stable ID.
            continue
        else:
            result[key]=_compact(item)
    return result


def model_material(row: dict, *, book: bool) -> dict:
    source=row['source']
    result={key:row[key] for key in ('request','profile')}
    result['source']={key:source[key] for key in ('id','key','family','fragment_id','file_sha256','sha256')}
    if row['request']['disposition']!='required':
        return result
    review=row['review']
    active=not book or row['profile'] in BOOK | {'preflight_process'}
    if not active:
        result['review']={key:review[key] for key in ('meaning','boundary','evidence_required')}
        result['stage_use']='后续章场细化时读取完整规则；当前书级不执行此项场景绑定。'
        return result
    result['review']=_compact(review)
    original=row.get('original')
    if original is not None:
        if isinstance(original,dict) and canonical(original)==canonical(review.get('contract',{})):
            result['original_contract_in_review']=True
        else:
            result['original']=_compact(original)
    if row.get('endpoints'):
        result['endpoints']=_compact(row['endpoints'])
    layer=result['review'].get('layer_contract')
    if layer:
        # Rejected legacy templates remain in the frozen full snapshot. Only
        # valid current-stage semantics and execution requirements are sent.
        result['review']['layer_contract']={
            'policy':layer['policy'],'owner_id':layer['owner_id'],'execution':layer['execution'],
            'aligned_fields':[field for pair in layer['pairs'] for field in pair['aligned_fields']],
            'source_anchors':[anchor for pair in layer['pairs'] for anchor in pair['source_anchors']],
            'legacy_rejected_fields_are_not_execution_instructions':True}
    return result


def model_package(package: dict) -> dict:
    result={key:value for key,value in package.items() if key not in {
        'material_recall','material_input','stage_materials','stage_source_policy','chapter_handoff','chapter_summary','chapter_reviews',
        'type_hierarchy_enabled','type_source_scope_enabled','type_name_evidence_enabled','governance_inputs',
        'dynamic_reference_checks','dynamic_screening_enabled','scene_source_binding_policy','action_state_policy',
        'action_template_priority_enabled','network_prerequisite_policy','multi_action_policy','network_layer_policy',
        'early_network_policy','same_stage_network_policy'}}
    if package.get('materials'):
        result['materials']=[model_material(row,book=package['scope']=='book') for row in package['materials']]
        result['material_input']={'policy':POLICY,'full_sources_frozen_for_verification':True}
    if package.get('material_work'):
        from nw.materials.work_contract import compact_session
        result['material_work']=compact_session(package['material_work'])
    if isinstance(parent_work := package.get('parent_material_work'), dict):
        compact_stages = []
        for st in parent_work.get('stages', ()):
            if isinstance(st, dict):
                entry = {k: st[k] for k in ('stage', 'task_id', 'sha256', 'source_ids', 'inputs') if k in st}
                if isinstance(prods := st.get('products'), dict):
                    entry['products'] = {k: v for k, v in prods.items() if k != '_criteria'}
                compact_stages.append(entry)
        result['parent_material_work'] = {
            **{k: v for k, v in parent_work.items() if k != 'stages'},
            'stages': compact_stages,
        }
    return result


def input_record(package: dict) -> dict:
    sent=model_package(package)
    return {'policy':POLICY,'model_package_sha256':content_sha256(sent),
            'complete_material_snapshots_preserved':True,
            'stage':package['scope'],'source_ids':[row['source']['id'] for row in package.get('materials',[])]}
