
"""Structured candidate plans and validation before saving model proposals."""
from dataclasses import dataclass
from graphlib import TopologicalSorter
import re

from nw.cards import _body
from nw.materials.binding import validate_bindings
from nw.story_models import CardRef
from nw.story_state import text

SCOPES = ('book', 'volume', 'chapter', 'scene', 'replan')
_DIRECTION = ('title', 'reader_promise', 'protagonist_want', 'conflict', 'resistance',
              'choice', 'cost', 'consequence', 'ending_direction')
_MEMBER_KINDS = {'world', 'character', 'plot', 'promise', 'volume', 'chapter', 'scene'}
_SCENE_TEXT = ('entering_state', 'conflict', 'choice', 'planned_result', 'allowed_disclosure')
_MAX_MEMBERS = 30


@dataclass(frozen=True)
class PlanProposal:
    id: str
    scope: str
    candidate_cards: list[CardRef]
    materialization: list[dict]
    findings: list[dict]
    task_id: str
    application: dict | None = None


def plan_prompt(scope: str, *, approved_direction: dict | None = None, planning_hierarchy: bool = False) -> str:
    opening = f'按冻结的 Brief、已批准方向、已接受状态和可用参考，提出 2–3 种不同的 {scope} 方案。'
    book = 'book 只提方向，chapters 为空；'
    if approved_direction is not None:
        from nw.materials.book_direction import stage_instruction

        opening = ('沿用输入的 approved_direction.candidate，只提交一个详细的全书设计方案。'
                   + stage_instruction('plot_design'))
        book = 'book 细化已选方向的世界、人物、剧情和收束计划，chapters 为空；'
    details = 'volume 带卷卡；chapter 只列一章；scene 只列一场；'
    if planning_hierarchy:
        from nw.materials.planning_hierarchy import INSTRUCTIONS

        opening += INSTRUCTIONS.get(scope, '')
        if scope == 'volume':
            opening = '沿用输入的已批准全书方案，只提交一份当前卷纲。' + INSTRUCTIONS[scope]
            details = '当前卷纲的 chapters 为空。'
    return (
        opening + '只输出 JSON 对象，' +
        f'顶层只有 scope（{scope}）及 candidate_cards 数组。每项只含 kind（plot）、body、members、chapters、'
        'open_world_rules（字符串数组）。body 必填：' + '、'.join(_DIRECTION) +
        '。members 是卡片，每项含 key（唯一 ASCII 字母、数字、下划线）、kind、body，可选 requires（必需卡 key/ID 数组）。'
        'world body 含 title/rule/limits；character 含 name/role/want；volume 含 title/goal/turn；'
        'chapter 含 title/goal/consequence；plot 含 title/conflict/consequence；promise 含 title/setup/payoff。'
        'scene body 含 title/goal/pov/characters/character_goals 及 ' + '、'.join(_SCENE_TEXT) +
        '。pov、characters 和 character_goals 的键使用人物卡 key 或输入已有 ID。'
        '需进入 POV 的卡应明确设 visibility 为 public 或 holders（附 holders 人物 key/ID）；'
        '私密设定留 author_only。核心世界规则待定时填 open_world_rules，勿擅自填成既定事实。'
        'chapters 每项含 index、card（本地 chapter key，已有章用 null）、scenes。'
        'scenes 每项含 index、card（本地 scene key）、story_order（整数，可倒叙）。'
        + book + details +
        'replan 以新的章/场景号保存候选改案。每案都列清选择、代价、后果与未决问题。'
    )


def _ids(value: object, allowed: set[str]) -> bool:
    return (isinstance(value, list) and all(isinstance(key, str) and key in allowed for key in value)
            and len(value) == len(set(value)))


def _members(rows: object, existing: dict[str, str]) -> dict[str, dict]:
    if not isinstance(rows, list) or len(rows) > _MAX_MEMBERS:
        raise ValueError('Invalid plan member count')
    members = {}
    for row in rows:
        if (not isinstance(row, dict) or not {'key', 'kind', 'body'} <= row.keys() or
                row.keys() - {'key', 'kind', 'body', 'requires'} or not text(row['key']) or
                not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,31}', row['key']) or row['key'] in members or
                row['key'] in existing or not isinstance(row['kind'], str) or row['kind'] not in _MEMBER_KINDS):
            raise ValueError('Invalid or duplicate plan member')
        members[row['key']] = {**row, 'body': _body(row['kind'], row['body'])}
    people = {key for key, kind in existing.items() if kind == 'character'}
    people.update(key for key, row in members.items() if row['kind'] == 'character')
    for key, row in members.items():
        body = row['body']
        if not _ids(row.get('requires', []), (members.keys() | existing.keys()) - {key}):
            raise ValueError('Unknown mandatory card in plan')
        if not _ids(body.get('holders', []), people):
            raise ValueError('Unknown visibility holder in plan')
        if 'introducer' in body.get('casting', {}) and body['casting']['introducer'] not in people - {key}:
            raise ValueError('身份介绍者必须是本项目中的另一位人物')
        if row['kind'] == 'scene':
            if 'length_policy' in body:
                raise ValueError('项目篇幅配置由已批准方案绑定，场景不得重写')
            if (body['pov'] not in people or not _ids(body.get('characters'), people) or
                    not all(text(body.get(field)) for field in _SCENE_TEXT) or
                    set(body.get('character_goals', {})) != {body['pov'], *body['characters']}):
                raise ValueError('Scene requires resolved character IDs, individual goals and a complete scene task')
    # A mandatory-card cycle cannot be resolved by applying the same candidate.
    tuple(TopologicalSorter({key: row.get('requires', []) for key, row in members.items()}).static_order())
    return members


def _chapters(rows: object, scope: str, members: dict[str, dict]) -> None:
    if (not isinstance(rows, list) or len(rows) > 5 or (scope == 'book') != (not rows) or
            scope in ('chapter', 'scene') and len(rows) != 1):
        raise ValueError('Invalid chapter materialization for scope')
    chapter_cards = {key for key, row in members.items() if row['kind'] == 'chapter'}
    scene_cards = {key for key, row in members.items() if row['kind'] == 'scene'}
    if scope=='book' and not rows and not scene_cards:return  # outline cards are designs; no prose coordinates yet
    used_chapters = set()
    for chapter in rows:
        if (not isinstance(chapter, dict) or set(chapter) != {'index', 'card', 'scenes'} or
                type(chapter['index']) is not int or not 1 <= chapter['index'] < 2**63 or chapter['index'] in used_chapters or
                not isinstance(chapter['scenes'], list) or not 1 <= len(chapter['scenes']) <= 10):
            raise ValueError('Invalid or duplicate plan chapter')
        if chapter['card'] is not None:
            if not text(chapter['card']) or chapter['card'] not in chapter_cards:
                raise ValueError('Invalid chapter card reference')
            chapter_cards.remove(chapter['card'])
        used_chapters.add(chapter['index'])
        used_scenes = set()
        for scene in chapter['scenes']:
            if (not isinstance(scene, dict) or set(scene) != {'index', 'card', 'story_order'} or
                    type(scene['index']) is not int or not 1 <= scene['index'] < 2**63 or scene['index'] in used_scenes or
                    type(scene['story_order']) is not int or not text(scene['card']) or scene['card'] not in scene_cards):
                raise ValueError('Invalid or duplicate plan scene')
            scene_cards.remove(scene['card'])
            used_scenes.add(scene['index'])
        if scope == 'scene' and len(used_scenes) != 1:
            raise ValueError('Scene scope materializes exactly one scene')
    if chapter_cards or scene_cards:
        raise ValueError('Every chapter and scene card needs a materialization coordinate')


def validate_plan(output: dict, scope: str, existing: dict[str, str], materials: list[dict] = (),
                  material_deferrals: dict | None = None,material_work: dict | None = None, length_context: dict | None = None,
                  *, approved_direction: dict | None = None, planning_hierarchy: bool = False) -> None:
    from nw.materials.planning_hierarchy import validate_plot, volume_outline

    outline = volume_outline(scope, planning_hierarchy)
    minimum=1 if scope!='book' and material_work and material_work.get('policy') in {'artifact-stage-binding-v3','artifact-stage-binding-v4'} else 2
    if approved_direction is not None:
        if scope != 'book' or output['scope'] != scope or len(output['candidate_cards']) != 1:
            raise ValueError('BOOK_DIRECTION: 已确认全书方向只接受一个对应的深化方案')
    elif outline:
        if output['scope'] != scope or len(output['candidate_cards']) != 1:
            raise ValueError('当前卷只提交一份围绕已批准父纲的设计')
    elif output['scope'] != scope or not minimum <= len(output['candidate_cards']) <= 3:
        raise ValueError('Expected 2–3 candidates for the requested scope')
    choices = set()
    for candidate in output['candidate_cards']:
        if (set(candidate) - {'material_bindings', 'process_bindings','material_work'} != {'kind', 'body', 'members', 'chapters', 'open_world_rules'} or
                candidate['kind'] != 'plot' or
                not all(text(candidate['body'].get(field)) for field in _DIRECTION) or
                'members' in candidate['body'] or 'unknowns' in candidate['body'] or
                not isinstance(candidate['open_world_rules'], list) or
                not all(text(rule) for rule in candidate['open_world_rules'])):
            raise ValueError('Invalid story direction, choice, cost or unresolved rules')
        body = _body('plot', candidate['body'])
        choice = ' '.join(body['choice'].casefold().split())
        if choice in choices:
            raise ValueError('Plan candidates need distinct choices')
        choices.add(choice)
        members = _members(candidate['members'], existing)
        if planning_hierarchy and scope in ('book', 'volume'):
            validate_plot(candidate, scope)
        _chapters(candidate['chapters'], 'book' if outline else scope, members)
        if length_context:
            from nw.length_plan import validate_candidate
            validate_candidate(candidate, scope, length_context)
        elif 'length_plan' in body or any({'word_budget', 'chapter_word_budget'} & member['body'].keys()
                                           for member in members.values()):
            raise ValueError('未冻结项目篇幅需求，不能给此方案附加写审字数约束')
        if outline:
            if any(candidate.get(field) for field in ('material_bindings', 'process_bindings')):
                raise ValueError('卷纲只交付阶段设计，正文绑定在具体场景环节完成')
        else:
            validate_bindings(candidate, scope, members, existing, materials, material_deferrals)
        from nw.materials.work_application import validate_work
        validate_work(candidate,material_work)
        if scope == 'volume' and not any(row['kind'] == 'volume' for row in members.values()):
            raise ValueError('Volume scope requires a volume card')
