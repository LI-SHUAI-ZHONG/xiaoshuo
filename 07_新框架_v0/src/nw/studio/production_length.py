"""Project length settings and counts for the currently accepted main manuscript."""
import json

from nw.length_settings import (
    CHAPTER_MAX_WORDS, CHAPTER_MIN_WORDS, LEGACY_QUOTAS, LENGTH_FIELDS, book_word_range,
    length_fields, parse_length_changes, validate_length_mode,
)
from nw.store import now
from nw.story_state import current_head, revision_state
from nw.task_models import canonical


def manuscript_length(store, wizard: dict) -> dict:
    from nw.length_plan import approved_book_plan, approved_length_budgets, count_words, manuscript_scene_ids
    managed = store.managed_story()
    state = revision_state(store, current_head(store, 'main')) if managed else {}
    scene_ids = manuscript_scene_ids(store, state) if managed else set()
    budgets = approved_length_budgets(store, state) if managed else {'chapters': {}, 'scenes': {}}
    chapters = {c.id: {'chapter_id': c.id, 'index': c.index, 'title': c.title,
                       'accepted_words': 0, 'scenes': [], 'budget': budgets['chapters'].get(c.id)}
                for c in store.list('chapter')}
    for scene in store.list('scene'):
        if managed and scene.id not in scene_ids:
            continue
        if managed:
            draft_id = state['slots'].get(scene.id, {}).get('draft_id')
        else:
            accepted = store.accepted(scene.id)
            draft_id = accepted.draft_id if accepted else None
        count = count_words(store.get('draft', draft_id).text) if draft_id else 0
        chapter = chapters[scene.chapter_id]
        row = {'scene_id': scene.id, 'index': scene.index, 'accepted_words': count,
               'budget': budgets['scenes'].get(scene.id)}
        if scene.id in budgets.get('tiered_scenes', ()):
            row['length_mode'] = 'tiered'
        chapter['scenes'].append(row)
        chapter['accepted_words'] += count
    visible = sorted((r for r in chapters.values() if r['scenes']), key=lambda r: r['index'])
    for row in visible:
        row['scenes'].sort(key=lambda r: r['index'])
    words = sum(r['accepted_words'] for r in visible)
    tiered = wizard.get('length_mode') == 'tiered'
    book = approved_book_plan(store, state, tiered_only=tiered) if managed else {}
    target = wizard.get('target_words') or book.get('target_words')
    if tiered:
        low, high = book_word_range(target) if target else (None, None)
        delta = None if low is None else words - min(max(words, low), high)
        return {**length_fields(wizard), 'target_words': wizard.get('target_words'), 'effective_target_words': target,
                'minimum_words': low, 'maximum_words': high, 'chapter_min_words': CHAPTER_MIN_WORDS,
                'chapter_max_words': CHAPTER_MAX_WORDS, 'effective_chapter_count': book.get('chapter_count'),
                'remaining_words': max(0, low - words) if low is not None else None, 'delta_words': delta,
                'book_plan': book, 'accepted_words': words, 'chapters': visible}
    tolerance = wizard.get('word_tolerance_pct', 0)
    return {**length_fields(wizard), 'target_words': wizard.get('target_words'), 'word_tolerance_pct': tolerance,
            'effective_target_words': target, 'book_plan': book,
            'effective_chapter_count': wizard.get('chapter_count') or book.get('chapter_count'),
            'accepted_words': words, 'remaining_words': max(0, target - words) if target else None,
            'delta_words': words - target if target else None, 'chapters': visible,
            'minimum_words': (target * (100 - tolerance) + 99) // 100 if target else None}


def verify_finish_length(summary: dict) -> None:
    total = summary['accepted_words']
    minimum = summary['minimum_words']
    if summary.get('length_mode') == 'tiered':
        if minimum is None:
            raise ValueError('全书篇幅档位待确定，请选择档位或先批准 AI 提出的书纲')
        maximum = summary['maximum_words']
        if not minimum <= total <= maximum:
            raise ValueError(f"全书篇幅超出所选档位的完稿范围：已接受 {total} 字，可在 {minimum}–{maximum} 字之间完稿")
        for chapter in summary['chapters']:
            if not CHAPTER_MIN_WORDS <= chapter['accepted_words'] <= CHAPTER_MAX_WORDS:
                raise ValueError(f"第{chapter['index']}章已接受 {chapter['accepted_words']} 字，"
                                 f"请在 {CHAPTER_MIN_WORDS}–{CHAPTER_MAX_WORDS} 字内以完整段落自然收束")
        return
    if minimum is not None and total < minimum:
        raise ValueError(f"全书篇幅未达标：已接受 {total} 字，目标 {summary['effective_target_words']} 字，"
                         f"完稿下限 {minimum} 字，还差 {minimum - total} 字")
    for chapter in summary['chapters']:
        for row in (chapter, *chapter['scenes']):
            budget = row['budget']
            if budget and not budget['min_words'] <= row['accepted_words'] <= budget['max_words']:
                position = f"第{chapter['index']}章"
                if 'scene_id' in row:
                    position += f"第{row['index']}场"
                raise ValueError(f"{position}已接受 {row['accepted_words']} 字，已批准范围 "
                                 f"{budget['min_words']}–{budget['max_words']} 字，请修稿或重做篇幅设计")


def retire_unstarted_book(store, novel: dict, budget) -> None:
    """Keep an untouched pre-API book task as history if its initial settings changed."""
    if not novel.get('job_id') or not novel['wizard'].get('length_policy_updated'):
        return
    with store.connection:
        store.connection.execute('BEGIN IMMEDIATE')
        row = store.connection.execute("""SELECT request_json FROM novel_jobs j WHERE id=? AND status='READY'
            AND NOT EXISTS (SELECT 1 FROM novel_steps s WHERE s.job_id=j.id)""", (novel['job_id'],)).fetchone()
        if not row:
            return
        frozen = json.loads(row[0])
        if frozen['mode'] != 'design' or frozen['design_scope'] != 'book' or frozen.get('parent_id'):
            return
        policy = frozen.get('governance_inputs', {}).get('plot_design', {}).get('length_policy', {})
        fields = ('output_limit','context_char_limit','max_calls','max_revisions')
        if policy == length_fields(novel['wizard']) and all(
                frozen['budget'].get(k) == getattr(budget, k) for k in fields):
            return
        store.connection.execute("""UPDATE novel_jobs SET status='CANCELLED',reason='LENGTH_SETTINGS_UPDATED'
                                    WHERE id=?""", (novel['job_id'],))


def change_length(app, ident: str, body: dict) -> dict:
    if not body or set(body) - (set(LENGTH_FIELDS) | {'budget'}):
        raise ValueError('请提供需要调整的篇幅或制作预算字段')
    changes = parse_length_changes(body)
    with app._lock, app.db.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT wizard_json,status FROM novels WHERE id=?', (ident,)).fetchone()
        if row is None:
            raise FileNotFoundError('未找到这本小说')
        if row['status'] == 'done':
            raise ValueError('已完稿作品的篇幅不能修改')
        wizard = json.loads(row['wizard_json'])
        previous = length_fields(wizard)
        prior_budget = wizard.get('call_budget', {})
        if changes.get('length_mode') == 'tiered' and previous.get('length_mode') != 'tiered':
            for field in (*LEGACY_QUOTAS, 'target_words'):
                wizard.pop(field, None)

        for key, value in changes.items():
            if value is None:
                wizard.pop(key, None)
            else:
                wizard[key] = value
        validate_length_mode(wizard)
        if wizard.get('length_mode') == 'tiered' and ('target_words' in changes or previous.get('length_mode') != 'tiered'):
            if wizard.get('target_words'):
                wizard.pop('length_recommendation', None)
            else:
                from nw.studio.production_inputs import freeze_length_recommendation
                freeze_length_recommendation(wizard, app.library)
        if 'budget' in body:
            raw = body['budget']
            if raw is not None and (not isinstance(raw, dict) or set(raw) - {'context_char_limit','output_limit'}):
                raise ValueError('请提供有效的输入字符或输出 token 预算')
            # Clearing input/output preferences preserves independently configured call and revision limits.
            patch = raw if raw is not None else {'context_char_limit': None, 'output_limit': None}
            saved = {**prior_budget, **patch}
            saved = {k: v for k, v in saved.items() if v is not None}
            app.budget(saved)
            wizard['call_budget'] = saved
        current = length_fields(wizard)
        if previous != current or prior_budget != wizard.get('call_budget', {}):
            wizard['length_policy_updated'] = True
            timestamp = now()
            db.execute('UPDATE novels SET wizard_json=?,updated_at=? WHERE id=?', (canonical(wizard), timestamp, ident))
            db.execute('INSERT INTO timeline_events(novel_id,ts,kind,summary,ref_json) VALUES(?,?,?,?,?)',
                       (ident, timestamp, 'length', '更新后续制作的篇幅与预算', canonical({
                           'before': previous, 'after': current, 'budget': wizard.get('call_budget', {})})))
    return {'length_plan': app.detail(ident)['length_plan']}
