
"""Budgeted design calls, immutable candidates, and read-only proposal inspection."""
from dataclasses import asdict, replace
import json
from uuid import uuid4

from nw.call_budget import create_budget, prepare_call
from nw.call_control import model_settings
from nw.chapter_state import continuation_chapter_state
from nw.cards import card_input_ref, _append, _link, eligible_rule_refs, read_card
from nw.config import Config
from nw.llm.base import LLMProvider
from nw.materials.binding import PROCESS, material_prompt, required_for, scene_routes, translate_bindings, verify_materials
from nw.materials.stage_input import input_record, model_package
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
                 budget: Budget, *, parent_id: str | None = None, branch: str = 'main',
                 governance_inputs: dict | None = None) -> PlanProposal:
    ident = uuid4().hex
    budget_id = create_budget(store, f'plan:{ident}', budget)
    request, package = prepare_plan_task(store, brief_ref, scope, provider, config, budget_id, ident,
                                         parent_id=parent_id, branch=branch, governance_inputs=governance_inputs)
    return _run_plan(store, request, package, provider, config)


def prepare_plan_task(store: Store, brief_ref: Ref | int, scope: str, provider: LLMProvider,
                      config: Config, budget_id: str, ident: str, *, parent_id: str | None = None,
                      branch: str = 'main', materials: list[dict] = (),
                      material_deferrals: dict | None = None,
                      governance_inputs: dict | None = None,
                      production_method_policy: dict | None = None) -> tuple[TaskRequest, dict]:
    from nw.call_budget import read_budget

    budget = read_budget(store, budget_id)
    prompt = plan_prompt(scope)
    manifest_id = f'plan:{ident}'
    with store.connection:
        store.connection.execute('BEGIN')
        head, parent = _plan_scope(store, scope, branch, parent_id)
        if parent:
            from nw.materials.work_application import validate_saved_work
            validate_saved_work(store, parent_id, parent.get('material_design', {}), parent['root'])
        inherited = parent.get('material_design', {}) if parent else {}
        by_id = {row['source']['id']: row for row in inherited.get('materials', [])}
        brief = _brief(store, brief_ref.version if isinstance(brief_ref, Ref) else brief_ref)
        parent_card = read_card(store, CardRef(**parent['root'])) if parent else None
        recall = None
        from nw.materials.source_set import selection_status
        staged_catalog = selection_status(store.directory.parent) is not None
        if not staged_catalog and not materials and (not by_id or inherited.get('recall')):
            from nw.materials.recall import recall_materials
            terms = ' '.join((brief.text, brief.constraints, parent_card['body']['choice'] if parent_card else ''))
            automatic, recall = recall_materials(store.directory.parent, terms, scope=scope, existing=list(by_id.values()))
            by_id.update({row['source']['id']: row for row in automatic})
        for row in materials:
            key = row['source']['id']
            if key in by_id and canonical(by_id[key]) != canonical(row):
                raise ValueError('MATERIAL_SCOPE: redesign the parent before changing an inherited decision')
            by_id[key] = row
        materials = list(by_id.values())
        deferrals = (material_deferrals or {}) if scope != 'book' else {}
        if deferrals.keys() - scene_routes(materials).keys():
            raise ValueError('MATERIAL_SCOPE: only adopted sources can be deferred in a detail plan')
        book_bindings = inherited.get('book_bindings', {})
        if scope != 'book' and required_for(materials, book=True).keys() != book_bindings.keys():
            raise ValueError('MATERIAL_SCOPE: confirm type commitments in the book plan first')
        processes = {row['profile'] for row in materials if row['request']['disposition'] == 'required'} & PROCESS
        if scope != 'book' and processes & {'material_selection','material_conversion'} and not scene_routes(materials, deferrals):
            raise ValueError('MATERIAL_SCOPE: selection and conversion require concrete scene-level materials')
        verify_materials(store.directory.parent, materials)
        prompt += material_prompt(materials, book=scope == 'book', deferrals=deferrals)
        brief = _brief(store, brief_ref.version if isinstance(brief_ref, Ref) else brief_ref)
        project_id = store.project().id
        brief_pin = legacy_ref('brief', project_id, brief)
        if isinstance(brief_ref, Ref) and brief_ref != brief_pin:
            raise ValueError('Brief reference does not match the recorded version')
        state = revision_state(store, head) if head else None
        settings = state['settings'] if state is not None else parent['approvals'] if parent else []
        operations=selected_operations(store,state) if state is not None else []
        facts = (replay(baseline_for(store, head.branch_id), operations)
                 if head is not None else [])
        cards = [read_card(store, CardRef(row['card_id'], row['version'])) for row in settings]
        parent_card = read_card(store, CardRef(**parent['root'])) if parent else None
        terms = ' '.join((brief.text, brief.constraints, parent_card['body']['choice'] if parent_card else ''))
        methods = _materials(store, terms)
        outline = [asdict(row) for row in store.list('chapter')]
        places = [{'id': row.id, 'chapter_id': row.chapter_id, 'index': row.index} for row in store.list('scene')]
        outline_pin = outline_ref(store)
        package = {'brief': asdict(brief), 'scope': scope, 'parent_id': parent_id, 'parent': parent_card,
                   'plan_checkpoint':{'task_id':ident,'budget_id':budget_id,'project_id':project_id},
                   'material_mode':'source_driven_required' if config.source_driven else 'legacy_when_catalog_missing_explicit',
                   'branch_head': asdict(head) if head else None, 'approved_cards': cards,
                   'accepted_state': [asdict(fact) for fact in facts],
                   'accepted_changes':[op for op in operations if op['claim']=='fact' and op['holder']=='WORLD'
                       and op['expected_old'] is not None and canonical(op['expected_old'])!=canonical(op['new_value'])],
                   'outline': {'chapters': outline, 'scenes': places}, 'method_cards': methods}
        if inherited.get('work_application'):
            session=inherited['work_session']
            package['parent_material_work']={'application':inherited['work_application'],
                **({'production_method_parents': session['production_method_parents']}
                   if any(p.get('world_design_basis') for p in session.get('production_method_parents', [])) else {}),
                'stages':session.get('stages',[]),'work_plan':session.get('result',{}).get('work_plan',[]),
                'selected_direction':{k:v for k,v in parent_card['body'].items() if k not in ('members','unknowns')}}
            if session.get('context', {}).get('design_network_policy'):
                from nw.materials.design_network import inherited as parent_design_uses
                approved = {a['card_id']: {'card_id': a['card_id'], 'version': a['version']} for a in parent['approvals']}
                member_refs = {key: approved[ident] for key, ident in inherited.get('process_context', {}).get('ids', {}).items()
                               if ident in approved}
                package['parent_design_network'] = parent_design_uses(package['parent_material_work'],
                    {**parent.get('members', {}), **member_refs}, cards)
        if production_method_policy:
            from nw.production_methods.policy import normalize
            package['production_method_policy']=normalize(production_method_policy)
        elif inherited.get('work_session',{}).get('production_method_policy'):
            # Turning off new selection cannot abandon an approved parent's design obligations.
            previous_policy=inherited['work_session']['production_method_policy']
            package['production_method_policy']={**previous_policy,'tasks':[]}
        if recall:
            package['material_recall'] = recall
        if governance_inputs is not None:
            from nw.materials.phase_routes import phase_order
            if (not isinstance(governance_inputs, dict) or governance_inputs.keys() - set(phase_order(scope))
                    or not all(isinstance(value, dict) for value in governance_inputs.values())):
                raise ValueError('MATERIAL_GOVERNANCE: expected inputs keyed by current planning stage')
            material_governance = dict(governance_inputs)
            if 'plot_design' in material_governance:
                project_inputs = dict(material_governance['plot_design'])
                project_inputs.pop('length_policy', None)
                project_inputs.pop('length_auto', None)
                project_inputs.pop('length_recommendation', None)
                if project_inputs:
                    material_governance['plot_design'] = project_inputs
                elif governance_inputs['plot_design']:
                    del material_governance['plot_design']
            package['governance_inputs'] = material_governance
        if head:
            from nw.materials.stage_effects import accepted_feedback
            feedback = accepted_feedback(store, head)
            if feedback:
                package['material_feedback'] = feedback
        if materials:
            package.update(materials=materials, book_bindings=book_bindings, material_deferrals=deferrals)
        # Pin the in-step text before the first stage, so resuming keeps the original prompts.
        existing = store.connection.execute('SELECT 1 FROM input_manifests WHERE id=?', (manifest_id,)).fetchone()
        if existing:
            _, previous_package = read_input_manifest(store, manifest_id)
            for key in ('length_context', 'stage_materials', 'stage_source_policy', 'chapter_handoff', 'chapter_summary', 'chapter_reviews', 'chapter_progress_policy',
                        'type_hierarchy_enabled', 'type_source_scope_enabled', 'type_name_evidence_enabled',
                        'dynamic_reference_checks', 'dynamic_screening_enabled', 'scene_source_binding_policy',
                        'action_state_policy', 'action_template_priority_enabled', 'network_prerequisite_policy',
                        'multi_action_policy', 'narration_policy', 'cast_previous_appearances', 'cast_demand_policy',
                        'cast_source_cards', 'cast_completed_direction', 'method_task_stages',
                        'network_layer_policy', 'early_network_policy', 'same_stage_network_policy',
                        'type_network_policy', 'world_network_policy', 'world_advancement_policy', 'world_conversion_policy',
                        'world_resource_policy', 'world_market_policy', 'world_history_policy', 'design_network_policy',
                        'parent_design_network'):
                if key in previous_package:
                    package[key] = previous_package[key]
        else:
            if scope == 'chapter' and head is not None:
                handoff = continuation_chapter_state(store, head, state)
                if handoff is not None:
                    # A legacy review of general progress did not separately verify the planned open question.
                    for advance in handoff.get('reviewed_progress', ()):
                        if not advance.get('pressure_evidence'):
                            advance['possible_next_pressure'] = None
                    package['chapter_handoff'] = handoff
                    from nw.chapter_records import continuation_reviews, continuation_summary
                    from nw.models import Chapter

                    if summary := continuation_summary(store, head, handoff['chapter']['index']):
                        package['chapter_summary'] = summary
                    if reviews := continuation_reviews(store, head, Chapter(**handoff['chapter'])):
                        package['chapter_reviews'] = reviews
            if (store.directory.parent / 'materials/catalog.db').is_file():
                from nw.materials.phase_context import ACTION_STATE_POLICY
                from nw.materials.story_policies import current as current_story_policies
                from nw.materials.phase_flow import STAGE_MATERIALS
                from nw.materials.phase_routes import phase_order
                from nw.materials.scene_source_bindings import POLICY as SCENE_SOURCE_BINDING_POLICY
                from nw.materials.scene_actions import MULTI_ACTION_POLICY
                package['type_hierarchy_enabled'] = True
                package['type_source_scope_enabled'] = True
                package['type_name_evidence_enabled'] = True
                package['dynamic_reference_checks'] = True
                package['dynamic_screening_enabled'] = True
                package['scene_source_binding_policy'] = SCENE_SOURCE_BINDING_POLICY
                package['multi_action_policy'] = MULTI_ACTION_POLICY
                package['action_state_policy'] = ACTION_STATE_POLICY
                package.update(current_story_policies())
                from nw.materials.cast_demands import completed_direction, source_card_ids
                package['cast_source_cards'] = source_card_ids(parent, cards, package.get('chapter_handoff', {}), scope)
                package['cast_completed_direction'] = completed_direction(parent, package.get('chapter_handoff', {}))
                from nw.materials.cast_design import previous_appearances
                package['cast_previous_appearances'] = previous_appearances(store, cards)
                package['action_template_priority_enabled'] = True
                package['stage_materials'] = {
                    stage: STAGE_MATERIALS[stage] for stage in phase_order(scope) if stage in STAGE_MATERIALS
                }
                if staged_catalog:
                    from nw.materials.network_followup import POLICY as NETWORK_FOLLOWUP_POLICY
                    from nw.materials.network_layers import POLICY as NETWORK_LAYER_POLICY
                    from nw.materials.type_network import POLICY as TYPE_NETWORK_POLICY
                    from nw.materials.world_advancement import POLICY as WORLD_ADVANCEMENT_POLICY
                    from nw.materials.world_conversion import POLICY as WORLD_CONVERSION_POLICY
                    from nw.materials.world_resources import POLICY as WORLD_RESOURCE_POLICY
                    from nw.materials.world_market import POLICY as WORLD_MARKET_POLICY
                    from nw.materials.world_history import POLICY as WORLD_HISTORY_POLICY
                    from nw.materials.world_network import POLICY as WORLD_NETWORK_POLICY
                    from nw.materials.network_workflow import EARLY_POLICY, POLICY as NETWORK_POLICY
                    from nw.materials.stage_input import STEP_SOURCE_POLICY
                    package['stage_source_policy'] = STEP_SOURCE_POLICY
                    package['network_prerequisite_policy'] = NETWORK_POLICY
                    package['early_network_policy'] = EARLY_POLICY
                    package['same_stage_network_policy'] = NETWORK_FOLLOWUP_POLICY
                    package['type_network_policy'] = TYPE_NETWORK_POLICY
                    package['world_network_policy'] = WORLD_NETWORK_POLICY
                    package['world_advancement_policy'] = WORLD_ADVANCEMENT_POLICY
                    package['world_conversion_policy'] = WORLD_CONVERSION_POLICY
                    package['world_resource_policy'] = WORLD_RESOURCE_POLICY
                    package['world_market_policy'] = WORLD_MARKET_POLICY
                    from nw.materials.design_network_catalog import POLICY as DESIGN_NETWORK_POLICY
                    package['design_network_policy'] = DESIGN_NETWORK_POLICY
                    package['world_history_policy'] = WORLD_HISTORY_POLICY
                    package['network_layer_policy'] = NETWORK_LAYER_POLICY
        from nw.length_settings import effective_brief_text
        from nw.length_plan import design_context, instructions
        if not existing and package.get('production_method_policy'):
            from nw.production_methods.sources import MethodReader, task_routes
            routes=task_routes(MethodReader(store.directory.parent), package)
            if routes:
                package['method_task_stages']=routes
        override = (governance_inputs or {}).get('plot_design', {}).get('length_policy')
        if existing:
            package['brief'] = previous_package['brief']
            if 'governance_inputs' in previous_package:
                package['governance_inputs'] = previous_package['governance_inputs']
            if 'length_override' in previous_package:
                package['length_override'] = previous_package['length_override']
        elif override is not None:
            package['length_override'] = override
            package['brief']['text'] = effective_brief_text(package['brief']['text'], override)
        automatic = (governance_inputs or {}).get('plot_design', {}).get('length_auto') is True
        if not existing:
            parent_chapters = tuple(ch['index'] for ch in (parent or {}).get('chapters', ()))
            length = design_context(store, package['brief'], state, parent_card, automatic=automatic,
                                    parent_chapters=parent_chapters)
            if length:
                suggestion = (governance_inputs or {}).get('plot_design', {}).get('length_recommendation')
                if suggestion and length['policy'].get('length_mode') == 'tiered' and not length['policy'].get('target_words'):
                    length['length_recommendation'] = suggestion
                package['length_context'] = length
        if package.get('length_context'):
            prompt += '\n' + instructions('plan', package['length_context'])
        while methods and len(prompt) + len(canonical(model_package(package))) > budget.context_char_limit:
            methods.pop()
        sources = _source_refs(store, [*cards, *methods])
        if materials:
            package['material_input']=input_record(package)
    messages = [{'role': 'system', 'content': prompt}, {'role': 'user', 'content': canonical(model_package(package))}]
    params, _ = prepare_call(store, budget_id, provider.name, config.params, messages)
    refs = tuple({'card_id': card['card_id'], 'version': card['version']} for card in [*cards, *methods])
    # Planning is author-facing, with the branch pin inside the frozen design work package.
    freeze_manifest(store, InputManifest(
        manifest_id, 'plan', model_settings(provider, config.model, params, 'story-plan-v1'),
        content_sha256(package), brief_ref=brief_pin,
        card_refs=refs, source_refs=sources, dependency_refs=(outline_pin,)), package)
    return TaskRequest(ident, project_id, 'plan', manifest_id, {'messages': messages}, budget_id), package


def retry_plan(store: Store, ident: str, provider: LLMProvider, config: Config) -> PlanProposal:
    _, package = plan_input(store, ident)
    row = store.connection.execute('SELECT request_json FROM task_calls WHERE id=?', (ident,)).fetchone()
    if row is None:
        checkpoint=package.get('plan_checkpoint',{})
        if checkpoint.get('task_id')!=ident:raise ValueError('Plan checkpoint not found')
        request=TaskRequest(ident,checkpoint['project_id'],'plan','plan:'+ident,{'messages':[]},checkpoint['budget_id'])
        return _run_plan(store,request,package,provider,config,retry_failed=True)
    previous = TaskRequest(**json.loads(row[0]))
    request = replace(previous, id=uuid4().hex, retry_of=ident, attempt=previous.attempt + 1)
    return _run_plan(store, request, package, provider, config)


def _run_plan(store: Store, request: TaskRequest, package: dict, provider: LLMProvider,
              config: Config,*,retry_failed: bool=False) -> PlanProposal:
    from nw.materials.work_session import drive_plan
    try:request,package=drive_plan(store,request,package,provider,config,retry_failed=retry_failed)
    except ValueError as exc:
        raise ValueError(f'{exc}; plan_checkpoint={request.id}; resume with plan retry --id {request.id}') from exc
    from nw.materials.phase_projection import expand_output
    result = run_task(store, request, provider, config,
                      validate=lambda output: validate_plan(expand_output(output,package), package['scope'], _known_cards(package),
                                                            package.get('materials', ()),
                                                            package.get('material_deferrals'),package.get('material_work'),package.get('length_context')))
    if result.validation != 'VALID':
        raise ValueError(f'Plan {result.status}/{result.validation}: {result.reason or ""} {result.id}')
    return show_plan(store, request.id)


def _known_cards(package: dict) -> dict[str, str]:
    return {card['card_id']: card['kind'] for card in package['approved_cards']}


def plan_input(store: Store, ident: str) -> tuple[dict, dict]:
    row = store.connection.execute("SELECT manifest_id FROM task_calls WHERE id=? AND kind='plan'", (ident,)).fetchone()
    if row is None:
        try:manifest,package=read_input_manifest(store,'plan:'+ident)
        except ValueError:raise ValueError('Plan task not found') from None
        if package.get('plan_checkpoint',{}).get('task_id')!=ident:raise ValueError('Plan task not found')
    else:manifest, package = read_input_manifest(store, row[0])
    if manifest['settings']['prompt_version'] not in ('story-plan-v1','story-plan-v2-materials','story-plan-v3-stages'):
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
    if 'introducer' in body.get('casting', {}):
        resolved['casting'] = {**body['casting'], 'introducer': ident(body['casting']['introducer'])}
    return resolved


def _save_candidates(store: Store, ident: str, raw: dict, package: dict) -> PlanProposal:
    from nw.materials.phase_projection import expand_output
    raw=expand_output(raw,package)
    materials = package.get('materials', ())
    validate_plan(raw, package['scope'], _known_cards(package), materials, package.get('material_deferrals'),package.get('material_work'),package.get('length_context'))
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
        chapter_budgets = {}
        if package.get('length_context'):
            from nw.length_plan import chapter_budget
            local_members = {row['key']: row for row in candidate['members']}
            for chapter in candidate['chapters']:
                budget = chapter_budget(chapter, local_members, package['length_context'])
                chapter_budgets.update({scene['card']: budget for scene in chapter['scenes']})
        for row in candidate['members']:
            ref = members[row['key']]
            body = _translate(row['body'], refs)
            if row['kind'] == 'scene':
                if package.get('length_context'):
                    book = candidate['body']['length_plan']
                    policy = package['length_context']['policy']
                    body['length_policy'] = {**policy, 'target_words': book['target_words']}
                    if policy.get('length_mode') != 'tiered':
                        body['length_policy']['chapter_count'] = book['chapter_count']
                elif 'length_override' in package:
                    body['length_policy'] = package['length_override']
                body['story_time'] = str(orders[row['key']])
                if row['key'] in chapter_budgets:
                    body['chapter_word_budget'] = chapter_budgets[row['key']]
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
        application = {'root': asdict(root), 'members': {key: asdict(ref) for key, ref in members.items()},
                       'chapters': candidate['chapters']}
        if materials or package.get('material_work'):
            bindings = candidate.get('material_bindings', {})
            application['material_design'] = {
                'materials': materials,
                'book_bindings': bindings if raw['scope'] == 'book' else package.get('book_bindings',{}),
                'material_deferrals': package.get('material_deferrals', {}),
                'process_bindings': candidate.get('process_bindings', {}),
                'recall': package.get('material_recall'),
                'process_context': {'members': candidate['members'], 'chapters': candidate['chapters'],
                    'existing': _known_cards(package), 'ids': {key: ref.card_id for key,ref in refs.items()}},
            }
            if package.get('material_work'):
                application['material_design'].update(work_session=package['material_work'],work_application=candidate['material_work'],
                    work_context=(candidate if package['material_work'].get('policy') in {'artifact-stage-binding-v3','artifact-stage-binding-v4'} else
                        {'body':candidate['body'],'members':candidate['members'],'material_work':candidate['material_work']}))
            if raw['scope'] != 'book':
                ids = {key: ref.card_id for key, ref in refs.items()}
                application['material_design']['scene_bindings'] = {
                    key: translate_bindings(value, ids) for key, value in bindings.items()}
        materialization.append(application)
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
