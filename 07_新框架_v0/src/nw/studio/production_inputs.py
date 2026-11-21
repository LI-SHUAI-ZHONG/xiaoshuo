"""Validate and freeze the author's wizard choices without inventing recommendations."""
from typing import Any

from nw.length_settings import length_fields, parse_length_changes, BRIEF_LENGTH
from nw.materials.phase_routes import ORDER
from nw.studio import catalog
from nw.task_models import canonical

SLOTS = {'genre': 'genre_ids', 'tone': 'tone_ids', 'style': 'style_ids', 'narration': 'narration_ids',
         'world': 'world_ids', 'character': 'character_ids', 'structure': 'structure_ids', 'hook': 'mechanism_ids'}
STAGES = catalog.SLOT_STAGES


def freeze_wizard(body: dict, library: Any) -> dict:
    raw = body.get('wizard', body)
    if not isinstance(raw, dict):
        raise ValueError('立项信息必须是对象')
    title, idea = str(raw.get('title', '')).strip(), str(raw.get('idea', '')).strip()
    if not title or len(title) > 120 or not idea or len(idea) > 12000:
        raise ValueError('请填写书名（120字内）和一句话故事构想（12000字内）')
    wizard = {'title': title, 'idea': idea, 'constraints': str(raw.get('constraints', '')).strip()[:12000]}
    for field in SLOTS.values():
        values = raw.get(field, [])
        if not isinstance(values, list) or len(values) > 30 or any(not isinstance(x, str) or len(x) > 200 for x in values):
            raise ValueError(f'无效的向导选项: {field}')
        wizard[field] = list(dict.fromkeys(values))
    genres = catalog.genres()
    known = {item['id'] for main in genres for item in [main, *main.get('children', [])]}
    if not wizard['genre_ids'] or set(wizard['genre_ids']) - known or len(wizard['genre_ids']) > 4:
        raise ValueError('请选择有效的主类型、子类型与最多两个副类型')
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
        references = freeze_preferences(MethodReader(library.workspace), method_choices, selected_types)
        wizard['method_references'] = references
    if raw.get('production_methods') is not None or references:
        from nw.production_methods.policy import normalize
        configuration = raw.get('production_methods', {})
        if isinstance(configuration, dict):
            configuration = {**configuration, 'preferred_methods': {row['id']: row['version'] for row in references}}
        if configuration is None:
            raise ValueError('如需关闭制作方法，请先取消所选立项方法')
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
    return wizard


def freeze_length_recommendation(wizard: dict, library) -> None:
    wizard.pop('length_recommendation', None)
    result = library.recommend_length(wizard.get('genre_ids', []))
    if result['recommended_tier'] is not None:
        wizard['length_recommendation'] = {key: result[key] for key in (
            'types', 'recommended_tier', 'counts', 'sample_count', 'eligible_count', 'outside_count')}



def governance(wizard: dict, *, library=None) -> dict:
    result = {stage: {'author_preferences': {}} for stage in ORDER}
    for slot, field in SLOTS.items():
        for stage in STAGES[slot]:
            if wizard.get(field):
                result[stage]['author_preferences'][slot] = wizard[field]
    config = {field: wizard.get(field,[]) for field in (
        'genre_ids', 'tone_ids', 'style_ids', 'structure_ids', 'mechanism_ids')}
    if any(config.values()):
        result['type_selection']['project_config'] = config
    filtered = {stage: {key: value for key, value in content.items() if value}
                for stage, content in result.items() if any(content.values())}
    if library is None:
        cast = wizard.get('cast_sample_reference')
    else:
        from nw.studio.cast_samples import design_reference, genre_cast_samples
        cast = design_reference(genre_cast_samples(library, wizard.get('genre_ids', [])))
    if cast:
        filtered.setdefault('world_design', {})['cast_sample_reference'] = cast
    length = length_fields(wizard)
    if wizard.get('auto_length') or wizard.get('length_mode') == 'tiered':
        filtered.setdefault('plot_design', {})['length_auto'] = True
    if wizard.get('length_recommendation') and not wizard.get('target_words') and wizard.get('length_mode') == 'tiered':
        filtered.setdefault('plot_design', {})['length_recommendation'] = wizard['length_recommendation']
    if length or wizard.get('length_policy_updated') or wizard.get('auto_length'):
        filtered.setdefault('plot_design', {})['length_policy'] = length
    return filtered


def brief_text(wizard: dict) -> str:
    choices = '\n'.join(f'{slot}: {"、".join(wizard[field]) or "由设计步骤提出方案"}' for slot, field in SLOTS.items())
    return (f"{wizard['idea']}\n\n作者偏好（不代替设计步骤与冻结产物）：\n{choices}"
            + BRIEF_LENGTH + canonical(length_fields(wizard)))
