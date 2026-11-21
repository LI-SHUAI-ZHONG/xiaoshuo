"""Follow an assigned character's contribution from the plot into accepted prose."""
import json
import re

from nw.materials.scene_actions import selected_action_ids
from nw.materials.template_support import product, require, rows
from nw.models import Draft


PREFIX = 'work:cast-result:'
SCHEMAS = {
    'plot_design': 'cast_events:[{demand:本轮职责id,event:本步event_nodes.id}]',
    'scene_design': 'cast_payoffs:[{demand:本轮职责id,scene:本场key,action:该场选中的行动id,step_index:动作步骤的零基下标}]',
}
INSTRUCTIONS = {
    'plot_design': ('cast_work 是本轮人物已承接的职责。每项在 cast_events 指向至少一个实际节点，受派人列入其 actors。'
                    '节点 goal 沿用该职责的 event，或 obstacle 沿用其 obstacle，或 completion_condition 沿用其 result。'
                    '不同人物可以共同推进一个节点，同一人可以在不同节点发挥不同作用。场上执行独立选定行动的人应有本节点的职责。'
                    '全书备选方向无需重复演一遍。'),
    'event_design': ('直接后继若承接人物职责，请保留完成该职责的人及前事件的完成门槛；'
                     '也可以留到其他场景处理。'),
    'action_design': ('为 cast_events 对应的实际节点或直接后继设计受派者可执行的候选。'
                      '在同一个 steps 条目中，action 与 result 分别沿用该需求的 action 和 result；'
                      '用 object、obstacle、response 具体设计他本人怎样实施，无法照做则退回补设计。'),
    'scene_design': ('在 cast_payoffs 给每项本轮职责选择真正发生作用的场和步骤。'
                     '该动作须由受派者在所选事件中执行。一次步骤只核销一项职责；相关人物可各有自己的行动。'
                     '路过或围观的人无须另设行动。动作与结果是当场的设计目标，审稿时按实际正文验收。'),
}


def cast_work(products: dict, context: dict) -> list[dict]:
    from nw.materials.cast_demands import effective_demands

    people = {r['demand']: r['actor'] for r in product(products, 'character_design')['cast_assignments']}
    return [{'id': d['id'], 'actor': people[d['id']], **{k: d[k] for k in ('event', 'obstacle', 'action', 'result')}}
            for d in effective_demands(products, context)]


def validate(stage: str, value: dict, products: dict, context: dict) -> None:
    if stage not in (*SCHEMAS, 'action_design'):
        return
    work = {row['id']: row for row in cast_work(products, context)}
    covered = set()
    if stage == 'plot_design':
        nodes = {r['id']: r for r in value['event_nodes']}
        seen = set()
        for row in rows(value, 'cast_events', {'demand', 'event'}):
            duty, event = row['demand'], row['event']
            require(duty in work and event in nodes and (duty, event) not in seen, '职责须关联真实且不重复的剧情节点')
            task, node = work[duty], nodes[event]
            require(task['actor'] in node['actors'], '剧情节点未安排实际受派人')
            require(any(node[field] == task[source] for field, source in (
                ('goal', 'event'), ('obstacle', 'obstacle'), ('completion_condition', 'result'))),
                '人物职责没有落到该事件的目标、障碍或完成条件')
            seen.add((duty, event))
            covered.add(duty)
    else:
        links = {(r['demand'], r['event']) for r in product(products, 'plot_design')['cast_events']}
        predecessors = {r['id']: r['predecessor'] for r in product(products, 'event_design')['candidates']}
        if stage == 'action_design':
            candidates = {(a['actor'], predecessors.get(a['event'], a['event']), step['action'], step['result'])
                          for a in value['candidates'] for step in a['steps']}
            for duty, node in links:
                task = work[duty]
                if (task['actor'], node, task['action'], task['result']) in candidates:
                    covered.add(duty)
            require(covered == work.keys(), '有已分派职责缺少可供选场的本人行动及其直接结果')
            return
        selected = selected_action_ids(value)
        events = {r['scene']: r['event'] for r in value['selected_events']}
        actions = {r['id']: r for r in product(products, 'action_design')['candidates']}
        occupied = set()
        actor_nodes = {(work[duty]['actor'], event) for duty, event in links}
        for scene, chosen in selected.items():
            event = events[scene]
            require(all((actions[a]['actor'], predecessors.get(event, event)) in actor_nodes for a in chosen),
                    '本场有执行独立行动的人物尚未获得相应剧情职责，请补场景选择或上游分派')
        for row in rows(value, 'cast_payoffs', {'demand', 'scene', 'action', 'step_index'}):
            duty, scene, action, index = (row[k] for k in ('demand', 'scene', 'action', 'step_index'))
            require(duty in work and action in selected.get(scene, ()) and action in actions,
                    '职责须落实到本场实际选中的行动')
            task, candidate = work[duty], actions[action]
            event = events[scene]
            require((duty, predecessors.get(event, event)) in links and candidate['event'] == event
                    and candidate['actor'] == task['actor'], '该职责的剧情节点、场内事件与执行人物不一致')
            require(type(index) is int and 0 <= index < len(candidate['steps'])
                    and (scene, action, index) not in occupied, '须指定一个尚未分给其他职责的实际行动步骤')
            step = candidate['steps'][index]
            require(step['action'] == task['action'] and step['result'] == task['result'],
                    '选中的行动步骤未落实该职责规定的动作及其直接结果')
            occupied.add((scene, action, index))
            covered.add(duty)
    require(covered == work.keys(), '有本轮已分派人物职责尚未落实到剧情节点或所选场景行动')


def scene_checks(records: dict, scene: str, context: dict) -> list[dict]:
    scenes = product(records, 'scene_design')
    links = [(i, link) for i, link in enumerate(scenes.get('cast_payoffs', ())) if link['scene'] == scene]
    if not links:
        return []
    work = {row['id']: row for row in cast_work(records, context)}
    event = next(row['event'] for row in scenes['selected_events'] if row['scene'] == scene)
    result = []
    for index, link in links:
        task = work[link['demand']]
        # The paired visible action carries the published actor and every step's action and result.
        result.append({'id': f'{PREFIX}{scene}:{index}', 'profile': 'method_work',
            'binding': {'observable': f'{link["action"]} 第{link["step_index"] + 1}步',
                        'check': '表现这一步由谁选择、怎样改变局面。'},
            'method_artifact': {'demand': task['id'], 'event': event, 'action_ref': link['action'],
                                'event_goal': task['event'], 'obstacle': task['obstacle'],
                                'step_index': link['step_index']},
            'action_check': f'work:selected:action:{scene}:{link["action"]}',
            'evidence_required': '与所指行动共享本稿实质引文；引用实际后果，说明怎样改变障碍或推进目标。'})
    return result


def performance(check: dict, checks: list[dict]) -> dict:
    """Resolve the role's selected step from the very contract used for independent review."""
    design = check['method_artifact']
    if 'actor' in design:
        return design
    action = next((row for row in checks if row['id'] == check['action_check']), None)
    require(action is not None and action['method_artifact'].get('id') == design['action_ref'],
            '人物职责依据缺少正式选定的同场行动')
    visible = json.loads(action['binding']['observable'])
    index = design['step_index']
    require(type(index) is int and 0 <= index < len(visible['steps']), '人物职责引用了不存在的动作节拍')
    step = visible['steps'][index]
    return {**design, 'actor': visible['actor'], 'action': step['action'], 'candidate_result': step['result']}


def assess(checks: list[dict], reviews: list[dict], draft: Draft) -> None:
    """Only use reviewed passages that actually refer back to this actor's selected action."""
    by_id = {r['id']: r for r in reviews}
    for check in checks:
        if not check['id'].startswith(PREFIX):
            continue
        review = by_id[check['id']]
        if review['status'] != 'pass':
            continue
        action = by_id[check['action_check']]
        related = any(_shares_passage(left, right, draft)
                      for left in review['evidence'] for right in action['evidence'])
        if action['status'] != 'pass' or not related:
            review.update(status='failed', reason='本项职责缺少与受派者所选行动相符的当前稿证据。')


_CLAUSE = re.compile(r'[^。.!！?？；;，,：:“”"「」\n]+')


def _shares_passage(left: dict, right: dict, draft: Draft) -> bool:
    if left['id'] != draft.id or right['id'] != draft.id:
        return False
    start, end = max(left['start'], right['start']), min(left['end'], right['end'])
    if end <= start:
        return False
    overlap = draft.text[start:end]
    if not any(c.isalnum() for c in overlap):
        return False
    if sum(c.isalnum() for c in overlap) >= 8:
        return True
    if left['start'] == right['start'] and left['end'] == right['end'] and len(''.join(overlap.split())) >= 8:
        # Both checks pinned exactly the same substantive excerpt under the base review contract.
        return sum(c.isalnum() for c in overlap) >= 2
    # A complete short reply or action can be cited from two different longer passages.
    return any(start <= match.start() and match.end() <= end and any(c.isalnum() for c in match.group())
               for match in _CLAUSE.finditer(draft.text))
