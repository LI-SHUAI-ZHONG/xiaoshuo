"""Run the dependent part of the static step after its relation record is frozen."""
from collections.abc import Callable

from nw.config import Config
from nw.llm.base import LLMProvider
from nw.materials.network_followup import BASIS_STAGE, DELTA_FIELDS, STAGE, basis_inputs, merge_followup
from nw.materials.network_workflow import early_waiting, same_stage_rules, step_sources
from nw.materials.phase_routes import phase_order, product_ref
from nw.materials.semantic_products import _network_relation_inputs, original
from nw.materials.work_catalog import SourceDesk
from nw.store import Store
from nw.task_models import TaskRequest, content_sha256


FOLLOWUP_FIELDS = tuple(sorted(DELTA_FIELDS))
PROMPT = '''[MATERIAL_STEP] 静网关系已保存。只处理所给的本步派生动网资料。
按本项目需求及该条原义核对触发条件、关系和双方，才可在 requirements 中写给真实后续阶段的设计约束。条件不足的条目说明原因并排除。
只返回 stage=static_relations 和 products，其中仅含 requirements、_uses、_excluded、_criteria 四个数组。基础关系和已有要求都已冻结。
requirements 中只写新增内容。每条写 id、source_id、target_stage、constraint、project_refs。project_refs 必须包含实际关系的双方 member:ID。
在 _uses 用 requirement:ID 登记实际采用。在 _criteria 覆盖所采用资料的原义义务，每个适用条款的 input_refs 引用 dynamic_relation_inputs
中的实际关系行或其具体字段。可另引用已送的 brief；其他前置缺失时说明原因。output_refs 指向本条新增要求的具体字段，
consumer 与 target_stage 相同。/requirements/ 的序号为
requirement_offset 加本次新增数组的序号。必须引用原义条款哈希，不能把设计约束写成已发生的事实。
所有已送资料都须有明确用途或排除原因。未解析的原义应明确保留。'''


def run_followup(store: Store, request: TaskRequest, package: dict, provider: LLMProvider, config: Config,
                 desk: SourceDesk, products: dict, context: dict, network: tuple[dict, dict], basis: dict,
                 basis_sources: list[dict], calls: list[dict], prior_sources: list[dict], retry_failed: bool,
                 verify: Callable | None, governance: dict | None, index: int) -> tuple[dict, list[dict], list[dict]]:
    from nw.materials.governance_runtime import check_stage_governance, freeze_report
    from nw.materials.network_layers import INSTRUCTION as LAYER_INSTRUCTION, uses_fields
    from nw.materials.phase_contract import validate_phase
    from nw.materials.phase_flow import _sources, model_semantics, resolve_stage_runtime, retrieval_need
    from nw.materials.work_session import _study_call, model_source

    stage = STAGE
    authored, rules = network
    candidates = same_stage_rules(authored, rules, context, desk.by_id)
    if not candidates:
        return basis, basis_sources, calls
    upstream = basis_inputs(products, basis)
    pool, _ = step_sources(stage, authored, rules, upstream, context, desk.by_id)
    pool = {ident: use for ident, use in pool.items() if ident in candidates}
    required = [row for row in package.get('materials', []) if row['source']['id'] in candidates
                and row['request']['disposition'] == 'required']
    if not pool and not required:
        return basis, basis_sources, calls
    ctx = {**context, 'require_semantics': True, 'early_static_sources': basis['prepared_static_sources'],
           'method_sources': [*prior_sources, *basis_sources], 'accepted_state': [],
           'allowed_input_stages': [ref['stage'] for ref in basis['inputs']] + [BASIS_STAGE]}
    relations = basis['products']['relations']
    query = ' '.join(' '.join((r['source'], r['target'], r['relation'], r['condition'])) for r in relations)
    query = query[:840] + ' ' + retrieval_need(stage, package, products)[:640]
    deferred: list[dict] = []
    search_trace: dict = {'queries': []}
    sources = _sources(desk, stage, {**package, 'materials': required}, upstream, ctx['method_sources'], reviewed_only=True,
                       step_pool=pool, network_context=ctx, source_query=query, deferrals=deferred, trace=search_trace,
                       relation_matched=tuple(pool) if len(pool) == 1 else ())
    if not sources:
        return basis, basis_sources, calls
    contracts = [desk.semantic_contract(source) for source in sources]
    reviews = {source['source']['id']: review for source in sources
               if (review := desk.binding_review(source, stage, package['scope'])) is not None}
    model_contracts = [model_semantics(contract) for contract in contracts]
    for source, contract, model in zip(sources, contracts, model_contracts, strict=True):
        if uses_fields(source, contract, ctx):
            model['network_layer_fields'] = True
    ctx = {**ctx, 'semantic_contracts': [*basis['semantic_contracts'], *contracts],
           'binding_reviews': {**context.get('binding_reviews', {}), **basis['binding_reviews'], **reviews},
           'method_sources': [*ctx['method_sources'], *sources]}
    keys = {source['source']['id']: sorted(_network_relation_inputs(source, original(source), upstream, ctx))
            for source in sources}
    if not all(keys.values()):
        raise ValueError('MATERIAL_WAITING_INPUTS: 派生动网缺少已冻结的静网关系')
    from nw.materials.binding_reviews import model_review

    pinned_basis = product_ref(upstream[BASIS_STAGE])
    order = phase_order(package['scope'])
    payload = {'stage': stage, 'scope': package['scope'], 'mode': 'execute', 'policy': ctx['same_stage_network_policy'],
        'brief': package['brief'], 'stage_source_policy': package['stage_source_policy'],
        'static_relations_basis': {'ref': pinned_basis, 'relations': relations,
                                  'requirement_offset': len(basis['products']['requirements'])},
        'dynamic_relation_inputs': keys, 'target_stages': order[order.index(stage) + 1:],
        'sources': [model_source(source, stage=stage, semantics=contract, step_use=pool[source['source']['id']])
                    for source, contract in zip(sources, contracts, strict=True)],
        'source_contracts': model_contracts,
        'source_use_reviews': [model_review(reviews[c['source_id']], c, stage) for c in contracts if c['source_id'] in reviews],
        'output_contract': {'stage': stage, 'products': {key: [] for key in FOLLOWUP_FIELDS}}}
    all_sources = [*basis_sources, *sources]

    def validate(raw: dict) -> None:
        if set(raw) != {'stage', 'products'} or raw['stage'] != stage:
            raise ValueError('MATERIAL_STAGE: static follow-up requires the exact incremental result')
        merged = merge_followup(basis, raw['products'], sources, products, ctx)
        from nw.production_methods.runtime import split

        clean, _ = split({'stage': stage, 'products': merged})
        validate_phase(clean, stage, upstream, all_sources, ctx)
        report = check_stage_governance(governance, stage, merged, products, all_sources, ctx)
        if report and report['status'] == 'failed':
            bad = [row['rule_id'] for row in report['checks'] if row['status'] == 'failed']
            raise ValueError('MATERIAL_GOVERNANCE: ' + ','.join(dict.fromkeys(bad)))

    stage_config, stage_provider = resolve_stage_runtime(config, provider, stage)
    suffix = LAYER_INSTRUCTION if any(row.get('network_layer_fields') for row in model_contracts) else ''
    delta, receipt = _study_call(store, request, stage_config, stage_provider, index, payload, sources, desk,
        retry_failed, verify, prompt=PROMPT, prompt_suffix=suffix, validator=validate,
        version='static-network-followup-v1', read_only_sources=basis_sources)
    delta = delta['products']
    merged = merge_followup(basis, delta, sources, products, ctx)
    used = {row['source_id'] for row in merged['_uses']}
    selection = {**basis['source_selection'], 'offered': [source['source'] for source in all_sources],
        'selected': [source['source'] for source in all_sources if source['source']['id'] in used],
        'queries': [*basis['source_selection']['queries'], *search_trace['queries']],
        'network_waiting': early_waiting(stage, authored, rules, upstream, context, desk.by_id),
        'same_stage_selection': {'eligible': len(pool), 'offered': len(sources)}}
    record = {**basis, 'task_id': receipt['task_id'], 'products': merged, 'sha256': content_sha256(merged),
        'source_ids': [source['source']['id'] for source in all_sources], 'semantic_contracts': ctx['semantic_contracts'],
        'binding_reviews': {**basis['binding_reviews'], **reviews}, 'source_selection': selection,
        'deferred_sources': [*basis['deferred_sources'], *deferred], 'static_relations_basis': basis,
        'static_relations_followup': {**receipt, 'products': delta, 'sha256': content_sha256(delta),
                                      'source_ids': [source['source']['id'] for source in sources]}}
    if governance:
        record['governance'] = freeze_report(check_stage_governance(governance, stage, merged, products, all_sources, ctx))
    return record, all_sources, [*calls, receipt]
