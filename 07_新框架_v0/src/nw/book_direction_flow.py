"""Select one durable story direction before detailed book planning."""
import json
from typing import Callable

from nw.novel_calls import JobCalls
from nw.novel_store import JobPaused
from nw.task_models import canonical, content_sha256


PROPOSE = 'direction:book:propose'
CONFIRM = 'direction:book:confirm'
GATE_KIND = 'book_direction_selection'
LABEL = '全书方向与确认'


def validate_choice(target: dict, choice: dict) -> None:
    if choice['action'] == 'approve' and choice.get('root') not in [
        candidate['id'] for candidate in target['candidates']
    ]:
        raise ValueError('请选择本次生成的一份全书方向')


def choose_direction(calls: JobCalls, decide: Callable) -> dict:
    from nw.book_directions import direction_options, prepare_direction_task, validate_direction_options

    journal = calls.journal
    creative = bool(journal.request.get('creative_workflow'))
    result = calls.task(PROPOSE, lambda: prepare_direction_task(calls, PROPOSE),
                        lambda raw: validate_direction_options(raw, creative=creative))
    candidates = direction_options(result.parsed, creative=creative)
    target = {'kind': GATE_KIND, 'task_id': result.id, 'candidates': candidates}
    actions = {'approve': 'novel_confirm', 'reject': 'novel_reject'}
    choice = journal.gate(CONFIRM, target, decide, actions, lambda item: validate_choice(target, item))
    gate = journal.latest(CONFIRM)
    decision_id = f'{journal.id}:{CONFIRM}'
    record = journal.store.connection.execute(
        'SELECT action,targets_json FROM story_decisions WHERE id=?', (decision_id,)).fetchone()
    expected = {'job_id': journal.id, 'step': CONFIRM, 'token': gate['input']['token'],
                'target': target, 'choice': choice}
    if (record is None or record['action'] != actions.get(choice.get('action'))
            or canonical(json.loads(record['targets_json'])) != canonical(expected)):
        raise JobPaused('STALE', CONFIRM, 'STALE_BOOK_DIRECTION: 全书方向确认记录与本次候选不一致')
    if choice['action'] == 'reject':
        raise JobPaused('REJECTED', CONFIRM, 'BOOK_DIRECTION_REJECTED: 当前方向均已退回，可按退回意见重新生成。')
    validate_choice(target, choice)
    selected = next(candidate for candidate in candidates if candidate['id'] == choice['root'])
    return {'task_id': result.id, 'decision_id': decision_id, 'candidate_id': selected['id'],
            'candidate': selected, 'sha256': content_sha256(selected)}
