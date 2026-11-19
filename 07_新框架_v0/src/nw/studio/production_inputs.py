"""Validate and freeze the author's wizard choices without inventing recommendations."""
from typing import Any

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
    genres = library.genres()['genres']
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
            ranked = library.recommend(copy['slot'], wizard['genre_ids'])['recommendations']
            matched = next(((i, rec) for i, rec in enumerate(ranked, 1) if rec and rec['option_key'] == copy['option_key']), None)
            if not matched:
                raise ValueError('推荐数据已变化，请重新选择或作为普通偏好提交')
            copy.update(rec_rank=matched[0], rec_level=matched[1].get('level', matched[1].get('rec_level')),
                        recommendation_snapshot=matched[1])
        wizard['choices'].append(copy)
    recorded = {(row['slot'], row['option_key']) for row in wizard['choices']}
    for slot, keys in chosen_keys.items():
        wizard['choices'].extend({'slot': slot, 'option_key': key, 'recommended': False}
                                 for key in sorted(keys) if (slot, key) not in recorded)
    wizard['author_references'] = library.freeze_references(wizard['choices'], wizard['genre_ids'])
    wizard['upgrade_snapshot'] = library.approved_upgrades(wizard['genre_ids'])
    for field in ('target_words', 'chapter_count', 'volume_count'):
        if raw.get(field) not in (None, ''):
            value = int(raw[field])
            if not 1 <= value <= 10000000:
                raise ValueError(f'无效的篇幅: {field}')
            wizard[field] = value
    return wizard


def governance(wizard: dict) -> dict:
    result = {stage: {'author_preferences': {}} for stage in ORDER}
    for slot, field in SLOTS.items():
        for stage in STAGES[slot]:
            if wizard[field]:
                result[stage]['author_preferences'][slot] = wizard[field]
    config = {field: wizard[field] for field in (
        'genre_ids', 'tone_ids', 'style_ids', 'structure_ids', 'mechanism_ids')}
    if any(config.values()):
        result['type_selection']['project_config'] = config
    for name, rows in (('author_references', wizard['author_references']),
                       ('upgrade_references', wizard['upgrade_snapshot'].get('items', []))):
        for row in rows:
            for stage in row.get('stages', row.get('stage', [])):
                if stage in result:
                    result[stage].setdefault(name, []).append(row)
    return {stage: {key: value for key, value in content.items() if value}
            for stage, content in result.items() if any(content.values())}


def brief_text(wizard: dict) -> str:
    choices = '\n'.join(f'{slot}: {"、".join(wizard[field]) or "由设计步骤提出方案"}' for slot, field in SLOTS.items())
    return f"{wizard['idea']}\n\n作者偏好（不代替设计步骤与冻结产物）：\n{choices}\n\n立项参数：\n" + canonical({
        key: wizard[key] for key in ('target_words', 'chapter_count', 'volume_count') if key in wizard})
