"""Pair frozen runtime layers with exact owners, without inheriting authority."""
from collections import defaultdict
from hashlib import sha256
import json
import re
import sqlite3

from nw.task_models import canonical

POLICY = 'source-runtime-pairing-v1'
_NETWORK_TEMPLATE_COST = {
    'static': '关系被重新确认后，至少一方失去原有权限、资源或安全余量，新的关系边界限制后续行动。',
    'dynamic': '传播会消耗行动窗口或暴露关系来源，后续对象必须在已改变的状态上重新决策。',
    'anchors': '角色为确认或避开该锚点付出时间、暴露位置或承受身体不适，场景状态因此不可完全复原。',
}
_NARRATION = {'editor', 'prose_review', 'scope_review', 'expression', 'knowledge'}
_PROCESS = {'material_selection', 'material_conversion', 'brief', 'preflight', 'continuity',
            'timeline_process', 'promise_process', 'pov_process', 'preflight_process', 'usage_process'}
_EVIDENCE = {
    'static_relation': ('relation', 'relation_constraints', 'design,scene,review',
                        '双方项目实体、原关系条件、约束及其实际影响；静态关系不强求状态改变。'),
    'static_binding': ('relation', 'relation_constraints', 'design,scene,review',
                       '双方项目实体、原关系条件、约束及其实际影响。'),
    'dynamic_relation': ('transition', 'cause_and_state_delta', 'design,scene,review,state,accept',
                         '核对前状态、原触发、行动、代价、失败分支、后状态及知情获取证据。'),
    'dynamic_binding': ('transition', 'cause_and_state_delta', 'design,scene,review,state,accept',
                        '核对前置静态关系、原触发、行动后果和世界及人物所知的变化。'),
    'type_transition': ('transition', 'cause_and_state_delta', 'design,scene,review,state,accept',
                        '核对已采用类型、允许字段、前置及相斥规则，再核对实际变化。'),
    'anchor': ('perception', 'pov_condition_and_observation', 'design,scene,review',
               '核对原条件、具体对象、观察者权限与观察时机；锚点不强求选择或代价。'),
    'material_selection': ('process', 'design_selection_record', 'design',
                           '检查任务功能→支撑板块→必需子项、实际选用及未选理由。'),
    'material_conversion': ('process', 'design_parameter_mapping', 'design,review',
                            '检查所选来源→项目参数→正文表现→核验点，未能转化的部分登记缺口。'),
    'type_identity': ('type', 'type_promise_and_boundary', 'design,scene,review',
                      '检查采用类型、期待、适用边界与实际兑现，不能以类型名代替设计。'),
    'type_combination': ('type', 'component_mechanism_and_conflict', 'design,scene,review',
                         '逐组成项核查兼容机制、冲突处理及非保证边界。'),
    'type_link': ('type', 'component_mechanism_and_conflict', 'design,scene,review',
                  '核对有向类型端点、组合条件、选择、代价和失败分支。'),
}


def _normal(value: str) -> str:
    return re.sub(r'[\s*\\]', '', value).strip('【】[]：:。')


def _unique(pairs: list[tuple]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate translation member')
        result[key] = value
    return result


def _record_ids(row: dict) -> set[str]:
    identities = {row['key']}
    if row['family'] in {'types', 'type_links'} and row['kind'] == 'record':
        position = re.fullmatch(r'(?:/原始条目)?/(\d+)', row['locator'] or '')
        if position:
            identities.add(f"{row['fragment_key']}:{int(position[1])+1}")
    return identities


def execution_for(profile: str, meaning: str) -> dict:
    domain, evidence, stages, action = _EVIDENCE.get(profile, (
        ('narration', 'complete_draft_comparison', 'design,review',
         '按原判据冻结完整稿件范围，比较叙述、披露和读者效果，保持人物与叙述者权限。')
        if profile in _NARRATION else
        ('process', 'stage_artifact', 'design,review', '在所属阶段核对真实输入、执行产物和结果。')
        if profile in _PROCESS else
        ('character' if profile == 'character' else profile, 'action_and_consequence',
         'design,scene,review', '把本项原义对应到具体项目参数与可观察表现，并核对前因后果和适用边界。')))
    return {'domain': domain, 'stages': stages.split(','), 'evidence_kind': evidence,
            'source_meaning': meaning, 'operation': action,
            'project_fields': ['trigger', 'operation', 'result', 'verification'],
            'authority': 'current_project_design_and_evidence_required'}


class LayerCompiler:
    def __init__(self, db: sqlite3.Connection) -> None:
        self.db = db
        self.by_fragment: dict[str, list] = defaultdict(list)
        self.by_key: dict[tuple, list] = defaultdict(list)
        self.fragments: dict[str, sqlite3.Row] = {}
        self.cache: dict[str, dict | None] = {}
        self.parsed: dict[str, tuple] = {}
        self.static_ordinals = {}
        self.declared: dict[tuple, list] = defaultdict(list)
        ordinals = defaultdict(int)
        for edge in db.execute("""SELECT f.id,f.source_id FROM fragments f JOIN sources s ON s.id=f.source_id
                WHERE s.family='static' AND s.layer='baseline' AND f.kind='network_edge'
                ORDER BY f.source_id,f.byte_start"""):
            ordinals[edge['source_id']] += 1
            self.static_ordinals[edge['id']] = ordinals[edge['source_id']]
        for raw in db.execute("""SELECT u.*,s.path,s.file_sha256,s.source_id,s.family FROM material_units u
                JOIN (SELECT f.id,f.source_id,s.path,s.file_sha256,s.family FROM fragments f
                      JOIN sources s ON s.id=f.source_id WHERE s.layer='baseline') s ON s.id=u.fragment_id
                WHERE u.origin='upgrade' OR (u.origin='supplement' AND u.kind='type_profile')
                ORDER BY u.byte_start,u.id"""):
            unit = dict(raw)
            self.by_fragment[unit['fragment_id']].append(unit)
            self.by_key[unit['source_id'], unit['key']].append(unit)
        for units in list(self.by_fragment.values()):
            for unit in units:
                if unit['family'] != 'library':
                    continue
                value, error = self._parse(unit)
                bindings = value.get('runtime_calling_layer', []) if isinstance(value, dict) else []
                if not error and isinstance(bindings, list):
                    for ident in {b.get('source_id') for b in bindings if isinstance(b, dict) and isinstance(b.get('source_id'), str)}:
                        self.declared[unit['source_id'], ident].append(unit)

    def _fragment(self, ident: str) -> sqlite3.Row:
        if ident not in self.fragments:
            # Large SOURCE blocks are reused by many records; keep one blob.
            self.fragments.clear()
            self.fragments[ident] = self.db.execute('SELECT * FROM fragments WHERE id=?', (ident,)).fetchone()
            f = self.fragments[ident]
            if not isinstance(f['payload'], bytes) or sha256(f['payload']).hexdigest() != f['sha256']:
                raise ValueError('Runtime layer fragment hash mismatch')
        return self.fragments[ident]

    def _payload(self, row: dict) -> bytes:
        f = self._fragment(row['fragment_id'])
        payload = f['payload']
        left, right = row['byte_start'] - f['byte_start'], row['byte_end'] - f['byte_start']
        data = payload[left:right]
        if not 0 <= left < right <= len(payload) or sha256(data).hexdigest() != row['sha256']:
            raise ValueError('Runtime layer source hash mismatch')
        return data

    def _candidates(self, row: dict) -> list[dict]:
        nested = [u for u in self.by_fragment[row['fragment_id']]
                  if u['byte_start'] >= row['byte_start'] and u['byte_end'] <= row['byte_end']
                  and (row['level'] == 'fragment' or u['locator'].rpartition('/')[0] == row['locator'])]
        siblings = []
        if row['family'] == 'library':
            for unit in self.declared[row['source_id'], row['key']]:
                if row['byte_end'] > unit['byte_start']:
                    continue
                preceding = self.db.execute("""SELECT id,byte_start FROM (
                    SELECT f.id,f.byte_start,f.byte_end,f.key FROM fragments f WHERE f.source_id=?
                      AND f.kind IN ('library_entry','library_block')
                    UNION ALL SELECT u.id,u.byte_start,u.byte_end,u.key FROM material_units u
                      JOIN fragments f ON f.id=u.fragment_id WHERE f.source_id=?
                      AND u.kind IN ('embedded_entry','embedded_block'))
                    WHERE key=? AND byte_end<=? ORDER BY byte_start DESC LIMIT 1""",
                    (row['source_id'], row['source_id'], row['key'], unit['byte_start'])).fetchone()
                if preceding is not None and preceding['id'] == row['id']:
                    siblings.append(unit)
        if row['family'] in {'library', 'anchors'}:
            for unit in self.by_key[row['source_id'], row['key']]:
                if unit['fragment_id'] == row['fragment_id']:
                    continue
                fragment = self._fragment(unit['fragment_id'])
                if fragment['kind'] == 'library_upgrade':
                    preceding = self.db.execute("""SELECT id FROM fragments WHERE source_id=?
                        AND kind IN ('library_entry','library_block') AND byte_start<?
                        ORDER BY byte_start DESC LIMIT 1""", (row['source_id'], fragment['byte_start'])).fetchone()
                    if preceding is None or preceding['id'] != row['fragment_id']:
                        continue
                elif row['family'] != 'anchors':
                    continue
                elif fragment['kind'] == 'anchor_upgrade':
                    preceding = self.db.execute("""SELECT id FROM fragments WHERE source_id=?
                        AND kind='anchor' AND byte_start<? ORDER BY byte_start DESC LIMIT 1""",
                        (row['source_id'], fragment['byte_start'])).fetchone()
                    if preceding is None or preceding['id'] != row['fragment_id']:
                        continue
                elif (fragment['payload'].lstrip().startswith(b'|') or self.db.execute("""
                        SELECT count(*) FROM fragments WHERE source_id=? AND key=? AND kind='anchor'
                        AND substr(CAST(payload AS TEXT),1,1)='|'""", (row['source_id'], row['key'])).fetchone()[0] != 1):
                    continue
                siblings.append(unit)
        if row['family'] in {'types', 'type_links'} and row['kind'] == 'record':
            identities = _record_ids(row)
            for unit in self.by_fragment[row['fragment_id']]:
                if unit in nested or unit['locator'] not in {'/运行层升级', '/runtime_calling_layer'}:
                    continue
                value, _ = self._parse(unit)
                bindings = value.get('runtime_calling_layer', []) if isinstance(value, dict) else value
                if (isinstance(bindings, list) and any(isinstance(b, dict) and isinstance(b.get('source_id'), str) and b['source_id'] in identities for b in bindings)
                        and self.db.execute("SELECT count(*) FROM material_units WHERE fragment_id=? AND key=? AND kind='record'",
                                            (row['fragment_id'], row['key'])).fetchone()[0] == 1):
                    siblings.append(unit)
            for unit in [u for ident in identities for u in self.by_key[row['source_id'], ident]]:
                if unit['fragment_id'] == row['fragment_id'] or not unit['locator'].startswith('supplement/'):
                    continue
                value, _ = self._parse(unit)
                bindings = value.get('runtime_calling_layer', []) if isinstance(value, dict) else []
                references = [b.get('source_ref') for b in bindings if isinstance(b, dict) and isinstance(b.get('source_id'), str) and b['source_id'] in identities] if isinstance(bindings, list) else []
                if (any(isinstance(ref, str) and re.search(r':'+re.escape(row['fragment_key'])+r'\[\d+\]$', ref) for ref in references)
                        and self.db.execute("SELECT count(*) FROM material_units WHERE fragment_id=? AND key=? AND kind='record'",
                                            (row['fragment_id'], row['key'])).fetchone()[0] == 1):
                    siblings.append(unit)
            original = json.loads(self._payload(row))
            if isinstance(original, dict) and isinstance(original.get('canonical_name'), str):
                for unit in self.by_key[row['source_id'], original['canonical_name']]:
                    if unit['kind'] == 'type_profile':
                        siblings.append(unit)
                    elif unit['locator'].startswith('supplement/'):
                        value, _ = self._parse(unit)
                        bindings = value.get('runtime_calling_layer', []) if isinstance(value, dict) else []
                        if isinstance(bindings, list) and bindings and all(isinstance(b, dict)
                            and b.get('source_id') == original['canonical_name']
                            and isinstance(b.get('source_ref'), str)
                            and b['source_ref'].endswith(':SECTION: ' + original['canonical_name']) for b in bindings):
                            siblings.append(unit)
        return list({u['id']: u for u in [*nested, *siblings]}.values())

    def _parse(self, unit: dict) -> tuple[object, str | None]:
        if unit['id'] not in self.parsed:
            raw = self._payload(unit).decode('utf-8').strip()
            try:
                fence = re.search(r'(?m)^```json[ \t]*\r?\n', raw)
                start = fence.end() if fence else raw.find('{') if not raw.startswith('[') else 0
                value, _ = json.JSONDecoder(object_pairs_hook=_unique).raw_decode(raw[max(start, 0):])
                self.parsed[unit['id']] = (value, None)
            except ValueError:
                self.parsed[unit['id']] = (None, 'unparsed_translation')
        return self.parsed[unit['id']]

    def _profile(self, unit: dict, ref: dict) -> dict:
        fields = []
        for raw in self.db.execute("""SELECT * FROM material_units WHERE fragment_id=? AND origin='supplement'
                AND kind IN ('profile_element','reader_expectation','style_constraint','length_guidance','risk')
                AND byte_start>=? AND byte_end<=? ORDER BY byte_start""",
                (unit['fragment_id'], unit['byte_start'], unit['byte_end'])):
            field = dict(raw)
            fields.append({'field': field['kind'], 'text': self._payload(field).decode('utf-8').strip(),
                           'source_id': field['id'], 'sha256': field['sha256']})
        return {'id': unit['id'], 'source_ref': ref, 'binding_ids': [], 'source_anchors': [],
                'aligned_fields': fields, 'rejected_fields': [], 'mode': 'type_profile_supplement'}

    @staticmethod
    def _review_network_strategy(family: str, index: int, strategy: dict, rejected: list[dict]) -> None:
        template_cost = _NETWORK_TEMPLATE_COST.get(family)
        if not template_cost or strategy.get('cost_or_change') != template_cost:
            return
        rejected.append({'binding': index, 'field': 'creation_binding/creative_strategy/cost_or_change',
                         'reason': '旧运用层统一代价。当前代价依据原条或本项目真实行动与变化证据。'})
        if family == 'anchors' and strategy.get('source_specific_trigger'):
            rejected.append({'binding': index, 'field': 'creation_binding/creative_strategy/source_specific_trigger',
                             'reason': '原表触发栏与本场实际视角和行动决定该锚点是否适用。'})

    def for_owner(self, row: dict, review: dict) -> dict | None:
        if row['layer'] != 'baseline' or review.get('owner_id') != row['id'] or review.get('contract', {}).get('upgrade_only'):
            return None
        if row['id'] in self.cache:
            return self.cache[row['id']]
        units = self._candidates(row)
        if not units:
            self.cache[row['id']] = None
            return None
        original = self._payload(row)
        for unit in sorted(units, key=lambda u: u['byte_start'], reverse=True):
            if unit['fragment_id'] == row['fragment_id']:
                a, b = unit['byte_start']-row['byte_start'], unit['byte_end']-row['byte_start']
                original = original[:a] + original[b:]
        original_text = _normal(original.decode('utf-8'))
        expected_ids = _record_ids(row)
        if row['family'] == 'static' and row['id'] in self.static_ordinals:
            edge = json.loads(self._payload(row))
            expected_ids.add(f"STATIC:{edge.get('source')}->{edge.get('target')}#{self.static_ordinals[row['id']]}")
        pairs, issues = [], []
        for unit in units:
            ref = {k: unit[k] for k in ('id', 'fragment_id', 'source_id', 'path', 'file_sha256', 'sha256',
                                       'byte_start', 'byte_end', 'line_start', 'line_end', 'locator')}
            if unit['kind'] == 'type_profile':
                pairs.append(self._profile(unit, ref))
                continue
            value, error = self._parse(unit)
            if error:
                issues.append({'kind': error, 'source_ref': ref})
                continue
            direct = isinstance(value, dict) and 'creation_binding' in value and 'binding_id' in value
            bindings = [value] if direct else value if isinstance(value, list) else value.get('runtime_calling_layer', []) if isinstance(value, dict) else []
            if isinstance(bindings, dict):
                bindings = [bindings]
            if not isinstance(bindings, list) or any(not isinstance(b, dict) or any(
                    key in b and not isinstance(b[key], dict) for key in ('semantic_interpretation','creation_binding','evidence_contract'))
                    or 'source_id' in b and not isinstance(b['source_id'], str)
                    for b in bindings):
                issues.append({'kind': 'malformed_translation', 'source_ref': ref})
                continue
            declared = value.get('canonical_source_id') if isinstance(value, dict) else None
            if declared is not None and not isinstance(declared, str):
                issues.append({'kind': 'malformed_translation', 'source_ref': ref})
                continue
            container = bool(declared and declared.startswith('TYPE-SOURCE:') and row['kind'] == 'record'
                             and unit['fragment_id'] == row['fragment_id'] and unit['locator'] in {'/运行层升级','/runtime_calling_layer'})
            if container:
                bindings = [b for b in bindings if b.get('source_id') in expected_ids]
            if row['family'] == 'types' and row['kind'] == 'record' and unit['locator'].startswith('supplement/'):
                name = json.loads(self._payload(row)).get('canonical_name')
                if isinstance(name, str) and bindings and all(b.get('source_id') == name
                    and isinstance(b.get('source_ref'), str) and b['source_ref'].endswith(':SECTION: ' + name) for b in bindings):
                    expected_ids = expected_ids | {name}
            bad_ordinal = any(row['family'] in {'types', 'type_links'} and b.get('source_id') in _record_ids(row) - {row['key']}
                and not (isinstance(b.get('source_ref'), str) and b['source_ref'].endswith(
                    ':' + b['source_id'].rsplit(':', 1)[0] + '[' + b['source_id'].rsplit(':', 1)[1] + ']'))
                for b in bindings)
            if declared and not container and declared not in expected_ids or any(
                    b.get('source_id') not in expected_ids and not (direct and 'source_id' not in b) for b in bindings) or bad_ordinal:
                issues.append({'kind': 'translation_identity_mismatch', 'source_ref': ref, 'declared_id': declared})
                continue
            if not bindings:
                issues.append({'kind': 'no_runtime_translation', 'source_ref': ref})
                continue
            anchors, aligned, rejected = [], [], []
            seen_bindings = set()
            for index, binding in enumerate(bindings):
                if row['family'] == 'static':
                    fingerprint = canonical(binding)
                    if fingerprint in seen_bindings:
                        continue
                    seen_bindings.add(fingerprint)
                strategy = binding.get('creation_binding', {}).get('creative_strategy')
                if isinstance(strategy, dict):
                    self._review_network_strategy(row['family'], index, strategy, rejected)
                semantic = binding.get('semantic_interpretation', {})
                anchor = semantic.get('source_semantic_anchor') or semantic.get('source_meaning', '')
                grounded = isinstance(anchor, str) and len(_normal(anchor)) >= 8 and _normal(anchor).rstrip('。') in original_text
                if grounded:
                    anchors.append(anchor)
                else:
                    rejected.append({'binding': index, 'field': 'semantic_interpretation', 'reason': '原义锚点不足或与原文字面不符，须重新转译'})
                for section, names in (('semantic_interpretation', ('operational_meaning',)),
                                       ('creation_binding', ('creative_action', 'scene_strategy', 'prose_strategy'))):
                    for name in names:
                        text = binding.get(section, {}).get(name, '')
                        if not isinstance(text, str) or not text:
                            continue
                        conflict = review['profile'] in _NARRATION | _PROCESS and any(
                            token in text for token in ('让角色', '角色身体', '身体反应', '状态变化', '角色选择'))
                        if conflict:
                            issues.append({'kind': 'semantic_domain_conflict', 'field': f'{section}/{name}', 'source_ref': ref})
                        if not conflict and len(_normal(text)) >= 8 and _normal(text).rstrip('。') in original_text:
                            aligned.append({'binding': index, 'field': f'{section}/{name}', 'text': text})
                        else:
                            rejected.append({'binding': index, 'field': f'{section}/{name}',
                                             'reason': '语义域错位' if conflict else '通用模板仅供当前项目重新转化，不能证明本项效果'})
            pairs.append({'id': unit['id'], 'source_ref': ref,
                          'owner_native_id': row['key'], 'owner_locator': row['locator'],
                          'translation_source_ids': sorted({b['source_id'] for b in bindings if isinstance(b.get('source_id'), str)}),
                          'binding_ids': sorted({b['binding_id'] for b in bindings if isinstance(b, dict) and isinstance(b.get('binding_id'), str)}),
                          'source_anchors': list(dict.fromkeys(anchors)), 'aligned_fields': aligned,
                          'rejected_fields': rejected, 'mode': 'source_grounded_project_translation_required'})
        execution = execution_for(review['profile'], review['meaning']) if pairs else None
        result = {'policy': POLICY, 'owner_id': row['id'], 'pairs': pairs, 'issues': issues, 'execution': execution,
                  'source_state': review['state'],
                  'pending': [] if review['state'] == 'design_ready' else [
                      {'step': 'repair_source_meaning_or_dependencies', 'missing': review.get('missing', []),
                       'conflicts': review.get('conflicts', [])},
                      {'step': 'design_function_from_source_and_translation', 'execution': execution},
                      {'step': 'verify_stage_artifact_before_adoption', 'owner_id': row['id']} ]}
        self.cache[row['id']] = result
        return result
