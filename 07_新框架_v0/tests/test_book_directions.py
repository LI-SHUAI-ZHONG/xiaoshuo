"""A bounded direction shortlist uses the normal task ledger and budget."""
import json
from pathlib import Path

import pytest

from nw.call_budget import BudgetExceeded, read_budget
from nw.config import Config
from nw.llm.base import GenResult
from nw.novel_calls import JobCalls
from nw.novel_store import JobPaused, JobRequest, Journal, start_job
from nw.store import Store
from nw.story_state import adopt_story
from nw.task_models import Budget, canonical
from nw.tasks import read_input_manifest
from story_fixture import baseline

STEP = 'direction:book:propose'


def options() -> dict:
    return {'candidates': [
        {'title': '[FAKE] 盐线外', 'premise': '被逐出盐行的抄账员追查盐票为何会抹去姓名。',
         'world_premise': '海潮淹没旧城，每张船票只有经录名方能通渡。',
         'protagonist': '抄账员已被销名，身边同事也不敢认他。',
         'goal': '找到当年被替换的渡簿，恢复家人的渡航资格。',
         'conflict': '长老握有唯一原册，并以家人无法通渡迫使抄账员服从。',
         'long_term_drive': '先见证票据失效的后果，再争取外岛互证，最终公开旧册推翻非法销名。',
         'type_fit': '用航票和录名构成玄幻规则，以失去登船资格表现代价。',
         'author_fit': '家人面临失去通渡资格，推动故事的始终是活人。'},
        {'title': '[FAKE] 织浪图', 'premise': '见习织工发现祖传纹样能召来一段短潮。',
         'world_premise': '岛间潮线依发出的织声短时偏移，由接潮者承担反向潮力。',
         'protagonist': '刚入门的织工背负一次误拨航道的赔偿。',
         'goal': '修复被短潮冲毁的浮桥，让困守外岛的居民回家。',
         'conflict': '善织的师傅认定浮桥必须拆除，否则内港会承受全部反潮。',
         'long_term_drive': '修桥尝试击穿原有利益平衡，各岛重谈分潮规则，织工选择公开承担反潮。',
         'type_fit': '用织声与反潮代价形成玄幻规则，并让每次尝试改变航路。',
         'author_fit': '只安排活人撤离和承担后果，遇难人员维持已发生事实。'},
    ]}


class Model:
    name = 'fake'

    def __init__(self, output: dict) -> None:
        self.output = output
        self.calls: list[tuple] = []

    def generate(self, messages: list[dict], **params: object) -> GenResult:
        self.calls.append((messages, params))
        return GenResult(canonical(self.output), 'complete', {}, 'response', {'test': True})


def _job(store: Store, *, context: int = 24000) -> str:
    store.init_project('潮票')
    store.add_brief('海边失落的船票引出两种故事方向。', '码头亡者不可复活。')
    adopt_story(store, baseline(), {})
    selection = {'types': [{'id': 'GENRE_XUANHUAN', 'name': '玄幻', 'definition': '超自然世界的原创故事。'}]}
    preference = {'key': 'structure.test', 'name': '逐步揭示', 'meaning': '先由结果引疑问，再追查规则。'}
    governance = {'type_selection': {'creation_plan': selection},
                  'plot_design': {'creation_plan': {'preferences': [preference]}},
                  'scene_design': {'creation_plan': {'preferences': [preference]}}}
    return start_job(store, JobRequest('design', design_scope='book', budget=Budget(3, context, 2400),
                                       governance_inputs=governance)).id


def _calls(store: Store, ident: str, provider: Model, *, retry: bool = False) -> JobCalls:
    return JobCalls(Journal(store, ident), provider, Config('fake', '', 'isolation', '', 3, {}, store.directory), retry)


def _run(calls: JobCalls):
    from nw.book_directions import prepare_direction_task, validate_direction_options

    return calls.task(STEP, lambda: prepare_direction_task(calls, STEP), validate_direction_options)


def test_shortlist_is_frozen_once_and_can_reopen_without_another_call(tmp_path: Path) -> None:
    from nw.book_directions import direction_options

    provider = Model(options())
    with Store(tmp_path, create=True, test_mode=True) as store:
        ident = _job(store)
        calls = _calls(store, ident, provider)
        result = _run(calls)
        expected = direction_options(result.parsed)
        assert len(expected) == 2 and expected[0]['id'] != expected[1]['id']
        step = calls.journal.latest(STEP)
        manifest, package = read_input_manifest(store, step['output']['manifest_id'])
        sent, _ = provider.calls[0]
        assert manifest['purpose'] == 'book_directions'
        assert json.loads(sent[1]['content']) == package
        assert package['brief']['constraints'] == '码头亡者不可复活。'
        assert package['types'][0]['id'] == 'GENRE_XUANHUAN'
        assert [row['name'] for row in package['preferences']] == ['逐步揭示']
        assert store.list('scene') == store.list('draft') == []
        assert read_budget(store, ident).used_calls == 1
    with Store(tmp_path, test_mode=True) as store:
        replay = _run(_calls(store, ident, provider))
        assert direction_options(replay.parsed) == expected
        assert len(provider.calls) == 1


def test_shortlist_rejects_cosmetic_alternatives_and_retries_same_frozen_inputs(tmp_path: Path) -> None:
    raw = options()
    raw['candidates'][1] = {**raw['candidates'][0], 'title': '[FAKE] 靠岸'}
    provider = Model(raw)
    with Store(tmp_path, create=True, test_mode=True) as store:
        ident = _job(store)
        with pytest.raises(JobPaused, match='BOOK_DIRECTION:.*实质差异'):
            _run(_calls(store, ident, provider))
        assert read_budget(store, ident).used_calls == 1
        with pytest.raises(JobPaused, match='BOOK_DIRECTION'):
            _run(_calls(store, ident, provider))
        assert len(provider.calls) == 1
        provider.output = options()
        assert _run(_calls(store, ident, provider, retry=True)).validation == 'VALID'
        assert provider.calls[0] == provider.calls[1]
        attempts = store.connection.execute('SELECT manifest_id,retry_of FROM task_calls ORDER BY rowid').fetchall()
        assert attempts[0]['manifest_id'] == attempts[1]['manifest_id'] and attempts[1]['retry_of']


@pytest.mark.parametrize('field,bad', [('conflict', '待定'), ('world_premise', []), ('title', '潮' * 60)])
def test_shortlist_bounds_and_requires_story_fields(field: str, bad: object) -> None:
    from nw.book_directions import validate_direction_options

    raw = options()
    raw['candidates'][0][field] = bad
    with pytest.raises(ValueError, match='BOOK_DIRECTION:'):
        validate_direction_options(raw)


def test_direction_call_preflight_preserves_hard_constraints_and_blocks_before_send(tmp_path: Path) -> None:
    provider = Model(options())
    with Store(tmp_path, create=True, test_mode=True) as store:
        ident = _job(store, context=100)
        with pytest.raises(BudgetExceeded, match='CONTEXT_TOO_LARGE'):
            _run(_calls(store, ident, provider))
        assert not provider.calls and read_budget(store, ident).used_calls == 0
