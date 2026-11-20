"""Project length decisions use the same frozen branch and approved cards as the prose."""
from __future__ import annotations

import json
from typing import Any

from nw.store import Store
from nw.story_models import StateHead
from nw.length_settings import WORD_FIELDS, saved_brief_length
from nw.story_state import approved_scene_positions

def count_words(text: str) -> int:
    return sum(not char.isspace() for char in text)


def _positive(value: Any) -> bool:
    return type(value) is int and 1 <= value <= 10_000_000


def check_budget(value: Any) -> None:
    if (not isinstance(value, dict) or set(value) - {'reference_words'} != {'min_words', 'target_words', 'max_words', 'reason'}
            or ('reference_words' in value and not _positive(value['reference_words']))
            or not all(_positive(value[key]) for key in ('min_words', 'target_words', 'max_words'))
            or not value['min_words'] <= value['target_words'] <= value['max_words']
            or not isinstance(value['reason'], str) or not value['reason'].strip()):
        raise ValueError('篇幅设计须提供 min_words ≤ target_words ≤ max_words 三个正整数和具体剧情功能 reason')


def check_reference(budget: dict, policy: dict, kind: str) -> None:
    check_budget(budget)
    given = policy.get(kind + '_target_words')
    if budget.get('reference_words') != given:
        raise ValueError(f'{kind} 篇幅的 reference_words 必须与本项目给定的参考字数一致')


def check_book(value: Any) -> None:
    if (not isinstance(value, dict) or set(value) != {'chapter_count', 'target_words', 'reason'}
            or not _positive(value['chapter_count']) or not _positive(value['target_words'])
            or not isinstance(value['reason'], str) or not value['reason'].strip()):
        raise ValueError('全书篇幅方案 length_plan 需要正整数 target_words、chapter_count 和规划理由 reason')


def manuscript_scene_ids(store: Store, state: dict | None, *,
                         approved_positions: dict | None = None) -> set[str]:
    """Current manuscript, including accepted legacy scenes with no planning-card identity."""
    if not state or 'settings' not in state:
        return {s.id for s in store.list('scene')}
    visible = set(approved_positions if approved_positions is not None else approved_scene_positions(store, state))
    legacy = state['slots'].keys() - visible - set(state.get('stale_plan_scenes', ()))
    if legacy:
        for scene in store.list('scene'):
            if scene.id not in legacy:
                continue
            binding = json.loads(scene.card_json).get('story')
            if not isinstance(binding, dict) or not binding.get('scene_ref'):
                visible.add(scene.id)
    return visible


def approved_length_budgets(store: Store, state: dict | None) -> dict:
    """Resolve only the current branch's real scene-card versions, including chapter budgets they inherit."""
    active = {(r['card_id'], r['version']) for r in state['settings']} if state is not None else None
    retired = set((state or {}).get('stale_plan_scenes', ()))
    scenes, chapters = {}, {}
    rows = store.connection.execute("""
        SELECT s.id, s.chapter_id, c.card_id, c.version,
               json_extract(c.body_json, '$.word_budget'), json_extract(c.body_json, '$.chapter_word_budget')
        FROM scenes s JOIN cards c
          ON c.card_id=json_extract(s.card_json,'$.story.scene_ref.card_id')
         AND c.version=json_extract(s.card_json,'$.story.scene_ref.version')
        WHERE json_type(c.body_json,'$.word_budget')='object'""")
    for scene_id, chapter_id, card_id, version, scene_json, chapter_json in rows:
        if scene_id in retired or (active is not None and (card_id, version) not in active):
            continue
        scenes[scene_id] = json.loads(scene_json)
        if chapter_json:
            budget = json.loads(chapter_json)
            if chapters.setdefault(chapter_id, budget) != budget:
                raise ValueError('同一章的已批准场景引用了不同篇幅方案，须先重做章设计')
    return {'chapters': chapters, 'scenes': scenes}


def approved_book_application(store: Store, state: dict) -> tuple[str | None, dict]:
    active = {(r['card_id'], r['version']) for r in state['settings']}
    if not active:
        return None, {}
    rows = store.connection.execute("""SELECT a.proposal_id, c.card_id, c.version,
            json_extract(c.body_json,'$.length_plan') FROM plan_applications a
            JOIN cards c ON c.card_id=json_extract(a.mapping_json,'$.root.card_id')
              AND c.version=json_extract(a.mapping_json,'$.root.version')
            JOIN task_calls t ON t.id=a.proposal_id JOIN input_manifests m ON m.id=t.manifest_id
            WHERE coalesce(json_extract(a.mapping_json,'$.length_scope'), json_extract(m.package_json,'$.scope'))='book'
            ORDER BY a.rowid DESC""")
    for proposal, ident, version, value in rows:
        if (ident, version) in active:
            return proposal, json.loads(value) if value else {}
    return None, {}


def approved_book_plan(store: Store, state: dict) -> dict:
    return approved_book_application(store, state)[1]


def design_context(store: Store, brief: dict, state: dict | None, parent: dict | None,
                   *, automatic: bool = False, parent_chapters: tuple = ()) -> dict | None:
    policy = saved_brief_length(brief['text'])
    if not automatic and not any(policy.get(k) for k in WORD_FIELDS):
        return None
    slots = state['slots'] if state is not None else {s: {'draft_id': d} for s, d in
             store.connection.execute('SELECT scene_id, draft_id FROM accepted')}
    budgets = approved_length_budgets(store, state)
    levels = {}
    chapter_indices = {ch.id: str(ch.index) for ch in store.list('chapter')}
    for chapter_id, index in chapter_indices.items():
        if budget := budgets['chapters'].get(chapter_id):
            levels[index] = {'word_budget': budget, 'allocated_words': 0}
    total = 0
    reserved = 0
    pending_max = {}
    accepted_by_chapter = {}
    active = manuscript_scene_ids(store, state)
    for scene in store.list('scene'):
        if scene.id not in active:
            continue
        slot = slots.get(scene.id)
        if slot:
            words = count_words(store.get('draft', slot['draft_id']).text)
            total += words
            accepted_by_chapter[scene.chapter_id] = accepted_by_chapter.get(scene.chapter_id, 0) + words
        else:
            words = budgets['scenes'].get(scene.id, {}).get('target_words', 0)
            reserved += words
            upper = budgets['scenes'].get(scene.id, {}).get('max_words', 0)
            pending_max[scene.chapter_id] = pending_max.get(scene.chapter_id, 0) + upper
        chapter_index = chapter_indices[scene.chapter_id]
        level = levels.setdefault(chapter_index, {'allocated_words': 0})
        level['allocated_words'] += words
        if not slot:
            level['open_scenes'] = level.get('open_scenes', 0) + 1
    for chapter_id, limit in list(pending_max.items()):
        if budget := budgets['chapters'].get(chapter_id):
            pending_max[chapter_id] = min(limit, max(0, budget['max_words'] - accepted_by_chapter.get(chapter_id, 0)))
    for chapter_id, index in chapter_indices.items():
        if index in levels:
            levels[index]['accepted_words'] = accepted_by_chapter.get(chapter_id, 0)
            levels[index]['pending_max_words'] = pending_max.get(chapter_id, 0)
    inherited = (parent or {}).get('body', {}).get('length_plan', {})
    target = policy.get('target_words') or inherited.get('target_words')
    return {'policy': policy, 'parent_plan': inherited, 'accepted_words': total, 'pending_planned_words': reserved,
            'pending_max_words': sum(pending_max.values()), 'parent_chapters': list(parent_chapters),
            'remaining_words': target - total if target else None, 'existing_chapters': levels}


def model_length_context(context: dict) -> dict:
    """Past accepted totals already contribute to the remaining budget; show only actionable chapter rows."""
    levels = context['existing_chapters']
    ordered = sorted(levels, key=int)
    pending = [i for i in ordered if levels[i].get('open_scenes')]
    completed = [i for i in ordered if not levels[i].get('open_scenes')]
    selected = {str(i) for i in context.get('parent_chapters', ())} | set(pending[:4] + pending[-2:] + completed[-1:])
    visible = {key: levels[key] for key in ordered if key in selected}
    return {**context, 'existing_chapters': visible, 'other_chapter_count': len(levels) - len(visible)}


def model_approved_cards(cards: list[dict]) -> list[dict]:
    # Project length history once through length_context; keep plot details and references as usual.
    fields = {'length_plan', 'word_budget', 'chapter_word_budget', 'length_policy'}
    return [{**card, 'body': {k: v for k, v in card['body'].items() if k not in fields}}
            if isinstance(card.get('body'), dict) and fields.intersection(card['body']) else card
            for card in cards]


def instructions(stage: str) -> str:
    plot = ('篇幅设计：directions 的每个正文方向 body（阶段 directions 数组中直接是 body）均含 '
            'length_plan={target_words,chapter_count,reason}。依据类型、冲突升级、兑现与 length_context 的剩余字数规划；'
            '有明确全书目标和章数须原值沿用，未指定时由你设计。已批准 parent_plan 继续生效，有新明确要求按新要求。'
            '每张将实际生成的卷卡和章卡 body 均含 word_budget={min_words,target_words,max_words,reason}。'
            '若明确给定 chapter_target_words，章预算另填 reference_words 原值；偏离时 reason 解释本章为何从参考值调整到实际目标。')
    scene = ('每张场景卡 body 填 word_budget={min_words,target_words,max_words,reason}，'
             '用非空白字符计数，依前置章目标、冲突、关系变化或兑现分配篇幅；场内 reason 仅用当前视角已知内容。新章各场 target_words 之和等于章卡 target_words，'
             '若明确给定 scene_target_words，场预算另填 reference_words 原值；偏离时 reason 说明本场伸缩的剧情原因。'
             '每场区间相加须覆盖章目标。续写已有章先用 existing_chapters 对应预算及已分配字数；若旧章尚无章预算，'
             '给本批各场 body 填相同的 chapter_word_budget，交代已有篇幅。')
    return {'plot_design': plot, 'scene_design': scene, 'plan': plot + scene}.get(stage, '')


def validate_direction(body: dict, context: dict) -> None:
    book = body.get('length_plan')
    check_book(book)
    for key in ('target_words', 'chapter_count'):
        given = context['policy'].get(key) or context['parent_plan'].get(key)
        if given and book[key] != given:
            raise ValueError('篇幅方案偏离已确定的全书目标或计划章数：' + key)


def chapter_budget(chapter: dict, members: dict, context: dict) -> dict:
    if chapter['card']:
        return members[chapter['card']]['body']['word_budget']
    existing = context['existing_chapters'].get(str(chapter['index']), {})
    return existing.get('word_budget') or members[chapter['scenes'][0]['card']]['body'].get('chapter_word_budget')


def validate_allocations(chapters: list, members: dict, context: dict) -> None:
    for chapter in chapters:
        budget = chapter_budget(chapter, members, context)
        if chapter['card'] or not context['existing_chapters'].get(str(chapter['index']), {}).get('word_budget'):
            check_reference(budget, context['policy'], 'chapter')
        else:
            check_budget(budget)
        planned = 0
        for scene in chapter['scenes']:
            body = members[scene['card']]['body']
            check_reference(body.get('word_budget'), context['policy'], 'scene')
            if 'chapter_word_budget' in body and body['chapter_word_budget'] != budget:
                raise ValueError('场景须承接同一份章篇幅方案')
            planned += body['word_budget']['target_words']
        if chapter['card'] and planned != budget['target_words']:
            raise ValueError('各场目标字数之和须等于新章目标字数')
        prior = context['existing_chapters'].get(str(chapter['index']), {}).get('allocated_words', 0)
        if not chapter['card'] and prior + planned > budget['max_words']:
            raise ValueError('已有章分配超出已批准上限，须调整场景预算或重做章设计')


def validate_candidate(candidate: dict, scope: str, context: dict) -> None:
    validate_direction(candidate['body'], context)
    members = {row['key']: row for row in candidate['members']}
    for row in members.values():
        if row['kind'] in ('chapter', 'volume') and scope != 'book':
            check_budget(row['body'].get('word_budget'))
    validate_allocations(candidate['chapters'], members, context)
    # At the point all planned chapters have coordinates, the book must be reachable
    # somewhere within both the chapter range and the sum of its scene ranges.
    new_chapters = [ch for ch in candidate['chapters'] if ch['card']]
    book = candidate['body']['length_plan']
    count = book['chapter_count']
    known = {int(i) for i in context['existing_chapters']} | {ch['index'] for ch in candidate['chapters']}
    if new_chapters and len(known) >= count:
        possible = context['accepted_words'] + context.get('pending_max_words', context['pending_planned_words'])
        for chapter in candidate['chapters']:
            scene_limit = sum(members[sc['card']]['body']['word_budget']['max_words'] for sc in chapter['scenes'])
            prior = context['existing_chapters'].get(str(chapter['index']), {})
            ceiling = chapter_budget(chapter, members, context)['max_words']
            available = max(0, ceiling - prior.get('accepted_words', 0) - prior.get('pending_max_words', 0))
            possible += min(available, scene_limit)
        tolerance = context['policy'].get('word_tolerance_pct', 0)
        if possible * 100 < book['target_words'] * (100 - tolerance):
            raise ValueError('末章方案加上已接受及已分配篇幅的上限仍不足全书目标，请重新分配章场篇幅')


def frozen_scene_budget(package: dict) -> dict | None:
    for item in package.get('items', ()):
        if item.get('source', '').startswith('scene:'):
            return json.loads(item['text']).get('word_budget')
    return None


def _feedback(actual: int, budget: dict, label: str) -> list[str]:
    if budget['min_words'] <= actual <= budget['max_words']:
        return []
    reason = '；剧情依据：' + budget['reason'] if label == '本场' else '，请按已批准场景的功能调整篇幅'
    return [f"{label}实际 {actual} 个非空白字符，已批准范围 {budget['min_words']}–{budget['max_words']}，"
            f"目标 {budget['target_words']}{reason}"]


def chapter_progress(store: Store, scene_id: str, state: dict, budgets: dict) -> dict | None:
    target = store.get('scene', scene_id)
    chapter = budgets['chapters'].get(target.chapter_id)
    if not chapter:
        return None
    active = manuscript_scene_ids(store, state)
    accepted = open_count = other_min = other_max = 0
    unknown_max = False
    for scene in store.list('scene'):
        if scene.chapter_id != target.chapter_id or scene.id == scene_id or scene.id not in active:
            continue
        if slot := state['slots'].get(scene.id):
            accepted += count_words(store.get('draft', slot['draft_id']).text)
        else:
            open_count += 1
            if other := budgets['scenes'].get(scene.id):
                other_min += other['min_words']
                other_max += other['max_words']
            else:
                unknown_max = True
    progress = {'chapter_min_words': chapter['min_words'], 'chapter_target_words': chapter['target_words'],
                'chapter_max_words': chapter['max_words'], 'accepted_other_words': accepted,
                'other_unwritten_scenes': open_count}
    if own := budgets['scenes'].get(scene_id):
        lower = own['min_words'] if unknown_max else max(own['min_words'], chapter['min_words'] - accepted - other_max)
        upper = min(own['max_words'], chapter['max_words'] - accepted - other_min)
        progress['feasible_min_words'] = lower
        progress['feasible_max_words'] = upper
        if lower <= upper:
            progress['suggested_scene_words'] = min(max(own['target_words'], lower), upper)
    return progress


def draft_feedback(store: Store, scene_id: str, state: dict, text: str, budgets: dict) -> list[str]:
    actual = count_words(text)
    scene_budget = budgets['scenes'].get(scene_id)
    issues = _feedback(actual, scene_budget, '本场') if scene_budget else []
    progress = chapter_progress(store, scene_id, state, budgets)
    if not progress:
        return issues
    if not progress['other_unwritten_scenes']:
        chapter = budgets['chapters'][store.get('scene', scene_id).chapter_id]
        issues.extend(_feedback(actual + progress['accepted_other_words'], chapter, '整章'))
    elif scene_budget and not issues and not progress['feasible_min_words'] <= actual <= progress['feasible_max_words']:
        issues.append(f"本场实际 {actual} 个非空白字符，依其他场已接受及待写篇幅，本场须在 "
                      f"{progress['feasible_min_words']}–{progress['feasible_max_words']} 字内才能使整章达标")
    return issues


def scene_length_feedback(store: Store, scene_id: str, manifest: dict, text: str) -> list[str]:
    from nw.story_delta import candidate_snapshot
    state = candidate_snapshot(store, StateHead(manifest['branch_id'], manifest['state_revision']),
                               manifest.get('candidate_delta_refs', ()), scene_id, include_later=True)
    return draft_feedback(store, scene_id, state, text, approved_length_budgets(store, state))
