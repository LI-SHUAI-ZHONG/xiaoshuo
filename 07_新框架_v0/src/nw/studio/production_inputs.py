"""Validate and freeze the author's wizard choices without inventing recommendations."""
from typing import Any

from nw.length_settings import length_fields, parse_length_changes, BRIEF_LENGTH
from nw.materials.phase_routes import ORDER
from nw.studio import catalog
from nw.studio import creation_plan
from nw.task_models import canonical

SLOTS = {'genre': 'genre_ids', 'tone': 'tone_ids', 'style': 'style_ids', 'narration': 'narration_ids',
         'world': 'world_ids', 'character': 'character_ids', 'structure': 'structure_ids', 'hook': 'mechanism_ids'}
STAGES = catalog.SLOT_STAGES


def freeze_wizard(body: dict, library: Any) -> dict:
    raw = body.get('wizard', body)
    if not isinstance(raw, dict):
        raise ValueError('立项信息必须是对象')
    mode = raw.get('design_mode')
    auto_recommendations = raw.get('auto_recommendations', False)
    if type(auto_recommendations) is not bool or auto_recommendations and mode != 'auto':
        raise ValueError('只有 AI 自动入口可以启用自动推荐')
    method_policy_mode = raw.get('method_policy_mode')
    if method_policy_mode is not None and method_policy_mode not in ('builtin_enhanced', 'strict_corpus'):
        raise ValueError('制作方法运行策略须为 builtin_enhanced 或 strict_corpus')
    # Creative workflow uses builtin_enhanced by default unless strict_corpus is explicitly requested.
    creative_default = bool(raw.get('creative_workflow'))
    effective_method_mode = method_policy_mode or (
        'strict_corpus' if (auto_recommendations and not creative_default)
        else ('builtin_enhanced' if creative_default else 'legacy')
    )
    auto_builtin_mode = (mode == 'auto' and effective_method_mode == 'builtin_enhanced')
    title, idea = str(raw.get('title', '')).strip(), str(raw.get('idea', '')).strip()
    if len(title) > 120 or len(idea) > 12000 or (not auto_recommendations and not auto_builtin_mode) and (not title or not idea):
        raise ValueError('请填写书名（120字内）和一句话故事构想（12000字内）')
    constraints = str(raw.get('constraints', '')).strip()
    if len(constraints) > 12000:
        raise ValueError('作者硬约束最多 12000 字，请先缩短内容')
    wizard = {'title': title, 'idea': idea, 'constraints': constraints}
    if method_policy_mode is not None or creative_default:
        wizard['method_policy_mode'] = effective_method_mode
    for key, label in (('direction_review', '全书方向确认'), ('planning_hierarchy', '分级设计'),
                       ('creative_workflow', '实际创作工作流')):
        if key in raw:
            if type(raw[key]) is not bool:
                raise ValueError(f'{label}设置必须为布尔值')
            wizard[key] = raw[key]
    if 'design_mode' in raw:
        if mode not in ('manual', 'auto'):
            raise ValueError('请选择人工选择或 AI 自动')
        wizard['design_mode'] = mode
    for field in SLOTS.values():
        values = raw.get(field, [])
        if not isinstance(values, list) or len(values) > 30 or any(not isinstance(x, str) or len(x) > 200 for x in values):
            raise ValueError(f'无效的向导选项: {field}')
        wizard[field] = list(dict.fromkeys(values))
    limits = catalog.wizard_selection_limits()
    genres = catalog.genres()
    known = {item['id'] for main in genres for item in [main, *main.get('children', [])]}
    if not wizard['genre_ids'] or set(wizard['genre_ids']) - known:
        raise ValueError('请选择有效的主类型、子类型与最多两个副类型')
    if len(wizard['genre_ids']) > limits['genre']:
        raise ValueError(f"类型最多选 {limits['genre']} 项，请先取消部分选项。")
    main_ids = {main['id'] for main in genres}
    selected_types = wizard['genre_ids']
    if selected_types[0] not in main_ids:
        raise ValueError('首项必须是主类型')
    primary = next(main for main in genres if main['id'] == selected_types[0])
    children = {row['id'] for row in primary.get('children', [])}
    secondary_at = 1
    if len(selected_types) > 1 and selected_types[1] not in main_ids:
        if selected_types[1] not in children:
            raise ValueError('子类型必须属于所选主类型')
        secondary_at = 2
    if len(selected_types[secondary_at:]) > 2:
        raise ValueError('副类型最多选择两个')
    candidate_titles: dict[str, str] = {}
    if auto_recommendations and effective_method_mode == 'strict_corpus':
        if any(wizard[field] for slot, field in SLOTS.items() if slot != 'genre') or raw.get('method_preferences'):
            raise ValueError('按类型自动推荐的入口使用已批准的方法，请在人工选择入口提交手动偏好')
        wizard['auto_recommendations'] = True
        wizard['title'] = title or f"未命名·{primary['name']}"
        if not idea:
            wizard['idea'] = ('根据所选类型及当前步骤获准的参考小说制作方法，提出原创小说的人物、处境、'
                              '目标、冲突和全书方向。将方法落实为本书具体设计。')
            wizard['idea_origin'] = 'auto_brief'
    elif auto_builtin_mode:
        from nw.studio.wizard_setup import auto_select_genre_preferences

        wizard['auto_recommendations'] = bool(auto_recommendations)
        wizard['title'] = title or f"未命名·{primary['name']}"
        if not idea:
            wizard['idea'] = (f"围绕「{primary['name']}」核心读者承诺与高辨识度冲突，结合内置写作工作流规则"
                              f"与同类型可用参考方法，原创构思主角处境、核心矛盾、代价抉择与全书推进方向。")
            wizard['idea_origin'] = 'auto_brief'
        # Fill differentiating genre defaults when author left slots blank in AI Auto mode.
        defaults = auto_select_genre_preferences(
            selected_types, library=library,
            target_words=raw.get('target_words') if isinstance(raw.get('target_words'), int) else None,
        )
        for field_name in ('structure_ids', 'mechanism_ids', 'tone_ids', 'style_ids'):
            if not wizard.get(field_name) and defaults.get(field_name):
                wizard[field_name] = defaults[field_name]
        if not raw.get('voice_profile') and defaults.get('voice_profile'):
            wizard['_auto_voice_profile'] = defaults['voice_profile']
        if not raw.get('craft_profiles') and defaults.get('craft_profiles'):
            wizard['_auto_craft_profiles'] = defaults['craft_profiles']
    chosen_keys = {'genre': {f'genre.{value}' for value in selected_types}}
    for slot, field in SLOTS.items():
        if slot == 'genre':
            continue
        options = catalog.option_map(slot)
        aliases = {row['id']: key for key, row in options.items() if row.get('selectable', True)}
        canonical_keys = []
        for value in wizard[field]:
            key = value if value in options else aliases.get(value)
            if key is None or not options[key].get('selectable', True):
                raise ValueError(f'选项不存在或不可选择: {slot}/{value}')
            canonical_keys.append(key)
        chosen_keys[slot] = set(canonical_keys)
        wizard[field] = list(dict.fromkeys(options[key]['id'] for key in canonical_keys))
    for slot, limit in limits.items():
        if len(chosen_keys[slot]) > limit:
            raise ValueError(f'{catalog.SLOT_LABELS[slot]}最多选 {limit} 项，请先取消部分选项。')
    choices = raw.get('choices', [])
    if not isinstance(choices, list) or len(choices) > 200:
        raise ValueError('无效的向导选择记录')
    wizard['choices'] = []
    for choice in choices:
        if not isinstance(choice, dict) or choice.get('slot') not in SLOTS or not isinstance(choice.get('option_key'), str):
            raise ValueError('无效的向导选择记录')
        if choice['option_key'] not in chosen_keys[choice['slot']]:
            raise ValueError('选择记录必须与立项偏好一致')
        copy = {key: choice.get(key) for key in ('step', 'slot', 'option_key', 'recommended', 'rec_rank', 'rec_level')}
        copy['recommended'] = bool(copy['recommended'])
        if copy['recommended']:
            raise ValueError('此选项来自历史短文推荐。请刷新立项向导，选择当前制作方法或作为普通偏好提交')
        copy['rec_rank'] = copy['rec_level'] = None
        wizard['choices'].append(copy)
    recorded = {(row['slot'], row['option_key']) for row in wizard['choices']}
    for slot, keys in chosen_keys.items():
        wizard['choices'].extend({'slot': slot, 'option_key': key, 'recommended': False}
                                 for key in sorted(keys) if (slot, key) not in recorded)
    wizard['author_references'] = []
    wizard['upgrade_snapshot'] = {'version': 0, 'items': []}
    method_choices = raw.get('method_preferences', [])
    references = []
    if 'method_preferences' in raw:
        from nw.production_methods.sources import MethodReader
        from nw.studio.method_recommendations import freeze_preferences
        references = freeze_preferences(MethodReader(library.workspace), method_choices, selected_types,
                                        planning_hierarchy=wizard.get('planning_hierarchy', False))
        wizard['method_references'] = references
    if raw.get('production_methods') is not None or references or mode:
        from nw.production_methods.policy import normalize
        from nw.production_methods.sources import MethodReader
        from nw.studio.method_recommendations import freeze_automatic_policy, freeze_optional_policy

        configuration = raw.get('production_methods', {})
        if mode and configuration is None:
            configuration = {}
        if configuration is None:
            raise ValueError('如需关闭制作方法，请先取消所选立项方法')
        if effective_method_mode == 'builtin_enhanced':
            # Builtin-first creative workflow: never deadlocks on missing reference methods!
            # Auto-attaches any available approved same-type corpus methods as optional enhancement.
            reader = MethodReader(library.workspace)
            explicit_tasks = list(configuration.get('tasks', ())) if isinstance(configuration, dict) else []
            if mode == 'auto':
                policy = freeze_optional_policy(
                    reader, selected_types, configuration if isinstance(configuration, dict) else {},
                    candidate_titles=candidate_titles,
                    planning_hierarchy=wizard.get('planning_hierarchy', False),
                    preferred_references=references,
                )
                if policy:
                    wizard['production_methods'] = policy
            elif references or explicit_tasks:
                cfg = {**(configuration if isinstance(configuration, dict) else {})}
                cfg['preferred_methods'] = {row['id']: row['version'] for row in references}
                if not explicit_tasks:
                    # Derive tasks strictly from the author's actually selected methods (no missing-world deadlock)
                    derived_tasks = list(dict.fromkeys(
                        t for row in references for t in _tasks_for_reference(reader, row)
                    ))
                    if derived_tasks:
                        cfg['tasks'] = derived_tasks
                if cfg.get('tasks'):
                    cfg.setdefault('recommendation_mode', 'manual')
                    wizard['production_methods'] = normalize(cfg, types=selected_types)
            elif mode == 'manual' and _has_book_world_method(reader, selected_types, wizard.get('planning_hierarchy', False)):
                # Auto-enhance manual mode with verified same-type world method ONLY when one actually exists.
                wizard['production_methods'] = normalize(
                    {'tasks': ['world_rules'], 'world_selection': 'ai', 'recommendation_mode': 'manual'},
                    types=selected_types,
                )
        else:
            if isinstance(configuration, dict):
                configuration = {**configuration, 'preferred_methods': {row['id']: row['version'] for row in references}}
                if 'recommended_slots' in configuration:
                    raise ValueError('推荐候选版本由类型资料库自动核定')
                if mode:
                    configuration.setdefault('tasks', ['world_rules'])
                    configuration.update(world_selection='ai', recommendation_mode=mode)
            if auto_recommendations and isinstance(configuration, dict):
                wizard['production_methods'] = freeze_automatic_policy(
                    MethodReader(library.workspace), selected_types, configuration, candidate_titles=candidate_titles,
                    planning_hierarchy=wizard.get('planning_hierarchy', False))
            else:
                wizard['production_methods'] = normalize(configuration, types=selected_types)
    if 'auto_length' in raw:
        if type(raw['auto_length']) is not bool:
            raise ValueError('AI 篇幅设计选项必须为布尔值')
        wizard['auto_length'] = raw['auto_length']
    wizard.update(length_fields(parse_length_changes(raw)))
    if wizard.get('length_mode') == 'tiered' and not wizard.get('target_words'):
        freeze_length_recommendation(wizard, library)
    from nw.studio.cast_samples import design_reference, genre_cast_samples
    if cast := design_reference(genre_cast_samples(library, selected_types)):
        wizard['cast_sample_reference'] = cast
    from nw.production_methods.passage_sources import recommendations
    if passages := recommendations(library, selected_types):
        wizard['passage_references'] = passages
    wizard['creation_plan'] = creation_plan.freeze(wizard, library, candidate_titles)
    # Compile 4-Pillar Book Craft Specs (world / cast / plot_pacing / voice) when provided or in creative_workflow.
    raw_craft = raw.get('craft_profiles')
    auto_craft = wizard.pop('_auto_craft_profiles', None)
    raw_voice = raw.get('voice_profile') or wizard.pop('_auto_voice_profile', None)
    if raw_craft is not None and not isinstance(raw_craft, dict):
        raise ValueError('四维基座配置 craft_profiles 必须是对象')
    if raw_voice is not None and not isinstance(raw_voice, dict):
        raise ValueError('语感规范配置必须是对象')
    if raw_craft is not None or raw_voice is not None or wizard.get('creative_workflow'):
        from nw.craft_specs import compile_craft_spec, domain_base_map
        from nw.craft_specs_base import CRAFT_DOMAINS

        merged_profiles: dict[str, dict[str, Any]] = {}
        if isinstance(auto_craft, dict):
            for dom, prof in auto_craft.items():
                if dom in CRAFT_DOMAINS and isinstance(prof, dict):
                    merged_profiles[dom] = dict(prof)
        if isinstance(raw_craft, dict):
            unknown_doms = set(raw_craft) - set(CRAFT_DOMAINS)
            if unknown_doms:
                raise ValueError(f'未知的基座域配置: {", ".join(sorted(unknown_doms))}')
            for dom, prof in raw_craft.items():
                if not isinstance(prof, dict):
                    raise ValueError(f'基座配置 {dom} 必须是对象')
                merged_profiles[dom] = dict(prof)
        if isinstance(raw_voice, dict) and 'voice' not in (raw_craft or {}):
            merged_profiles['voice'] = dict(raw_voice)

        compiled_specs: dict[str, dict[str, Any]] = {}
        for dom in CRAFT_DOMAINS:
            # Compile all 4 domains when creative_workflow or craft_profiles is active;
            # if ONLY legacy voice_profile was passed without creative_workflow, compile voice only.
            if dom != 'voice' and raw_craft is None and not wizard.get('creative_workflow'):
                continue
            prof = merged_profiles.get(dom) or {}
            base_id = prof.get('base_voice_id') if dom == 'voice' and 'base_voice_id' in prof else prof.get('base_id')
            bmap = domain_base_map(dom)
            if base_id is not None and base_id != '' and base_id not in bmap:
                raise ValueError(f'未知的{dom}基座: {base_id}')
            fp_ids = prof.get('fingerprint_ids') or []
            if not isinstance(fp_ids, list) or len(fp_ids) > 5:
                raise ValueError(f'{dom} 指纹最多选择 5 项')
            resolved_fps: list[dict[str, Any]] = []
            if library is not None and fp_ids:
                if hasattr(library, 'craft_fingerprints_by_ids'):
                    resolved_fps = library.craft_fingerprints_by_ids(fp_ids, domain=dom)
                elif dom == 'voice' and hasattr(library, 'voice_fingerprints_by_ids'):
                    resolved_fps = library.voice_fingerprints_by_ids(fp_ids)
            elif auto_builtin_mode and not fp_ids and library is not None:
                try:
                    if hasattr(library, 'craft_fingerprints'):
                        resolved_fps = library.craft_fingerprints(domain=dom, types=selected_types, status='approved')[:2]
                    elif dom == 'voice' and hasattr(library, 'voice_fingerprints'):
                        resolved_fps = library.voice_fingerprints(types=selected_types, status='approved')[:2]
                except Exception:
                    resolved_fps = []
            compiled_specs[dom] = compile_craft_spec(
                dom,
                selected_types,
                base_id=base_id or None,
                knobs=prof.get('knobs') if isinstance(prof.get('knobs'), dict) else None,
                fingerprints=resolved_fps,
                custom_notes=str(prof.get('custom_notes') or ''),
                enabled=bool(prof.get('enabled', True)),
                target_words=wizard.get('target_words') if isinstance(wizard.get('target_words'), int) else None,
                wizard=wizard,
            )
        if compiled_specs:
            wizard['craft_specs'] = compiled_specs
            if 'voice' in compiled_specs:
                wizard['voice_spec'] = compiled_specs['voice']
    return wizard


def _has_book_world_method(reader: Any, types: list[str], planning_hierarchy: bool) -> bool:
    if not types or not reader.db_path.is_file():
        return False
    try:
        from nw.studio.method_recommendations import recommendations
        rec = recommendations(reader, 'world', types, [], planning_hierarchy=planning_hierarchy, limit=1)
        return bool(rec.get('book_world_available'))
    except Exception:
        return False


def _tasks_for_reference(reader: Any, ref: dict) -> list[str]:
    try:
        row = reader.get_method(ref['id'], ref['version'])
        return list(row.get('body', {}).get('tasks', ()))
    except Exception:
        return []


def freeze_length_recommendation(wizard: dict, library) -> None:
    wizard.pop('length_recommendation', None)
    result = library.recommend_length(wizard.get('genre_ids', []))
    if result['recommended_tier'] is not None:
        wizard['length_recommendation'] = {key: result[key] for key in (
            'types', 'recommended_tier', 'counts', 'sample_count', 'eligible_count', 'outside_count')}



def governance(wizard: dict, *, library=None, store=None, scope: str = 'book') -> dict:
    result = {stage: {'author_preferences': {}} for stage in ORDER}
    for slot, field in SLOTS.items():
        values = wizard.get(field)
        if not values:
            continue
        if slot != 'genre':
            opt_by_id = {row['id']: row for row in catalog.option_map(slot).values() if row.get('selectable', True)}
            by_stage: dict[str, list[str]] = {}
            for ident in values:
                target_stages = opt_by_id.get(ident, {}).get('stages') or STAGES[slot]
                for stage in target_stages:
                    if stage in result:
                        by_stage.setdefault(stage, []).append(ident)
            for stage, stage_vals in by_stage.items():
                result[stage]['author_preferences'][slot] = stage_vals
        else:
            for stage in STAGES[slot]:
                result[stage]['author_preferences'][slot] = values
    plan = wizard.get('creation_plan')
    if plan and plan.get('version') == 1:
        for stage in result:
            if packet := creation_plan.for_stage(plan, stage):
                result[stage]['creation_plan'] = packet
    config = {field: wizard.get(field,[]) for field in (
        'genre_ids', 'tone_ids', 'style_ids', 'structure_ids', 'mechanism_ids')}
    if plan and plan.get('version') == 1:
        for slot in ('tone', 'style', 'structure', 'hook'):
            # Section-based craft preferences belong to their design stage.
            # The type governance registry accepts typed identifiers only.
            config[SLOTS[slot]] = [r['id'] for r in plan['preferences'] if r['slot'] == slot
                                    and 'original_line' in r['source_ref']]
        extra_mechanisms = [
            r['id'] for r in plan['preferences']
            if r['slot'] in ('world', 'character')
            and 'original_line' in r['source_ref']
            and str(r['id']).startswith('PLOT_MECHANISM_')
        ]
        if extra_mechanisms:
            config['mechanism_ids'] = list(dict.fromkeys([*config['mechanism_ids'], *extra_mechanisms]))
    if any(config.values()):
        result['type_selection']['project_config'] = config
        if catalog.single_genre_path(config['genre_ids']):
            result['type_selection']['single_genre_selection'] = list(config['genre_ids'])
    filtered = {stage: {key: value for key, value in content.items() if value}
                for stage, content in result.items() if any(content.values())}
    if library is None:
        cast = wizard.get('cast_sample_reference')
        passages = wizard.get('passage_references')
    else:
        from nw.studio.cast_samples import design_reference, genre_cast_samples
        cast = design_reference(genre_cast_samples(library, wizard.get('genre_ids', [])))
        from nw.production_methods.passage_sources import recommendations
        passages = recommendations(library, wizard.get('genre_ids', []))
    if cast:
        filtered.setdefault('world_design', {})['cast_sample_reference'] = cast
    if passages:
        filtered.setdefault('world_design', {})['passage_references'] = passages
    length = length_fields(wizard)
    if wizard.get('auto_length') or wizard.get('length_mode') == 'tiered':
        filtered.setdefault('plot_design', {})['length_auto'] = True
    if wizard.get('length_recommendation') and not wizard.get('target_words') and wizard.get('length_mode') == 'tiered':
        filtered.setdefault('plot_design', {})['length_recommendation'] = wizard['length_recommendation']
    if length or wizard.get('length_policy_updated') or wizard.get('auto_length'):
        filtered.setdefault('plot_design', {})['length_policy'] = length
    from nw.craft_specs import build_stage_craft_spec_packet, load_all_craft_specs
    craft_specs = load_all_craft_specs(store, wizard=wizard)
    if any(isinstance(v, dict) and v.get('enabled', True) for v in craft_specs.values()):
        for st in ('world_design', 'action_design', 'character_design', 'static_relations',
                   'plot_design', 'event_design', 'scene_design'):
            if packet := build_stage_craft_spec_packet(st, scope, craft_specs):
                filtered.setdefault(st, {})['craft_spec'] = packet
    return filtered


def brief_text(wizard: dict) -> str:
    if wizard.get('creation_plan', {}).get('version') == 1:
        names = '、'.join(row['name'] for row in wizard['creation_plan']['types'])
        return f"{wizard['idea']}\n\n立项所选类型：{names}" + BRIEF_LENGTH + canonical(length_fields(wizard))
    choices = '\n'.join(f'{slot}: {"、".join(wizard[field]) or "由设计步骤提出方案"}' for slot, field in SLOTS.items())
    return (f"{wizard['idea']}\n\n作者偏好（不代替设计步骤与冻结产物）：\n{choices}"
            + BRIEF_LENGTH + canonical(length_fields(wizard)))
