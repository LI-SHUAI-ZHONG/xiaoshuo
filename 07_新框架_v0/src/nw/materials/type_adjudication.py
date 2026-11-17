"""Read-only adjudication of original, scoped type contracts for F2 design."""
from collections import Counter, defaultdict
from hashlib import sha256
import json
import sqlite3

from nw.materials.type_source_repairs import StaticTypeRepairs
from nw.materials.type_auxiliary import review_auxiliary


TYPE_TABLE = r'类型本体\类型总表.json'
_TYPE_A_DEFINITIONS = ('主类型.json', '子类型.json', '混合类型.json', '爽文机制.json',
                       '特殊叙事结构.json', '风格.json', '语气.json', '读者体验标签.json')
_DEFINITIONS = (*_TYPE_A_DEFINITIONS, TYPE_TABLE)
_COMBINATIONS = {'类型组合总表.json', '类型静态搭配库.json', '类型动态搭配库.json'}
_TYPE_FIELDS = ('primary_type_id', 'component_type_ids', 'type_ids', 'subtype_ids', 'hybrid_ids',
                'component_mechanism_ids', 'mechanism_ids', 'component_structure_ids',
                'structure_ids', 'component_style_ids', 'style_ids', 'tone_ids', 'audience_ids')
_REF_FIELDS = {'static_connection_ids': ('类型静态连接总表.json',),
               'dynamic_rule_ids': ('类型动态规则总表.json',),
               'candidate_effect_ids': ('类型动态候选效果.json',),
               'trigger_condition_ids': ('类型动态触发条件.json',),
               'adaptation_ids': ('类型表达适配总表.json',)}
_LIMITS = ('scope', 'exclusions', 'not_guaranteed', 'limitations', 'not_overrides',
           'forbidden_assumptions', 'forbidden_triggers', 'continuity_risks',
           'selection_constraints', 'continuity_constraints', 'compatibility_constraints',
           'conflict_constraints', 'propagation_limits', 'propagation_profile')
_CONDITIONS = ('conditions', 'preconditions', 'applicable_to', 'required_context',
               'required_information', 'required_resources', 'required_capabilities',
               'required_relationships', 'required_identity_conditions', 'required_moral_conditions')
_IDS = ('connection_id', 'combination_id', 'static_combination_id', 'dynamic_combination_id',
        'adaptation_id', 'effect_id', 'trigger_condition_id', 'candidate_effect_id',
        'type_id', 'hybrid_id', 'mechanism_id', 'structure_id', 'style_id', 'tone_id', 'tag_id',
        'condition_id', 'rule_id', 'validation_id', 'state_adaptation_id', 'propagation_id', 'mapping_id',
        'stable_id', 'id')
_UPGRADES = {'运行层升级', 'runtime_calling_layer'}


class _JSONObject(dict):
    def __init__(self, items: list[tuple]) -> None:
        super().__init__()
        self.duplicates: list[str] = []
        for name, member in items:
            if name in self:
                self.duplicates.append(f'原始JSON包含重复成员 {name}')
            self[name] = member


def _original(value: object, problems: list[str]) -> object:
    if isinstance(value, dict):
        if isinstance(value, _JSONObject):
            problems.extend(value.duplicates)
        return {k: _original(v, problems) for k, v in value.items() if k not in _UPGRADES}
    if isinstance(value, list):
        return [_original(v, problems) for v in value]
    return value


def _symbol(value: dict) -> str | None:
    return next((value[k] for k in _IDS if isinstance(value.get(k), str) and value[k]), None)


def _values(value: dict, fields: tuple) -> dict:
    return {k: value[k] for k in fields if value.get(k) not in (None, [], {}, '')}


def _ref(row: dict) -> dict:
    return {k: row[k] for k in ('id', 'fragment_id', 'source_id', 'fragment_key', 'locator', 'path',
                                 'file_sha256', 'sha256', 'byte_start', 'byte_end', 'line_start', 'line_end')}


class TypeAdjudicator:
    """One instance per catalog snapshot; never grants project or prose permission."""

    definition_blocks = _DEFINITIONS

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.records: dict[str, tuple[dict, dict]] = {}
        self.owners: dict[tuple[str, str], str] = {}
        self.scopes: dict[tuple[str, str], list[str]] = defaultdict(list)
        self.by_symbol: dict[str, list[str]] = defaultdict(list)
        self.record_issues: dict[str, list[str]] = {}
        self.results: dict[str, dict] = {}
        self._loaded = False
        self.repairs: StaticTypeRepairs | None = None

    def _load(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        fragments = self.connection.execute("""
            SELECT f.*,s.path,s.family,s.layer,s.file_sha256 FROM fragments f
            JOIN sources s ON s.id=f.source_id
            WHERE s.layer='baseline' AND s.family IN ('types','type_links') AND f.kind='source_block'
        """)
        for raw in fragments:
            f = dict(raw)
            payload = f.pop('payload')
            if sha256(payload).hexdigest() != f['sha256']:
                raise ValueError(f'Type source fragment hash mismatch: {f["id"]}')
            units = self.connection.execute("""
                SELECT * FROM material_units WHERE fragment_id=? AND kind='record'
                AND origin IN ('source','mixed') ORDER BY byte_start,id
            """, (f['id'],)).fetchall()
            for unit in units:
                row = dict(unit)
                data = payload[row['byte_start']-f['byte_start']:row['byte_end']-f['byte_start']]
                if sha256(data).hexdigest() != row['sha256']:
                    raise ValueError(f'Type source record hash mismatch: {row["id"]}')
                duplicates: list[str] = []
                value = _original(json.loads(data, object_pairs_hook=_JSONObject), duplicates)
                if not isinstance(value, dict):
                    continue
                row.update({k: f[k] for k in ('path', 'family', 'layer', 'file_sha256', 'source_id')})
                row.update(level='unit', fragment_key=f['key'])
                self.records[row['id']] = row, value
                self.record_issues[row['id']] = duplicates
                self.owners[f['id'], row['locator']] = row['id']
                if ident := _symbol(value):
                    self.scopes[f['key'], ident].append(row['id'])
                    self.by_symbol[ident].append(row['id'])
        self.repairs = StaticTypeRepairs(self.records, self.scopes, _ref)

    def _resolve(self, ident: str, blocks: tuple, *, source_scope: tuple[str, str | None] | None = None
                 ) -> tuple[list[str], list[str]]:
        for block in blocks:
            ids = self.scopes.get((block, ident), [])
            if source_scope is not None:
                source_id, version = source_scope
                ids = [i for i in ids if self.records[i][0]['source_id'] == source_id
                       and (version is None or self.records[i][1].get('schema_version') == version)]
            if ids:
                break
        else:
            return [], [f'未找到原始对象 {ident}；限定表：{"、".join(blocks)}']
        variants = {json.dumps(self.records[i][1], ensure_ascii=False, sort_keys=True) for i in ids}
        conflicts = [f'{block} 内 {ident} 有 {len(variants)} 个不同原始定义'] if len(variants) > 1 else []
        return sorted(ids), conflicts

    def _base(self, row: dict, value: dict, profile: str) -> dict:
        return dict(state='reference', can_offer_for_design=False, profile=profile,
                    meaning='', boundary='仅按此来源位置解释；运行层升级及评分不构成原始语义或项目批准。',
                    evidence_required='作者确认项目用途、参数、可观察表现和检验点；正文另需真实稿件证据。',
                    related=[], source_refs=[_ref(row)], conditions=_values(value, _CONDITIONS),
                    missing=[], conflicts=[], owner_id=row['id'],
                    contract=dict(scoped_id=dict(source_id=row['source_id'], block=row['fragment_key'],
                                                 locator=row['locator'], original_id=_symbol(value)),
                                  definition=value.get('definition') or value.get('description'),
                                  conditions=_values(value, _CONDITIONS), limits=_values(value, _LIMITS),
                                  source_refs=value.get('source_refs', []),
                                  evidence=_values(value, ('evidence_type', 'confidence', 'status')),
                                  constituents=[], original_fields_sha256=sha256(json.dumps(
                                      value, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()))

    def _references(self, result: dict, value: dict, fields: tuple, blocks: tuple, *,
                    source_scope: tuple[str, str | None] | None = None) -> None:
        for field in fields:
            raw = value.get(field, [])
            values = [raw] if isinstance(raw, str) else raw
            if not isinstance(values, list):
                result['conflicts'].append(f'{field} 不是ID或ID数组')
                continue
            for ident in dict.fromkeys(x for x in values if isinstance(x, str) and x):
                ids, problems = self._resolve(ident, blocks, source_scope=source_scope)
                if not ids:
                    result['missing'].extend(f'{field}: {p}' for p in problems)
                else:
                    result['conflicts'].extend(problems)
                    result['related'].extend(ids)
                result['contract']['constituents'].append(dict(field=field, original_id=ident, root_ids=ids))

    def _identity(self, row: dict, value: dict) -> dict:
        result = self._base(row, value, 'type_identity')
        definition = value.get('definition')
        name = value.get('canonical_name')
        result['meaning'] = f'{name or _symbol(value)}：{definition or "缺少原始定义"}'
        result['contract']['identity'] = _values(value, ('type_id', 'hybrid_id', 'mechanism_id',
             'structure_id', 'style_id', 'tone_id', 'tag_id', 'type_kind', 'canonical_name',
             'parent_id', 'component_type_ids', 'component_weights', 'inclusions',
             'distinguishing_features', 'information_distribution', 'time_handling',
             'viewpoint_handling', 'validation_requirements'))
        if not isinstance(definition, str) or not definition.strip() or definition == name:
            result['missing'].append('原始定义缺失或仅复述规范名称，不能仅凭名称恢复完整类型契约')
            alternatives = []
            for ident in self.by_symbol.get(_symbol(value), []):
                other_row, other = self.records[ident]
                if (other_row['fragment_key'] in _DEFINITIONS and other_row['fragment_key'] != row['fragment_key']
                        and other.get('definition') and other.get('definition') != other.get('canonical_name')
                        and other.get('parent_id') == value.get('parent_id')
                        and other.get('type_kind') == value.get('type_kind')
                        and other.get('component_type_ids') == value.get('component_type_ids')):
                    alternatives.append(ident)
            result['contract']['fuller_source_alternatives'] = alternatives
            result['related'].extend(alternatives)
        definition_scope = (TYPE_TABLE,) if row['fragment_key'] == TYPE_TABLE else _TYPE_A_DEFINITIONS
        original_scope = (row['source_id'], value.get('schema_version'))
        if value.get('parent_id'):
            self._references(result, value, ('parent_id',), definition_scope, source_scope=original_scope)
        if value.get('component_type_ids'):
            self._references(result, value, ('component_type_ids',), definition_scope, source_scope=original_scope)
        if (any(k in value for k in ('style_id', 'tone_id', 'structure_id', 'mechanism_id', 'tag_id'))
                or value.get('type_kind') in {'STYLE', 'TONE', 'NARRATIVE_STRUCTURE', 'PLOT_MECHANISM', 'AUDIENCE_TAG'}):
            result['profile'] = 'type_expression'
        result['contract']['project_completion_required'] = ['作者选择用途与角色', '项目承诺、边界和兑现计划']
        result['state'] = 'design_ready' if not result['missing'] and not result['conflicts'] else 'blocked'
        return result

    def _link(self, row: dict, value: dict) -> dict:
        binary = value.get('connection_type') in {'TYPE_REFINES', 'TYPE_COMBINES_WITH',
                                                  'TYPE_COMPATIBLE_WITH', 'TYPE_USES_MECHANISM'}
        result = self._base(row, value, 'type_link' if binary else 'type_expression')
        result['meaning'] = f'{value.get("source_id")} → {value.get("target_id")}：{value.get("connection_type")}'
        result['contract'].update(_values(value, ('connection_id', 'source_id', 'source_kind',
                                  'target_id', 'target_kind', 'connection_type', 'relation_scope',
                                  'direction', 'parameters', 'supported_uses', 'alternatives')))
        for field in ('connection_id', 'source_id', 'target_id', 'source_kind', 'target_kind', 'connection_type'):
            if not isinstance(value.get(field), str) or not value[field].strip():
                result['missing'].append(f'原始连接缺少有效 {field}')
        supported = {'TYPE_SUPPORTS_CONCEPT', 'TYPE_SUPPORTS_ENTITY', 'TYPE_SUPPORTS_EVENT',
                     'TYPE_SUPPORTS_INFORMATION', 'TYPE_SUPPORTS_RESOURCE', 'TYPE_SUPPORTS_FORESHADOWING',
                     'TYPE_DISTINGUISHED_FROM'}
        if not binary and value.get('connection_type') not in supported:
            result['missing'].append('原始 connection_type 不在本裁定已解释的关系集合中')
        self._references(result, value, ('source_id',), _DEFINITIONS)
        if binary:
            self._references(result, value, ('target_id',), _DEFINITIONS)
        else:
            result['contract']['target_binding'] = '目标是原文分类词；项目需自行选择实体，不能自动创建事件或结果'
        ident = value.get('connection_id')
        for other in self.by_symbol.get(ident, []):
            other_row, other_value = self.records[other]
            block = other_row['fragment_key']
            if other != row['id'] and ('连接' in block or block == '类型兼容关系.json') and other_value != value:
                result['conflicts'].append(f'{ident} 与 {block}#{other_row["locator"]} 原始字段不一致；需明确采用来源')
        if value.get('connection_type') == 'TYPE_REFINES' and result['related']:
            source_ids, _ = self._resolve(value.get('source_id'), _DEFINITIONS)
            if source_ids and any(self.records[i][1].get('parent_id') != value.get('target_id') for i in source_ids):
                result['conflicts'].append('TYPE_REFINES 目标与源子类型原始 parent_id 不一致')
        if value.get('connection_type') == 'TYPE_COMBINES_WITH':
            source_ids, _ = self._resolve(value.get('source_id'), _DEFINITIONS)
            if source_ids and any(value.get('target_id') not in self.records[i][1].get('component_type_ids', []) for i in source_ids):
                result['conflicts'].append('TYPE_COMBINES_WITH 目标不在原始混合类型 component_type_ids 中')
        result['contract']['project_completion_required'] = ['作者选择两端及用途', '项目触发、选择、代价、失败分支和检验点']
        if not binary and not value.get('limitations'):
            result['missing'].append('原始适配边缺少可解释的适用限制')
        result['state'] = 'design_ready' if value.get('status') == 'active' and not result['missing'] and not result['conflicts'] else 'reference'
        return result

    def _combination(self, row: dict, value: dict) -> dict:
        result = self._base(row, value, 'type_combination')
        result['meaning'] = value.get('description') or f'{_symbol(value)} 的类型、机制、结构及风格多维组合候选'
        result['contract']['constituent_fields'] = _values(value, _TYPE_FIELDS + tuple(_REF_FIELDS))
        value, repairs = self.repairs.apply(value)
        result['source_repair'] = result['contract']['source_repair'] = repairs
        result['contract']['effective_constituent_fields'] = _values(value, _TYPE_FIELDS + tuple(_REF_FIELDS))
        result['source_refs'].extend(x['replacement_ref'] for x in repairs)
        result['contract']['focus_fields'] = {k: v for k, v in value.items()
                                              if ('focus' in k or k.endswith('_type_ids') or k == 'concept_ids') and v}
        self._references(result, value, _TYPE_FIELDS, _DEFINITIONS)
        for field, blocks in _REF_FIELDS.items():
            self._references(result, value, (field,), blocks)
        if not value.get('primary_type_id'):
            result['missing'].append('缺少 primary_type_id')
        if not any(value.get(k) for k in ('component_type_ids', 'type_ids')):
            result['missing'].append('缺少组成类型ID；机制、结构、风格另按各自字段核验')
        dependencies = {i for c in result['contract']['constituents'] for i in c['root_ids']}
        for ident in sorted(dependencies):
            ref_row, ref_value = self.records[ident]
            if ref_row['fragment_key'] not in _DEFINITIONS and ref_value.get('status') not in {'active'}:
                result['missing'].append(f'{ref_row["fragment_key"]}:{_symbol(ref_value)} 原始状态为 {ref_value.get("status")}，不能作为已确认组成依据')
            if ref_value.get('confidence') == 999:
                result['conflicts'].append(f'{ref_row["fragment_key"]}:{_symbol(ref_value)} confidence=999，超出0–1')
        selected = {x['original_id'] for x in result['contract']['constituents'] if x['field'] in _TYPE_FIELDS}
        rules = set(value.get('dynamic_rule_ids', []))
        for item in result['contract']['constituents']:
            for ident in item['root_ids']:
                ref_row, ref_value = self.records[ident]
                if item['field'] == 'static_connection_ids' and ref_value.get('source_id') not in selected:
                    result['conflicts'].append(f'{item["original_id"]} 的 source_id={ref_value.get("source_id")} 不在本组合所列类型中')
                if item['field'] == 'candidate_effect_ids' and ref_value.get('rule_id') not in rules:
                    result['conflicts'].append(f'{item["original_id"]} 属于规则 {ref_value.get("rule_id")}，未列入组合 dynamic_rule_ids')
                if item['field'] in _REF_FIELDS:
                    for other in self.by_symbol.get(item['original_id'], []):
                        other_row, other_value = self.records[other]
                        if other_row['fragment_key'] == ref_row['fragment_key'] and other_value != ref_value:
                            result['conflicts'].append(f'{item["original_id"]} 在其限定来源表中有不同原始记录')
        result['contract']['project_completion_required'] = ['作者确认组合取舍与冲突处理', '项目触发、行动、代价及失败分支', '场景兑现与检验点']
        result['state'] = 'reference'
        if result['missing'] or result['conflicts']:
            result['state'] = 'blocked'
        elif value.get('status') == 'active' and (value.get('description') or value.get('not_guaranteed')):
            result['state'] = 'design_ready'
        return result

    def _record(self, row: dict, value: dict) -> dict:
        block = row['fragment_key']
        if block.startswith(('作品知识库', '作品资料库')) or any(x in block for x in ('字段说明', '模板', '验证规则', '枚举', '别名', '来源映射')):
            result = self._base(row, value, 'metadata')
            result['meaning'] = '原文中的来源、结构、示例、校验或导航记录，不作为独立创作规则'
        elif block in _DEFINITIONS:
            result = self._identity(row, value)
        elif 'connection_id' in value and 'source_id' in value:
            result = self._link(row, value)
        elif block in _COMBINATIONS:
            result = self._combination(row, value)
        else:
            result = review_auxiliary(self, row, value)
        confidence = value.get('confidence')
        result['conflicts'].extend(self.record_issues[row['id']])
        if ident := _symbol(value):
            _, problems = self._resolve(ident, (block,))
            result['conflicts'].extend(problems)
        if isinstance(confidence, (int, float)) and not isinstance(confidence, bool) and not 0 <= confidence <= 1:
            result['conflicts'].append(f'confidence={confidence} 超出原始Schema规定的0–1，未自动修复')
        if value.get('status') in {'pending', 'pending_review', 'deprecated', 'template', 'quarantined'}:
            result['missing'].append(f'原始 status={value["status"]}，未冒充已确认条目')
            result['state'] = 'reference'
        if result['conflicts']:
            result['state'] = 'blocked'
        if result['state'] == 'design_ready' and value.get('status') != 'active':
            result['missing'].append('原始记录未声明 active 状态，需先核对来源状态')
            result['state'] = 'reference'
        if result['contract'].get('fuller_source_alternatives') and not result['conflicts']:
            result['state'] = 'reference'
        result['related'] = sorted(set(result['related']) - {row['id']})
        result['missing'] = sorted(set(result['missing']))
        result['conflicts'] = sorted(set(result['conflicts']))
        result['can_offer_for_design'] = result['state'] == 'design_ready'
        return result

    def review(self, row: dict) -> dict | None:
        """Return JSON-ready source judgment; non-baseline/non-type rows are out of scope."""
        if row.get('family') not in {'types', 'type_links'} or row.get('layer') != 'baseline':
            return None
        self._load()
        if row['id'] in self.results:
            return self.results[row['id']]
        if row['id'] in self.records:
            original_row, value = self.records[row['id']]
            result = self._record(original_row, value)
            self.results[row['id']] = result
            return result
        pointer = row.get('locator') or ''
        owner = None
        if row.get('origin') not in {'upgrade', 'supplement', 'residual'}:
            while True:
                if owner := self.owners.get((row['fragment_id'], pointer)):
                    break
                if not pointer:
                    break
                pointer = pointer.rpartition('/')[0]
        result = self._base(dict(row, source_id=row.get('source_id')), {}, 'metadata')
        result['owner_id'] = owner or row['fragment_id']
        result['state'] = 'context' if owner else 'reference'
        result['meaning'] = '所属原始记录的字段，仅连同完整记录解释' if owner else '结构、空集、导航、补充或升级材料，保留来源核对用途'
        result['contract'] = dict(owner_id=result['owner_id'], field=row.get('label'), locator=row.get('locator'))
        if owner:
            result['related'] = [owner]
        return result

    def diagnostics(self) -> dict:
        """Root counts and exact unresolved sources; child contexts are intentionally excluded."""
        self._load()
        counts: Counter = Counter()
        cohorts: dict[str, Counter] = defaultdict(Counter)
        missing: Counter = Counter()
        conflicts: Counter = Counter()
        examples: dict[str, dict] = {}
        orphans: list[dict] = []
        fuller: list[dict] = []
        repairs: list[dict] = []
        for row, _ in self.records.values():
            result = self.review(row)
            counts[result['state']] += 1
            cohorts[row['fragment_key']][result['state']] += 1
            missing.update(result['missing'])
            conflicts.update(result['conflicts'])
            examples.setdefault(result['state'], dict(id=row['id'], key=row['key'], block=row['fragment_key']))
            for item in result['contract'].get('constituents', []):
                if not item['root_ids']:
                    orphans.append(dict(owner_id=row['id'], source_ref=_ref(row), **item))
            if alternatives := result['contract'].get('fuller_source_alternatives'):
                fuller.append(dict(owner_id=row['id'], original_id=_symbol(self.records[row['id']][1]), alternatives=alternatives))
            repairs.extend(dict(owner_id=row['id'], **item) for item in result.get('source_repair', []))
        return dict(policy='type-source-adjudication-v1', roots=sum(counts.values()), states=dict(counts),
                    cohorts={b: dict(c) for b, c in sorted(cohorts.items())},
                    missing=[dict(reason=k, count=v) for k, v in missing.most_common()],
                    conflicts=[dict(reason=k, count=v) for k, v in conflicts.most_common()], examples=examples,
                    orphan_constituents=orphans, fuller_source_mappings=fuller,
                    applied_source_repairs=repairs,
                    execution_allowed=False, upgrade_authority_accepted=False)
