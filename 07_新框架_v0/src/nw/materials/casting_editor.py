"""Judge a proposed causal role against the frozen story before any person is designed."""
from collections.abc import Callable
from dataclasses import replace

from nw.config import Config, resolve_stage_runtime
from nw.llm.base import LLMProvider
from nw.materials.work_catalog import SourceDesk
from nw.store import Store
from nw.task_models import TaskRequest, content_sha256


PROMPT = """[CASTING_EDITOR] 你是独立的剧情编辑，此时尚未为这批需求建卡。对照批准的故事前置、已有人物和这批提议，逐项裁定。
还原一件具体事情：当事人面临什么难题，谁因什么条件可以采取哪一步，局面因此发生什么改变？拿掉这个承担者会怎样？
认可等义表达、符合人物利益的意外选择以及实际改变局面的细小动作。不能只靠关键词相同、引文正确、角色标签或提议者自己的结论。
逐一考虑环境本身能否解决问题、已有角色是否有接触机会和动机、同批职责能否由一人承担。拒绝无依据增人、无关动作、违背既有事实和重复设岗。
先决条件允许多种合理解时，按所选路径的因果判断。剧情本身支持新增人、保密或换人时说明原因即可。
对每个原 id 返回一条 {id,verdict,reason}，verdict 为 accept 或 redesign。reason 写明所依据的具体前置与动作后果，需重设时指出哪一环应改。
只返回 {"judgments":[...]}。"""


def world_conditions(products: dict, context: dict) -> dict:
    cards = [(row['card_id'], row['body']) for row in context.get('approved_cards', ()) if row['kind'] == 'world']
    cards.extend((row['key'], row['body']) for row in products['members'])
    return {'rules': {key: {k: v for k, v in body.items() if k in ('rule', 'limits', 'cost')}
                      for key, body in cards}, 'limitations': products['limitations']}


def _inputs(context: dict, demands: list[dict]) -> dict:
    from nw.materials.cast_demands import roster, source_options

    sources = source_options(context)
    cast = roster(context)
    facts = [{k: v for k, v in row.items() if k in ('entity_id', 'holder', 'claim', 'predicate', 'value', 'story_order')}
             for row in context.get('accepted_state', ()) if row.get('entity_id') in cast or row.get('holder') in cast]
    result = {'scope': context['scope'], 'plot_sources': sources, 'current_cast': cast,
              'branch_facts': facts, 'demands': demands}
    if limits := context.get('cast_world_conditions'):
        result['world_conditions'] = limits
    if constraints := context.get('brief', {}).get('constraints'):
        result['brief_constraints'] = constraints
    if prior := context.get('cast_prior_work'):
        result['prior_performances'] = prior
    if context.get('plot_cast_gap'):
        result['plot_gap'] = context['plot_cast_gap']
        result['gap_upstream'] = context['cast_gap_inputs']
    return result


def _judgments(raw: dict, demands: list[dict]) -> list[dict]:
    rows = raw.get('judgments')
    ids = {d['id'] for d in demands}
    if set(raw) != {'judgments'} or not isinstance(rows, list) or len(rows) != len(ids):
        raise ValueError('CASTING_EDITOR: 需要逐项裁定本批剧情用人需求')
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {'id', 'verdict', 'reason'} or (
            not isinstance(row['id'], str) or row['id'] not in ids or row['id'] in seen
            or row['verdict'] not in ('accept', 'redesign')
            or not isinstance(row['reason'], str) or not row['reason'].strip()
        ):
            raise ValueError('CASTING_EDITOR: 用人裁定的对象、结论或具体理由无效')
        seen.add(row['id'])
    return rows


def revisions(review: dict) -> list[dict]:
    return [row for row in review['judgments'] if row['verdict'] == 'redesign']


def require_approved(review: dict, context: dict, demands: list[dict], calls: list[dict]) -> None:
    if not isinstance(review, dict) or review.get('input_sha256') != content_sha256(_inputs(context, demands)):
        raise ValueError('CASTING_EDITOR: 用人裁定没有对应当前剧情前置和当前阵容')
    receipt = {k: review.get(k) for k in ('task_id', 'manifest_id')}
    if not all(receipt.values()) or receipt not in calls:
        raise ValueError('CASTING_EDITOR: 缺少建卡前独立核验的模型调用记录')
    _judgments({'judgments': review.get('judgments')}, demands)
    if todo := revisions(review):
        raise ValueError('CASTING_EDITOR: 剧情用人须重新设计。' + '；'.join(r['id'] + ' ' + r['reason'] for r in todo))


def review_demands(store: Store, request: TaskRequest, provider: LLMProvider, config: Config, desk: SourceDesk,
                   context: dict, demands: list[dict], *, retry_failed: bool, verify: Callable | None) -> tuple[dict, dict]:
    from nw.materials.work_session import _study_call

    payload = _inputs(context, demands)
    digest = content_sha256(payload)
    cfg, editor = resolve_stage_runtime(config, provider, 'review')
    if editor.name == 'ollama':
        item = {'type': 'object', 'properties': {
            'id': {'type': 'string', 'enum': [d['id'] for d in demands]},
            'verdict': {'type': 'string', 'enum': ['accept', 'redesign']}, 'reason': {'type': 'string'}},
            'required': ['id', 'verdict', 'reason'], 'additionalProperties': False}
        shape = {'type': 'object', 'properties': {'judgments': {'type': 'array', 'items': item}},
                 'required': ['judgments'], 'additionalProperties': False}
        cfg = replace(cfg, params={**cfg.params, 'format': shape})
    raw, receipt = _study_call(store, request, cfg, editor, 0, payload, [], desk, retry_failed, verify,
        version='cast-editor-v1:' + digest, prompt=PROMPT, validator=lambda raw: _judgments(raw, demands))
    return {**receipt, 'input_sha256': digest, 'judgments': raw['judgments']}, receipt


def edit_world_demands(store: Store, request: TaskRequest, provider: LLMProvider, config: Config, desk: SourceDesk,
                       context: dict, record: dict, calls: list[dict], *, retry_failed: bool, verify: Callable | None) -> dict:
    from nw.materials import cast_demands
    from nw.materials.phase_routes import product_ref
    from nw.materials.phase_schema import obj
    from nw.materials.work_session import _study_call

    demands = record['products']['cast_demands']
    if not demands:
        return record
    review, receipt = review_demands(store, request, provider, config, desk, context, demands,
                                     retry_failed=retry_failed, verify=verify)
    calls.append(receipt)
    if corrections := revisions(review):
        source = product_ref(record)
        feedback = {**_inputs(context, demands), 'world_ref': source, 'corrections': corrections}
        cfg, author = resolve_stage_runtime(config, provider, 'world_design')
        if author.name == 'ollama':
            fields = {}
            cast_demands.add_schema('world_design', fields)
            cfg = replace(cfg, params={**cfg.params, 'format': obj(fields)})

        def validate(raw: dict) -> None:
            if set(raw) != {'cast_demands'}:
                raise ValueError('CASTING_EDITOR: 本次只重设用人需求')
            cast_demands.validate_demands(raw['cast_demands'], feedback['plot_sources'], feedback['current_cast'])

        prompt = ('[CASTING_REDESIGN] 按独立编辑指出的具体问题重设用人需求。返回 {"cast_demands":[...]}。'
                  '保留有效职责，可以合并、改作复用或撤销多余职责。' + cast_demands.world_instruction(context))
        amended, receipt = _study_call(store, request, cfg, author, 0, feedback, [], desk, retry_failed, verify,
            version='cast-demand-redesign-v1', prompt=prompt, validator=validate)
        calls.append(receipt)
        products = {**record['products'], **amended}
        record = {**record, 'products': products, 'task_id': receipt['task_id'], 'sha256': content_sha256(products),
                  'cast_demand_revision': {'basis': source, 'demands': demands, 'rejected_review': review, 'call': receipt}}
        demands = amended['cast_demands']
        if not demands:
            return record
        review, receipt = review_demands(store, request, provider, config, desk, context, demands,
                                         retry_failed=retry_failed, verify=verify)
        if receipt not in calls:
            calls.append(receipt)
    require_approved(review, context, demands, calls)
    return {**record, 'cast_editor_review': review}


def verify_world(record: dict, context: dict, calls: list[dict]) -> None:
    if context.get('cast_world_conditions') != world_conditions(record['products'], context):
        raise ValueError('CASTING_EDITOR: 用人判断引用的世界条件与本步世界设计不同')
    correction = record.get('cast_demand_revision')
    if correction:
        from nw.materials.phase_routes import product_ref

        initial = correction['demands']
        basis = {**correction['basis'], 'products': {**record['products'], 'cast_demands': initial}}
        product_ref(basis)
        rejected = correction['rejected_review']
        _judgments({'judgments': rejected['judgments']}, initial)
        if (not revisions(rejected) or rejected['input_sha256'] != content_sha256(_inputs(context, initial))
            or {k: rejected[k] for k in ('task_id', 'manifest_id')} not in calls
            or basis['stage'] != 'world_design' or not any(c['task_id'] == basis['task_id'] for c in calls)
            or correction['call'] not in calls or correction['call']['task_id'] != record['task_id']):
            raise ValueError('CASTING_EDITOR: 用人修订与初版世界设计或编辑退回记录不一致')
    if demands := record['products']['cast_demands']:
        require_approved(record.get('cast_editor_review'), context, demands, calls)


def verify_calls(store: Store, session: dict) -> None:
    if not session['context'].get('cast_demand_policy'):
        return
    from nw.tasks import read_input_manifest, read_task

    world = next(r for r in session['stages'] if r['stage'] == 'world_design')
    reviews = [world.get('cast_editor_review'), session.get('cast_repair', {}).get('editor_review')]
    if revised := world.get('cast_demand_revision'):
        call = read_task(store, revised['call']['task_id'])
        _, saved = read_input_manifest(store, revised['call']['manifest_id'])
        if (call.validation != 'VALID' or call.parsed != {'cast_demands': world['products']['cast_demands']}
                or saved['study_input']['world_ref'] != revised['basis']
                or saved['study_input']['demands'] != revised['demands']):
            raise ValueError('CASTING_EDITOR: 用人修订与模型保存的原始版本不同')
        reviews.append(revised['rejected_review'])
    for review in filter(None, reviews):
        call = read_task(store, review['task_id'])
        _, saved = read_input_manifest(store, review['manifest_id'])
        if (call.validation != 'VALID' or call.parsed != {'judgments': review['judgments']}
                or content_sha256(saved['study_input']) != review['input_sha256']):
            raise ValueError('CASTING_EDITOR: 剧情编辑裁定与原始调用不同')
