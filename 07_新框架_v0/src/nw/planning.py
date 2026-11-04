
"""Budgeted design calls, immutable candidates, and read-only proposal inspection."""
from dataclasses import asdict, replace
import json
from uuid import uuid4

from nw.call_budget import create_budget, prepare_call
from nw.call_control import model_settings
from nw.cards import card_input_ref, _append, _link, eligible_rule_refs, read_card
from nw.config import Config
from nw.llm.base import LLMProvider
from nw.models import Brief
from nw.plan_application import apply_plan
from nw.plan_contract import PlanProposal, SCOPES, plan_prompt, validate_plan
from nw.selection import _keywords
from nw.sources import read_span
from nw.store import Store
from nw.story_dependencies import add_dependency, legacy_ref, outline_ref
from nw.story_models import CardRef, SourceRef, StateHead
from nw.story_state import baseline_for, current_head, replay, revision_state, selected_operations
from nw.task_models import Budget, Finding, InputManifest, Ref, TaskRequest, canonical, content_sha256
from nw.tasks import freeze_manifest, read_input_manifest, read_task, run_task


def _brief(store: Store, version: int) -> Brief:
    for brief in store.briefs():
        if brief.version == version:
            return brief
    raise ValueError('Brief version not found')


def _application(store: Store, proposal_id: str) -> dict | None:
    row = store.connection.execute('SELECT mapping_json FROM plan_applications WHERE proposal_id=?',
                                   (proposal_id,)).fetchone()
    return json.loads(row[0]) if row else None


def _materials(store: Store, terms: str) -> list[dict]:
    keywords = _keywords([terms])
    ranked = []
    for ref in eligible_rule_refs(store):
        card = read_card(store, ref)
        body = card['body']
        hits = keywords & _keywords([body['title'], body['applies_when'], *body.get('tags', [])])
        if hits:
            ranked.append((-len(hits), ref.card_id, card))
    return [item[2] for item in sorted(ranked)[:5]]


def _source_refs(store: Store, cards: list[dict]) -> tuple[dict, ...]:
    refs = {}
    for card in cards:
        for raw in card['source_refs']:
            source = SourceRef(**raw)
            read_span(store, source)
            refs[source] = raw
    return tuple(refs.values())


def _plan_scope(store: Store, scope: str, branch: str, parent_id: str | None) -> tuple[StateHead | None, dict | None]:
    if scope not in SCOPES:
        raise ValueError('Unknown plan scope')
    if scope == 'book' and parent_id:
        raise ValueError('Book scope starts a new direction')
    if scope != 'book' and not parent_id:
        raise ValueError('Detailed design requires an applied parent proposal')
    head = current_head(store, branch) if store.managed_story() else None
    if head is None and branch != 'main':
        raise ValueError('Plan branches require story adoption')
    if scope == 'replan' and (head is None or branch == 'main'):
        raise ValueError('Replan requires a managed candidate branch')
    parent = _application(store, parent_id) if parent_id else None
    if parent_id and parent is None:
        raise ValueError('Select and apply a parent proposal before designing details')
    if parent and head:
        active = {(row['card_id'], row['version']) for row in revision_state(store, head)['settings']}
        if (parent['root']['card_id'], parent['root']['version']) not in active:
            raise ValueError('Selected parent is unavailable on this branch')
    return head, parent


def propose_plan(store: Store, brief_ref: Ref | int, scope: str, provider: LLMProvider, config: Config,
                 budget: Budget, *, parent_id: str | None = None, branch: str = 'main') -> PlanProposal:
    ident = uuid4().hex
    budget_id = create_budget(store, f'plan:{ident}', budget)
    request, package = prepare_plan_task(store, brief_ref, scope, provider, config, budget_id, ident,
                                         parent_id=parent_id, branch=branch)
    return _run_plan(store, request, package, provider, config)


def prepare_plan_task(store: Store, brief_ref: Ref | int, scope: str, provider: LLMProvider,
                      config: Config, budget_id: str, ident: str, *, parent_id: str | None = None,
                      branch: str = 'main') -> tuple[TaskRequest, dict]:
    from nw.call_budget import read_budget

    budget = read_budget(store, budget_id)
    prompt = plan_prompt(scope)
    with store.connection:
        store.connection.execute('BEGIN')
        head, parent = _plan_scope(store, scope, branch, parent_id)
        brief = _brief(store, brief_ref.version if isinstance(brief_ref, Ref) else brief_ref)
        project_id = store.project().id
        brief_pin = legacy_ref('brief', project_id, brief)
        if isinstance(brief_ref, Ref) and brief_ref != brief_pin:
            raise ValueError('Brief reference does not match the recorded version')
        state = revision_state(store, head) if head else None
        settings = state['settings'] if state is not None else parent['approvals'] if parent else []
        facts = (replay(baseline_for(store, head.branch_id), selected_operations(store, state))
                 if head is not None else [])
        cards = [read_card(store, CardRef(row['card_id'], row['version'])) for row in settings]
        parent_card = read_card(store, CardRef(**parent['root'])) if parent else None
        terms = ' '.join((brief.text, brief.constraints, parent_card['body']['choice'] if parent_card else ''))
        methods = _materials(store, terms)
        outline = [asdict(row) for row in store.list('chapter')]
        places = [{'id': row.id, 'chapter_id': row.chapter_id, 'index': row.index} for row in store.list('scene')]
        outline_pin = outline_ref(store)
        package = {'brief': asdict(brief), 'scope': scope, 'parent_id': parent_id, 'parent': parent_card,
                   'branch_head': asdict(head) if head else None, 'approved_cards': cards,
                   'accepted_state': [asdict(fact) for fact in facts],
                   'outline': {'chapters': outline, 'scenes': places}, 'method_cards': methods}
        while methods and len(prompt) + len(canonical(package)) > budget.context_char_limit:
            methods.pop()
        sources = _source_refs(store, [*cards, *methods])
    messages = [{'role': 'system', 'content': prompt}, {'role': 'user', 'content': canonical(package)}]
    params, _ = prepare_call(store, budget_id, provider.name, config.params, messages)
    refs = tuple({'card_id': card['card_id'], 'version': card['version']} for card in [*cards, *methods])
    # Planning is author-facing, with the branch pin inside the frozen design work package.
    manifest_id = f'plan:{ident}'
    freeze_manifest(store, InputManifest(
        manifest_id, 'plan', model_settings(provider, config.model, params, 'story-plan-v1'),
        content_sha256(package), brief_ref=brief_pin,
        card_refs=refs, source_refs=sources, dependency_refs=(outline_pin,)), package)
    return TaskRequest(ident, project_id, 'plan', manifest_id, {'messages': messages}, budget_id), package


def retry_plan(store: Store, ident: str, provider: LLMProvider, config: Config) -> PlanProposal:
    _, package = plan_input(store, ident)
    row = store.connection.execute('SELECT request_json FROM task_calls WHERE id=?', (ident,)).fetchone()
    previous = TaskRequest(**json.loads(row[0]))
    request = replace(previous, id=uuid4().hex, retry_of=ident, attempt=previous.attempt + 1)
    return _run_plan(store, request, package, provider, config)


def _run_plan(store: Store, request: TaskRequest, package: dict, provider: LLMProvider,
              config: Config) -> PlanProposal:
    result = run_task(store, request, provider, config,
                      validate=lambda output: validate_plan(output, package['scope'], _known_cards(package)))
    if result.validation != 'VALID':
        raise ValueError(f'Plan {result.status}/{result.validation}: {result.id}')
    return show_plan(store, request.id)


def _known_cards(package: dict) -> dict[str, str]:
    return {card['card_id']: card['kind'] for card in package['approved_cards']}


def plan_input(store: Store, ident: str) -> tuple[dict, dict]:
    row = store.connection.execute("SELECT manifest_id FROM task_calls WHERE id=? AND kind='plan'", (ident,)).fetchone()
    if row is None:
        raise ValueError('Plan task not found')
    manifest, package = read_input_manifest(store, row[0])
    if manifest['settings']['prompt_version'] != 'story-plan-v1':
        raise ValueError('Task is not a story proposal')
    return manifest, package


def _translate(body: dict, refs: dict[str, CardRef]) -> dict:
    def ident(key: str) -> str:
        return refs[key].card_id
    resolved = dict(body)
    for field in ('holders', 'characters'):
        if field in body:
            resolved[field] = [ident(key) for key in body[field]]
    if 'pov' in body:
        resolved['pov'] = ident(body['pov'])
    if 'character_goals' in body:
        resolved['character_goals'] = {ident(key): goal for key, goal in body['character_goals'].items()}
    return resolved


def _save_candidates(store: Store, ident: str, raw: dict, package: dict) -> PlanProposal:
    validate_plan(raw, package['scope'], _known_cards(package))
    parent = package['parent']
    roots, materialization, findings = [], [], []
    inherited = {card['card_id']: CardRef(card['card_id'], card['version']) for card in package['approved_cards']}
    for i, candidate in enumerate(raw['candidate_cards'], 1):
        prefix = f'plan-{ident}-{i}'
        members = {row['key']: CardRef(f"{prefix}-{row['key']}", 1) for row in candidate['members']}
        refs = {**inherited, **members}
        orders = {row['card']: row['story_order'] for ch in candidate['chapters'] for row in ch['scenes']}
        open_rules = list(candidate['open_world_rules'])
        if parent and raw['scope'] != 'replan':
            open_rules.extend(parent['body'].get('unknowns', []))
        for row in candidate['members']:
            if row['kind'] == 'world':
                open_rules.extend(row['body'].get('unknowns', []))
        open_rules = list(dict.fromkeys(open_rules))
        for row in candidate['members']:
            ref = members[row['key']]
            body = _translate(row['body'], refs)
            if row['kind'] == 'scene':
                body['story_time'] = str(orders[row['key']])
                questions = [*body.get('unknowns', []), *open_rules]
                if questions:
                    body['unknowns'] = list(dict.fromkeys(questions))
            _append(store, {'card_id': ref.card_id, 'kind': row['kind'], 'origin': 'model', 'body': body}, None)
        member_hashes = [asdict(card_input_ref(read_card(store, ref))) for ref in members.values()]
        root_body = {**candidate['body'], 'members': member_hashes, 'unknowns': open_rules}
        root = _append(store, {'card_id': prefix, 'kind': 'plot', 'origin': 'model', 'body': root_body}, None)
        root_hash = card_input_ref(read_card(store, root))
        if parent:
            parent_ref = CardRef(parent['card_id'], parent['version'])
            _link(store, root, parent_ref, 'supersedes' if raw['scope'] == 'replan' else 'depends_on')
            add_dependency(store, root_hash, card_input_ref(parent))
        for row in candidate['members']:
            member = members[row['key']]
            _link(store, root, member, 'contains')
            member_hash = card_input_ref(read_card(store, member))
            add_dependency(store, member_hash, root_hash)
            for key in row.get('requires', []):
                _link(store, member, refs[key], 'depends_on')
                add_dependency(store, member_hash, card_input_ref(read_card(store, refs[key])))
        roots.append(root)
        materialization.append({'root': asdict(root), 'members': {key: asdict(ref) for key, ref in members.items()},
                                'chapters': candidate['chapters']})
        findings.extend(asdict(Finding('OPEN_WORLD_RULE', 'hard', asdict(root_hash), [], question,
                                       '由作者确认规则与限制后重做场景设计', 'OPEN'))
                        for question in open_rules)
    return PlanProposal(ident, raw['scope'], roots, materialization, findings, ident)


def show_plan(store: Store, ident: str) -> PlanProposal:
    _, package = plan_input(store, ident)
    task = read_task(store, ident)
    if task.validation != 'VALID':
        raise ValueError(f'Plan {task.status}/{task.validation}: {ident}')
    with store.connection:
        store.connection.execute('BEGIN IMMEDIATE')
        raw = json.loads(store.connection.execute('SELECT result_json FROM task_calls WHERE id=?', (ident,)).fetchone()[0])
        if 'plan_proposal' not in raw:
            proposal = _save_candidates(store, ident, raw, package)
            raw = asdict(proposal)
            store.connection.execute('UPDATE task_calls SET result_json=? WHERE id=?',
                                     (canonical({'plan_proposal': raw}), ident))
        else:
            raw = raw['plan_proposal']
        raw['candidate_cards'] = [CardRef(**ref) for ref in raw['candidate_cards']]
        raw['application'] = _application(store, ident)
        return PlanProposal(**raw)
