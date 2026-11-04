
"""Bounded, deterministic recall over versioned method cards."""
from dataclasses import asdict, dataclass
import re
from unicodedata import normalize

from nw.cards import eligible_rule_refs, read_card, read_links
from nw.store import Store
from nw.story_models import CardRef, StateView


@dataclass
class Selection:
    candidates: list[CardRef]
    selected_refs: list[CardRef]
    excluded_reasons: list[dict]
    mappings: list[dict]
    manifest_id: str | None = None


def _keywords(parts: list[str]) -> set[str]:
    words = set()
    for part in parts:
        for word in re.findall(r'[a-z0-9]+|[\u3400-\u9fff]+', normalize('NFKC', part).casefold()):
            if '\u3400' <= word[0] <= '\u9fff':
                words.update(word[i:i + 2] for i in range(len(word) - 1))
            elif len(word) > 1:
                words.add(word)
    return words


def select_rules(store: Store, scene_ref: CardRef, state_view: StateView, limit: int = 5) -> Selection:
    if type(limit) is not int or not 0 <= limit <= 5:
        raise ValueError('Rule selection limit must be between 0 and 5')
    scene = read_card(store, scene_ref)
    if scene['kind'] != 'scene':
        raise ValueError('Rule selection requires a scene card')
    body = scene['body']
    problem = body.get('function') or body['goal']
    cues = [body[key] for key in ('title', 'goal', 'function', 'conflict', 'choice')
            if body.get(key)] + body.get('tags', [])
    keywords = _keywords(cues)
    cue_text = ' '.join(cues).casefold()
    entities = {scene_ref, *(CardRef(row['card_id'], row['version']) for row in state_view.settings)}
    entity_ids = {body['pov'], *body.get('characters', []), *(fact.entity_id for fact in state_view.facts)}
    entities.update(link.target for link in read_links(store, scene_ref) if link.relation == 'depends_on')
    ranked = []
    excluded = []
    for ref in eligible_rule_refs(store):
        card = read_card(store, ref)
        method = card['body']
        if method['visibility'] == 'holders' and state_view.holder not in method['holders']:
            continue
        if method['excludes_when'].casefold() in cue_text:
            excluded.append({'ref': asdict(ref), 'reason': 'EXPLICIT_EXCLUSION_MATCH'})
            continue
        hits = sorted(keywords & _keywords([method['title'], method['applies_when'], *method.get('tags', [])]))
        related = sorted({link.target.card_id for link in read_links(store, ref)
                          if link.relation in ('depends_on', 'interprets', 'corrects')
                          and (link.target in entities or link.target.card_id in entity_ids)})
        tagged = sorted(set(body.get('tags', [])) & set(method.get('tags', [])))
        if not (hits or related or tagged):
            excluded.append({'ref': asdict(ref), 'reason': 'NO_SCENE_MATCH'})
            continue
        mapping = {'ref': asdict(ref), 'problem': problem, 'original_meaning': method['original_meaning'],
                   'action': method['operation'], 'check': method['check'],
                   'applies_when': method['applies_when'], 'excludes_when': method['excludes_when'],
                   'reason': {'keywords': hits, 'tags': tagged, 'related_ids': related}}
        score = (len(related), len(tagged), len(hits))
        ranked.append((score, ref, mapping))
    ranked.sort(key=lambda row: (*(-n for n in row[0]), row[1].card_id, row[1].version))
    for i, (_, ref, _) in enumerate(ranked[limit:], start=limit):
        excluded.append({'ref': asdict(ref), 'reason': 'CANDIDATE_LIMIT' if i >= 20 else 'LOWER_RANK'})
    return Selection([row[1] for row in ranked[:20]], [row[1] for row in ranked[:limit]],
                     excluded, [row[2] for row in ranked[:limit]])


def validate_selected_ids(selection: Selection, ids: list[str]) -> list[CardRef]:
    candidates = {ref.card_id: ref for ref in selection.candidates}
    if (not isinstance(ids, list) or len(ids) > 5 or
            any(not isinstance(ident, str) or ident not in candidates for ident in ids) or
            len(set(ids)) != len(ids)):
        raise ValueError('Selected IDs must be a unique subset of recalled candidates')
    return [candidates[ident] for ident in ids]
