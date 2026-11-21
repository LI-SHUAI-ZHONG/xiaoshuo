"""Project only prior prose the current viewpoint can receive."""
from dataclasses import asdict
import json

from nw.cards import read_card
from nw.materials.narration_review import PREFIX, issue
from nw.models import Draft
from nw.store import Store
from nw.story_delta import draft_ref, read_delta
from nw.story_models import CardRef
from nw.tasks import read_input_manifest


def _reviewed_paragraphs(draft: Draft, beats: dict, review: dict, contract: dict) -> list[tuple[int, int]]:
    """Expand the reviewed evidence to whole paragraphs, leaving other dialogue usable."""
    pin = asdict(draft_ref(draft))
    if contract['draft'] != pin or review.get('recommendation') != 'pass':
        raise ValueError('Prior narration review and draft differ')
    checked = {row['id']: row for row in contract['checks'] if row['id'] in beats}
    judgments = {row['id']: row for row in review['material_checks'] if row['id'] in beats}
    if checked.keys() != beats.keys() or judgments.keys() != beats.keys():
        raise ValueError('Prior narration review is incomplete')
    private = []
    for ident, observable in beats.items():
        check, row = checked[ident], judgments[ident]
        if (check['method_artifact']['narration']['owner'] is not None
                or json.loads(check['binding']['observable']) != observable
                or row['status'] != 'pass' or issue(row) != 'as_designed'):
            raise ValueError('Prior reader-only beat has no verified disclosure')
        if 'passage_step' in check:
            from nw.materials.passage_review import primary_spans
            spans = primary_spans(row, draft.id)
        else:
            spans = [s for s in row['evidence'] if s['id'] == draft.id]
        if not spans:
            raise ValueError('Prior reader-only beat has no draft locations')
        for span in spans:
            start, end = span['start'], span['end']
            if (any(span[k] != v for k, v in pin.items()) or not 0 <= start < end <= len(draft.text)
                    or span['quote'] != draft.text[start:end]):
                raise ValueError('Prior narration quote does not match')
            line_start = draft.text.rfind('\n', 0, start) + 1
            line_end = draft.text.find('\n', end - 1)
            private.append((line_start, len(draft.text) if line_end < 0 else line_end + 1))
    return private


def prior_prose(store: Store, draft: Draft, slot: dict, pov: str) -> tuple[str, list[tuple[int, int]]]:
    """Return the text and unreadable paragraphs; an unverified optional excerpt stays out."""
    hidden = [(0, len(draft.text))]
    try:
        run = store.get('run', draft.run_id)
        items = json.loads(run.context_package_json).get('items', [])
        viewers = [item['source'][4:] for item in items if item['source'].startswith('pov:')]
        if not viewers:
            ref = json.loads(store.get('scene', draft.scene_id).card_json).get('story', {}).get('scene_ref')
            if ref:
                viewers = [read_card(store, CardRef(**ref))['body']['pov']]
        if viewers != [pov]:
            return draft.text, hidden
        beats = {}
        for item in items:
            if item['source'].startswith('material:' + PREFIX):
                check = json.loads(item['text'])
                observable = json.loads(check['observable'])
                if observable['audience'] == 'reader_only':
                    beats[check['id']] = observable
        if not beats:
            return draft.text, []
        delta = read_delta(store, slot['delta_id'])
        _, extraction = read_input_manifest(store, delta.manifest_id)
        review = store.get('run', extraction['material_review_run'])
        message = json.loads(review.input_snapshot_json)['messages'][-1]['content']
        return draft.text, _reviewed_paragraphs(draft, beats, json.loads(review.output_text),
                                                json.loads(message)['material_review'])
    except (AttributeError, IndexError, KeyError, TypeError, ValueError):
        return draft.text, hidden
