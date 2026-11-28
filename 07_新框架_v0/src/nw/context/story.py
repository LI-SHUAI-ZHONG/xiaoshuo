
"""Scene work packages from explicit card and branch versions."""
from collections.abc import Callable
from dataclasses import asdict, dataclass
import json

from nw.call_budget import BudgetExceeded
from nw.cards import card_input_ref, read_card, read_links
from nw.context.base import ContextItem, ContextPackage, package
from nw.context.prior_prose import prior_prose
from nw.materials.binding import verify_materials
from nw.materials.evidence import comparison_draft, scene_checks, scene_materials, verify_preconditions, writer_checks
from nw.materials.stage_input import check_source_keys, step_material_prompt
from nw.materials.steps.writing import MATERIAL as WRITING_MATERIAL
from nw.selection import select_rules
from nw.sources import read_span
from nw.store import Store
from nw.story_delta import candidate_snapshot, draft_ref
from nw.story_dependencies import check_inputs_current, legacy_ref
from nw.story_models import CardRef, Fact, SourceRef, StateHead
from nw.story_state import baseline_for, current_head, position, revision_state, state_at
from nw.task_models import Ref, canonical, content_sha256

WRITE_PROMPT = ('按作者约束和本场任务写正文。人物只凭当前视角可知的信息判断，人物的belief可能有误。'
                '仅在本场明确安排面向读者的叙述节拍时，叙述者可交代该拍获准的事实，保留人物原来的知情范围。'
                '按场景卡的披露边界写作，计划结果仍是候选。方法卡只在适用条件有依据时使用。只输出正文。')

# These scoped sources also have direct uses written into the prose step.
_WRITING_SCOPE_KEYS = frozenset({
    '板块52 感官描写#五感规则',
    '板块52 感官描写#触觉描写',
    '板块52 感官描写#嗅觉描写',
    '板块52 感官描写#味觉描写',
    '板块53 叙述距离#距离变化规则',
    '126.11_多视角切换模板调用',
})


@dataclass(frozen=True)
class StoryScope:
    branch_id: str
    revision: int
    story_order: int
    scene_ref: dict


@dataclass(frozen=True)
class StoryWork:
    scope: StoryScope
    disclosure: tuple[int, int, int]
    package: dict
    brief_ref: Ref | None
    card_refs: tuple[dict, ...]
    source_refs: tuple[dict, ...]
    predecessor_drafts: tuple[Ref, ...]
    dependency_refs: tuple[Ref, ...]
    selection: dict
    material_design_sha256: str | None = None
    prompt: str = WRITE_PROMPT
    writing_source_keys: tuple[str, ...] = ()
    omitted_optional_groups: tuple[str, ...] = ()


def _pov_goals(body: dict, pov: str) -> dict:
    if 'character_goals' not in body:
        return body
    # Other participants' author-side intentions remain in the design. Their
    # observable behaviour is delivered separately through the scene beats.
    return {**body, 'character_goals': {
        actor: goal for actor, goal in body['character_goals'].items() if actor == pov}}


class StoryProvider:
    name = 'story'

    def build(self, project: dict, scene: dict) -> ContextPackage:
        items = []
        if project['brief'] is not None:
            items.append(ContextItem('brief', canonical(project['brief']), '作者需求与硬约束'))
        pov = project['holder']
        scene_body = _pov_goals(scene['body'], pov)
        if 'chapter_word_budget' in scene_body or 'length_policy' in scene_body:
            # The chapter rationale can describe a later reveal outside this scene's POV.
            scene_body = {key: value for key, value in scene_body.items() if key not in ('chapter_word_budget', 'length_policy')}
        progress = project.get('chapter_length_progress')
        if progress and progress.get('length_mode') == 'tiered':
            estimate = scene_body['word_budget']
            scene_body = {k: v for k, v in scene_body.items() if k != 'word_budget'}
            scene_body['scene_length_estimate'] = {'estimated_words': estimate['target_words'], 'reason': estimate['reason']}
        items.append(ContextItem('scene:' + scene['card_id'], canonical(scene_body), '本场任务'))
        if progress:
            items.append(ContextItem('chapter:length', canonical(progress), '按已接受稿与其余场景分配的本场可写字数'))
        from nw.length_plan import model_approved_cards
        for card in model_approved_cards(project['settings']):
            if card['kind'] == 'promise':
                # Planned setups and payoffs reach prose through the authorized scene checks.
                continue
            body = card['body']
            if card['kind'] == 'character' and 'casting' in body:
                from nw.materials.cast_design import writer_card
                body = writer_card(body, own=card['card_id'] == pov)
            elif card['kind'] == 'character' and card['card_id'] != pov and (
                    body.get('visibility') == 'public' or scene_body.get('narrative_person') and body.get('visibility') == 'holders'):
                # Public casting cards often mix a speaking voice with author-side wounds
                # and motives. Private facts the POV has learned come through its state.
                body = {key: body[key] for key in ('name', 'role', 'voice') if key in body}
            elif card['kind'] == 'scene':
                body = _pov_goals(body, pov)
            elif card['kind'] == 'world' and scene_body.get('narrative_person') and 'history' in body:
                # Only a chosen disclosure beat may bring this history into today's scene.
                body = {key: value for key, value in body.items() if key != 'history'}
            items.append(ContextItem('card:' + card['card_id'], canonical(body), '本场确认设定'))
        items.append(ContextItem('pov:' + project['holder'], canonical(project['facts']), '此时POV所知与误信'))
        if project.get('previous'):
            prev = project['previous']
            items.append(ContextItem('previous:' + prev['scene_id'], prev['tail_text'], '同视角紧邻前场正文衔接'))
        if project.get('continuity'):
            items.append(ContextItem('prior-evidence', canonical(project['continuity']),
                                     '前文中支持本场人物所知的段落定位'))
        if project.get('reader'):
            items.append(ContextItem('reader', canonical(project['reader']),
                                     '读者此前也已得知的本场可用信息'))
        for check in project.get('material_checks', ()):
            purpose = ('本场已绑定的世界规则与写法约束' if check['id'] in project.get('ai_world_checks', ())
                       else '作者采用的本场资料约束')
            items.append(ContextItem('material:' + check['id'], canonical(check), purpose))
        for mapping in project.get('mappings', []):
            items.append(ContextItem('rule:' + mapping['ref']['card_id'], canonical(mapping), '场景问题与写法检验'))
        return package(items)


def _ref(raw: dict) -> CardRef:
    try:
        return CardRef(**raw)
    except TypeError as exc:
        raise ValueError('Expected a versioned scene CardRef') from exc


def scene_scope(store: Store, scene_id: str, branch: str = 'main') -> StoryScope:
    scene = store.get('scene', scene_id)
    binding = json.loads(scene.card_json).get('story')
    if not isinstance(binding, dict) or set(binding) != {'scene_ref', 'story_order'}:
        raise ValueError('CONTEXT_PROVIDER_REQUIRED: provide an approved scene CardRef and story time')
    head = current_head(store, branch)
    return StoryScope(branch, head.revision, binding['story_order'], binding['scene_ref'])


def _check_scene(scene: dict, ref: CardRef, scope: StoryScope, snapshot: dict) -> None:
    selected = {(row['card_id'], row['version']) for row in snapshot['settings']}
    if scene['kind'] != 'scene' or (ref.card_id, ref.version) not in selected:
        raise ValueError('CONTEXT_PROVIDER_REQUIRED: scene version must be approved on this branch')
    if scene['body'].get('story_time') not in (None, str(scope.story_order)):
        raise ValueError('Scene card story time does not match the work package')
    if scene['body'].get('unknowns'):
        raise ValueError('OPEN_DESIGN_QUESTIONS: ' + '；'.join(scene['body']['unknowns']))
    if scene['body']['pov'] in ('AUTHOR', 'WORLD', 'READER'):
        raise ValueError('Scene POV requires a character ID')


def _settings(store: Store, scene: dict, ref: CardRef, visible: list[dict]) -> list[dict]:
    body = scene['body']
    people = {body['pov'], *body.get('characters', [])}
    cards = {(c['card_id'], c['version']): c for c in visible}
    pending = [ref]
    mandatory = set()
    while pending:
        for link in read_links(store, pending.pop()):
            target = (link.target.card_id, link.target.version)
            if link.relation != 'depends_on' or target in mandatory:
                continue
            if target not in cards:
                raise ValueError('MISSING_MANDATORY_INPUT: a required card is unavailable to this POV or branch')
            mandatory.add(target)
            pending.append(link.target)
    if people - {c['card_id'] for c in visible if c['kind'] == 'character'}:
        raise ValueError('MISSING_MANDATORY_INPUT: a scene character ID is unavailable')
    result = [c for key, c in sorted(cards.items())
              if key in mandatory or c['kind'] in ('world', 'style', 'taboo') or c['card_id'] in people]
    if any(card['body'].get('unknowns') and
           (card['kind'] in ('world', 'taboo') or (card['card_id'], card['version']) in mandatory) for card in result):
        raise ValueError('OPEN_DESIGN_QUESTIONS: a mandatory story card has unresolved fields')
    return result


def _previous_refs(store: Store, snapshot: dict, facts: list[Fact],
                   disclosure: tuple[int, int, int]) -> tuple[tuple[Ref, ...], tuple[Ref, ...]]:
    """Pin adjacent prose and all fact evidence, including earlier events disclosed later."""
    earlier = []
    evidence_ids = {item['draft_id'] for fact in facts for item in fact.evidence if 'draft_id' in item}
    for scene_id, slot in snapshot['slots'].items():
        scene = store.get('scene', scene_id)
        order = (store.get('chapter', scene.chapter_id).index, scene.index)
        if order < disclosure[:2]:
            earlier.append((order, slot['draft_id']))
    previous_ids = {ident for _, ident in earlier if ident in evidence_ids}
    if earlier:
        previous_ids.add(max(earlier)[1])
    predecessors = tuple(draft_ref(store.get('draft', ident)) for ident in sorted(previous_ids))
    other_evidence = tuple(draft_ref(store.get('draft', ident)) for ident in sorted(evidence_ids - previous_ids))
    return predecessors, other_evidence


def build_story_context(store: Store, scene_id: str, scope: StoryScope, char_limit: int, *,
                        candidate_refs: tuple[tuple[str, str], ...] = (), base_prompt: str = WRITE_PROMPT,
                        validate_capacity: Callable[[str, dict, set[str]], object] | None = None) -> StoryWork:
    """Freeze the same versioned information the model receives, with source receipts."""
    if type(char_limit) is not int or char_limit < 1:
        raise ValueError('Context character limit must be a positive integer')
    scene = store.get('scene', scene_id)
    chapter = store.get('chapter', scene.chapter_id)
    disclosure = position((chapter.index, scene.index, 0))
    scene_data = json.loads(scene.card_json)
    binding = scene_data.get('story')
    if binding is not None and binding != {'scene_ref': scope.scene_ref, 'story_order': scope.story_order}:
        raise ValueError('Story scope does not match the materialized scene')
    scene_ref = _ref(scope.scene_ref)
    card = read_card(store, scene_ref)
    head = StateHead(scope.branch_id, scope.revision)
    snapshot = (candidate_snapshot(store, head, candidate_refs, scene_id, include_later=True) if candidate_refs
                else revision_state(store, head))
    if scene.id in snapshot.get('stale_plan_scenes', []):
        raise ValueError('STALE_PLAN: this scene was retired by a revised plan on this branch')
    _check_scene(card, scene_ref, scope, snapshot)
    view = state_at(store, scope.branch_id, scope.revision, scope.story_order, card['body']['pov'],
                    disclosure, before_scene=scene_id, snapshot=snapshot)
    visible_ids = {c['card_id'] for c in view.settings}
    cast_guards = [row for row in view.settings if 'casting' in row['body']]
    for ref in snapshot['settings']:
        if ref['card_id'] in visible_ids:
            continue
        hidden_card = read_card(store, CardRef(ref['card_id'], ref['version']))
        if hidden_card['kind'] == 'taboo':
            raise ValueError('MISSING_MANDATORY_INPUT: an approved taboo is unavailable to this POV')
        if card['body'].get('narrative_person') and hidden_card['body'].get('casting', {}).get('entry') == 'withheld':
            cast_guards.append(hidden_card)
    settings = _settings(store, card, scene_ref, view.settings)
    briefs = store.briefs()
    brief = briefs[-1] if briefs else None
    facts = [{key: value for key, value in asdict(f).items() if key != 'evidence'} for f in view.facts]
    visible_brief = asdict(brief) if brief else None
    if visible_brief and 'length_policy' in card['body']:
        from nw.length_settings import effective_brief_text
        visible_brief['text'] = effective_brief_text(visible_brief['text'], card['body']['length_policy'])
    if visible_brief and card['body'].get('narrative_person'):
        from nw.materials.cast_design import writer_brief
        visible_brief = writer_brief(visible_brief, cast_guards)
    inputs = {'brief': visible_brief, 'settings': settings, 'holder': view.holder, 'facts': facts}
    if 'chapter_word_budget' in card['body'] and 'word_budget' in card['body']:
        from nw.length_plan import approved_length_budgets, chapter_progress
        progress = chapter_progress(store, scene_id, snapshot, approved_length_budgets(store, snapshot))
        if progress and 'feasible_min_words' in progress:
            if progress['feasible_min_words'] > progress['feasible_max_words']:
                raise ValueError('WORD_BUDGET: 其余场的已接受和待写篇幅使本场无法同时满足批准的章、场区间，'
                                 '请修订已接受的相关场，或调整章场篇幅方案')
            inputs['chapter_length_progress'] = progress
    design = scene_materials(store, scene_id, scope.scene_ref)
    source_keys = set()
    narration_evidence = []
    if design:
        verify_materials(store.directory.parent, design['materials'])
        checks = scene_checks(design)
        if any(check['profile'] == 'editor' for check in checks) and comparison_draft(store, scene_id, snapshot) is None:
            raise ValueError('MATERIAL_PRECONDITION: cross-chapter review requires a prior chapter draft')
        legacy_preconditions=any(check['profile'] in ('static_binding', 'dynamic_binding', 'static_relation', 'dynamic_relation',
                                   'anchor', 'character_editor') or check['profile']!='method_work' and check['binding'].get('state') for check in checks)
        native_preconditions=any(check['profile']=='method_work' and check['binding'].get('state') for check in checks)
        from nw.materials.chapter_progress import verify_current, writing_preconditions
        progress_preconditions = writing_preconditions(checks, design.get('work_session', {}), design['material_key'])
        narration_states = {c['narration_state_sha256'] for c in checks if 'narration_state_sha256' in c}
        narration_states.update(sha for check in checks for sha in check.get('narration_state_refs', ()))
        narration_states.update(c['situated_known_sha256'] for c in checks if c.get('situated_known_sha256'))
        if legacy_preconditions or native_preconditions or progress_preconditions or narration_states:
            author = state_at(store, scope.branch_id, scope.revision, scope.story_order, 'AUTHOR',
                              disclosure, before_scene=scene_id, snapshot=snapshot)
            if narration_states:
                from nw.materials.narration import verify_scene_facts
                narration_evidence = verify_scene_facts(narration_states, author.facts)
            if progress_preconditions:
                operations = None
                if any((check.get('chapter_progress_prior') or {}).get('removal_source')
                       for check in progress_preconditions):
                    from nw.story_state import selected_operations
                    operations = selected_operations(store, snapshot)
                verify_current(progress_preconditions, author.facts, snapshot['slots'], disclosure,
                               operations=operations, story_order=scope.story_order)
            if legacy_preconditions:
                legacy_design={key:value for key,value in design.items() if key!='work_session'}
                verify_preconditions(legacy_design, author.facts, {item['card_id'] for item in snapshot['settings']})
            if native_preconditions:
                from nw.materials.phase_projection import verify_current_state
                verify_current_state(design['work_session'],design['material_key'],design.get('process_ids',{}),author.facts)
        inputs['ai_world_checks'] = {c['id'] for c in checks if c.get('selection_origin') == 'ai_world'}
        inputs['material_checks'] = writer_checks(design)
        ids = {row['id'] for row in inputs['material_checks']}
        source_keys.update(check_source_keys(check for check in checks if check['id'] in ids))
        source_keys.update(row['source']['key'] for row in design['materials'] if row['source']['id'] in ids)
        source_keys.update(check_source_keys(scene_checks(design, scoped=True)) & _WRITING_SCOPE_KEYS)
    from nw.context.registry import get_provider

    if inputs.get('chapter_length_progress', {}).get('length_mode') == 'tiered':
        from nw.chapter_break import WRITING
        base_prompt += ' ' + WRITING
    if design:
        from nw.studio.craft_materials import design_genre_ids, writing_genre_guidance
        if genre_note := writing_genre_guidance(design_genre_ids(design)):
            base_prompt += ' ' + genre_note
        session_stages = (design.get('work_session') or {}).get('stages') or ()
        if session_stages:
            from nw.materials.step_guard import build_continuity_ledger, format_writing_continuity_prompt
            products_map = {row['stage']: row for row in session_stages if isinstance(row, dict) and row.get('stage')}
            ledger = build_continuity_ledger('writing', products_map, [], {
                'approved_cards': list(view.settings),
                'current_scene': design.get('material_key') or '',
                'accepted_state': [asdict(f) for f in view.facts],
            })
            if guard_note := format_writing_continuity_prompt(ledger):
                base_prompt += ' ' + guard_note
            base_prompt += ' 叙事生命力原则：以人物在当场压力下的真实选择、对手阻力与可见感官动作推动叙事，杜绝机械汇报设定或套话抒情。'
    prompt = step_material_prompt(base_prompt, WRITING_MATERIAL, source_keys)
    provider = get_provider('story')
    assembled = asdict(provider.build(inputs, card))
    def fits(candidate: dict, *, mandatory: bool = False) -> bool:
        try:
            if validate_capacity is not None:
                validate_capacity(prompt, candidate, source_keys)
            if len(prompt) + len(canonical(candidate)) > char_limit:
                raise BudgetExceeded('CONTEXT_TOO_LARGE: mandatory story inputs exceed the budget')
            return True
        except BudgetExceeded:
            if mandatory:
                raise
            return False

    fits(assembled, mandatory=True)
    dependency_facts = [*view.facts, *narration_evidence]
    predecessors, other_evidence = _previous_refs(store, snapshot, dependency_facts, disclosure)
    earlier = {ref.id for ref in predecessors}
    prior_slots_by_draft = {slot['draft_id']: slot for slot in snapshot['slots'].values()}
    prior_texts: dict[str, tuple[str, list[tuple[int, int]]]] = {}

    def excerpt_source(ident: str) -> tuple[str, list[tuple[int, int]]]:
        if ident not in prior_texts:
            prior_texts[ident] = prior_prose(store, store.get('draft', ident), prior_slots_by_draft[ident], view.holder,
                                             at_story_order=scope.story_order)
        return prior_texts[ident]

    def _enrich_span(span: dict) -> dict:
        did = span.get('draft_id')
        start, end = span.get('start'), span.get('end')
        if isinstance(did, str) and did in earlier and type(start) is int and type(end) is int and 0 <= start < end:
            text, hidden = excerpt_source(did)
            snippet = text[start:end]
            if snippet and len(snippet) <= 240 and not any(start < b and a < end for a, b in hidden):
                return {**span, 'quote': snippet}
        return span

    continuity = [{'entity_id': fact.entity_id, 'predicate': fact.predicate,
                   'spans': [_enrich_span(item) for item in fact.evidence if item.get('draft_id') in earlier]}
                  for fact in view.facts if any(item.get('draft_id') in earlier for item in fact.evidence)]
    adjacent_previous = None
    prior_slots = []
    for cand_scene_id, slot in snapshot['slots'].items():
        cand_scene = store.get('scene', cand_scene_id)
        cand_order = (store.get('chapter', cand_scene.chapter_id).index, cand_scene.index)
        if cand_order < disclosure[:2]:
            prior_slots.append((cand_order, cand_scene_id, slot['draft_id']))
    if prior_slots:
        _, prev_scene_id, prev_draft_id = max(prior_slots, key=lambda row: row[0])
        prev_text, hidden = excerpt_source(prev_draft_id)
        safe_tail = prev_text[max((b for _, b in hidden), default=0):][-1200:]
        if safe_tail.strip():
            adjacent_previous = {'scene_id': prev_scene_id, 'draft_id': prev_draft_id, 'tail_text': safe_tail}
    shared = []
    if disclosure > position(baseline_for(store, scope.branch_id)['disclosure_order']):
        reader = state_at(store, scope.branch_id, scope.revision, scope.story_order, 'READER', disclosure,
                          before_scene=scene_id, snapshot=snapshot)
        known = {(fact.entity_id, fact.predicate, canonical(fact.value)) for fact in view.facts if fact.claim == 'fact'}
        shared = [fact for fact in reader.facts if fact.claim == 'fact' and fact.disclosure_order < disclosure
                  and (fact.entity_id, fact.predicate, canonical(fact.value)) in known]
    already_disclosed = [{'entity_id': fact.entity_id, 'predicate': fact.predicate, 'value': fact.value}
                         for fact in shared]
    optional_parts = [('continuity', continuity), ('reader', already_disclosed)]
    if adjacent_previous is not None:
        optional_parts.insert(0, ('previous', adjacent_previous))
    omitted = []
    for name, optional in optional_parts:
        trial = asdict(provider.build({**inputs, name: optional}, card))
        if fits(trial):
            inputs[name] = optional
            assembled = trial
        elif optional:
            omitted.append(name)
    if inputs.get('reader'):
        predecessors, other_evidence = _previous_refs(store, snapshot, [*dependency_facts, *shared], disclosure)
    selection = select_rules(store, scene_ref, view)
    selected = []
    for mapping in selection.mappings:
        trial = asdict(provider.build({**inputs, 'mappings': [*selected, mapping]}, card))
        if not fits(trial):
            selection.excluded_reasons.append({'ref': mapping['ref'], 'reason': 'OPTIONAL_CONTEXT_BUDGET'})
        else:
            selected.append(mapping)
            assembled = trial
    selection.mappings = selected
    selection.selected_refs = [_ref(m['ref']) for m in selected]
    cards = [card, *settings, *(read_card(store, _ref(m['ref'])) for m in selected)]
    receipts = {}
    for item in cards:
        for raw in item['source_refs']:
            source = SourceRef(**raw)
            read_span(store, source)
            receipts[source] = raw
    # Keep audit data outside the model-visible package so omissions cannot leak context.
    refs = tuple(dict.fromkeys(card_input_ref(item) for item in cards))
    check_inputs_current(store, list(refs))
    if cast_guards:
        from nw.materials.cast_design import guard_writer_package
        guard_writer_package(cast_guards, facts, inputs.get('material_checks', []), assembled)
    return StoryWork(scope, disclosure, assembled,
                     legacy_ref('brief', store.project().id, brief) if brief else None,
                     tuple({'card_id': ref.id, 'version': ref.version} for ref in refs),
                     tuple(receipts.values()), predecessors, (*refs, *other_evidence), asdict(selection),
                     content_sha256(design) if design else None, prompt, tuple(sorted(source_keys)), tuple(omitted))
