"""Freeze the choices that enter production through either Studio entrance."""
from copy import deepcopy

from nw.studio import catalog
from nw.task_models import content_sha256


def freeze(wizard: dict, library, candidate_titles: dict[str, str]) -> dict:
    from nw.studio.kb import freeze_type_knowledge

    preferences = []
    seen: set[str] = set()
    for choice in wizard['choices']:
        slot, key = choice['slot'], choice['option_key']
        if slot == 'genre' or key in seen:
            continue
        seen.add(key)
        option = catalog.option_map(slot)[key]
        meaning = option.get('definition') or option.get('description') or option.get('source_excerpt')
        if not meaning:
            raise ValueError(f"立项选项「{option['name']}」缺少对应步骤中的释义")
        source = {**option['source_ref'], 'title': option['name'], 'material_sha256': content_sha256(
            catalog.material(option['source_ref']['file']))}
        preferences.append({'slot': slot, 'key': key, 'id': option['id'], 'name': option['name'],
                            'meaning': meaning, 'source_ref': source, 'stages': list(option['stages'])})
        if step_use := option.get('step_use'):
            preferences[-1]['step_use'] = step_use

    policy = wizard.get('production_methods', {})
    recommendations = [
        {'slot': slot, 'scope': route['scope'], 'stage': route['stage'],
         'candidates': [{'id': ident, 'version': version, 'title': candidate_titles.get(ident, ident)}
                        for ident, version in route['versions'].items()]}
        for slot, route in policy.get('recommended_slots', {}).items()]
    return {'version': 1, 'mode': wizard.get('design_mode', 'manual'), 'constraints': wizard['constraints'],
            'types': freeze_type_knowledge(library, wizard['genre_ids']), 'preferences': preferences,
            'references': deepcopy(wizard.get('method_references', [])), 'recommendations': recommendations,
            'preference_interactions': _interactions(seen)}


def _interactions(keys: set[str]) -> list[dict]:
    if {'structure.NARRATIVE_STRUCTURE_SINGLE_POV', 'structure.NARRATIVE_STRUCTURE_MULTI_POV'} <= keys:
        raise ValueError('单视角叙事与多视角叙事同时指定了全书视角结构，请保留其中一项。')
    interactions = (
        (('style.STYLE_LIGHT', 'style.STYLE_GRITTY'),
         '分别决定轻松与粗粝表达用在哪个场景、角色说话时机或叙述节拍，并说明各处为什么适合。'),
        (('tone.TONE_LIGHT', 'tone.TONE_SERIOUS'),
         '分别确定轻快与庄重语气适合的交流对象和情境。可在同场用不同角色或节拍体现。'),
    )
    return [{'keys': list(pair), 'stages': ['expression_design'], 'guidance': guidance}
            for pair, guidance in interactions if keys.issuperset(pair)]


def for_stage(plan: dict, stage: str) -> dict:
    from nw.studio.kb import project_type_knowledge

    result = {}
    if stage in catalog.SLOT_STAGES['genre'] and plan['types']:
        result['types'] = project_type_knowledge(plan['types'])
    if preferences := [row for row in plan['preferences'] if stage in row['stages']]:
        result['preferences'] = preferences
    if interactions := [row for row in plan['preference_interactions'] if stage in row['stages']]:
        result['preference_interactions'] = interactions
    # Approved methods use the existing production-method contracts. Their
    # scopes, applicable inputs and output placement are enforced there.
    return deepcopy(result)
