"""Exact, focus-corroborated overlays; original type records remain immutable."""
from collections import defaultdict
from collections.abc import Callable


_RELATION = ('source_kind', 'target_id', 'target_kind', 'connection_type', 'direction', 'relation_scope')
_FOCUS = {'concept': ('concept_ids', 'concept_focus_ids'),
          'entity_type': ('entity_type_ids', 'entity_focus_types'),
          'event_type': ('event_type_ids', 'event_focus_types'),
          'information_type': ('information_type_ids', 'information_focus_types'),
          'resource_type': ('resource_type_ids', 'resource_focus_types'),
          'foreshadowing_type': ('foreshadowing_type_ids', 'foreshadowing_focus_types'),
          'scene_type': ('scene_type_ids', 'scene_focus_types')}
_PREFIX = {'genre': 'GENRE_', 'subgenre': 'SUBGENRE_', 'hybrid_genre': 'HYBRID_'}


class StaticTypeRepairs:
    """Repair only uniquely matched active original edges with explicit focus evidence."""

    def __init__(self, records: dict, scopes: dict, reference: Callable[[dict], dict]) -> None:
        self.records, self.scopes, self.reference = records, scopes, reference
        self.index: dict[tuple, list[str]] = defaultdict(list)
        for ident, (row, value) in records.items():
            if row['fragment_key'] == '类型静态连接总表.json' and 'connection_id' in value:
                self.index[value.get('source_id'), *(value.get(k) for k in _RELATION)].append(ident)

    def apply(self, original: dict) -> tuple[dict, list[dict]]:
        effective = dict(original)
        selected = {original.get('primary_type_id')}
        for key in ('type_ids', 'component_type_ids', 'subtype_ids', 'hybrid_ids'):
            selected.update(original.get(key, []))
        repairs: list[dict] = []
        refs = list(original.get('static_connection_ids', []))
        for position, logical_id in enumerate(refs):
            old = self.scopes.get(('类型静态连接总表.json', logical_id), [])
            if len(old) != 1:
                continue
            old_row, value = self.records[old[0]]
            if value.get('source_id') in selected:
                continue
            prefix = _PREFIX.get(value.get('source_kind'))
            sources = [x for x in selected if isinstance(x, str) and prefix and x.startswith(prefix)]
            focus_fields = {k: original[k] for k in _FOCUS.get(value.get('target_kind'), ())
                            if value.get('target_id') in original.get(k, [])}
            if len(sources) != 1 or not focus_fields:
                continue
            comparison = tuple(value.get(k) for k in _RELATION)
            candidates = self.index.get((sources[0], *comparison), [])
            if len(candidates) != 1:
                continue
            replacement_row, replacement = self.records[candidates[0]]
            if replacement.get('status') != 'active':
                continue
            refs[position] = replacement['connection_id']
            repairs.append(dict(
                field='static_connection_ids', position=position,
                original_reference=dict(original_id=logical_id, **self.reference(old_row)),
                replacement_ref=dict(original_id=replacement['connection_id'], **self.reference(replacement_row)),
                exact_comparison_fields={k: value.get(k) for k in _RELATION},
                selected_source_id=sources[0], focus_evidence=focus_fields,
                replacement_conditions=replacement.get('conditions', []),
                replacement_limits={k: replacement[k] for k in ('limitations', 'not_guaranteed') if k in replacement},
                interpretation='按原文组合类型及明确焦点重绑到唯一active原始边；不是改写原始记录',
                original_unchanged=True))
        if repairs:
            effective['static_connection_ids'] = refs
        return effective, repairs
