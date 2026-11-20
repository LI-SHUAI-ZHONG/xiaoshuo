"""C00738 keeps the grant, the working procedure and the actual decision in the same system."""
import json
from pathlib import Path

import pytest

from nw.materials.authority_semantics import check_conflict, eligible, validate_use
from nw.materials.evidence import scene_checks, scene_materials, writer_checks
import test_stage_network_design_flow as flow
from test_world_method_creation_flow import finish_design, new_project, packets, policy
from test_project_methods import start


SOURCE = '档官签发借卷令后，守档人比对两枚印章和库房回执才能开卷'
LIMIT = '两枚印章少一枚或者库房回执未送达，守档人就退件，拒绝开卷'
EXEMPT = '持有署长紧急特许令时可先开卷并事后登记，本项调阅需在当日留痕'
KEY = 'C00738'


def decision(limit=LIMIT, extra=''):
    return {'key': KEY, 'excerpts': [SOURCE, limit], 'evidence': [
        {'ref': 'input:world_design:/members/0/body/rule', 'value': SOURCE},
        {'ref': 'input:world_design:/members/0/body/limits', 'value': limit + ('。' + extra if extra else '')}]}


@pytest.mark.parametrize('limit', ['缺少第二枚印不得开卷', '少一枚印就退件', '没有库房回执的借阅申请须退回'])
def test_qualification_follows_the_same_procurement(limit):
    assert eligible(KEY, SOURCE, limit)
    assert not eligible(KEY, SOURCE, limit, full_rule=SOURCE, full_limits='仅限客堂递水。')


@pytest.mark.parametrize('rule, limit', [
    (SOURCE, '码头食堂的青瓷饭碗仅供厨师盛汤'),
    (SOURCE, '档官签发外卖用的青瓷饭碗仅供厨师盛汤'),
    ('档官每周签发借卷令', LIMIT),
    ('档官无权签发借卷令，守档人比对两枚印章和库房回执再开卷', LIMIT),
    ('档官签发食堂饭票，守档人比对两枚印章和库房回执才能开卷', LIMIT),
    ('据说档官可以签发借卷令，并由守档人比对双印核验', LIMIT),
    (SOURCE, '缺少印章后的制度决定仍然待定'),
])
def test_rule_identity_and_program_condition_must_be_confirmed_together(rule, limit):
    assert not eligible(KEY, rule, limit)


@pytest.mark.parametrize('outcome', [
    '两枚印章齐备且已收到库房回执，守档人核验无误后开卷。',
    '少一枚印就退件，守档人将借卷申请退给来人。',
    '回执未送达，守档人依规拒绝开卷。',
    '库房回执尚未送达，守档人擅自开卷，事后因此停职受查。',
    '库房回执未到，守档人违背库规擅自开卷，此举导致他被问责。',
    '回执未送达，守档人先退件。库房回执送达后，守档人重新核对印章再开卷。',
])
def test_allowed_outcomes_include_explicit_violations_with_actual_consequences(outcome):
    validate_use(decision(), outcome, operation=outcome, stage='scene_design')


@pytest.mark.parametrize('outcome', [
    '库房回执未送达且少一枚印，守档人根据库规仍无条件开卷。',
    '档官收回借卷令、库房回执也未送达，守档人依规决定照常开卷。',
    '少一枚印，守档人擅自开卷；借阅就此顺利办结。',
    '库房回执未到，守档人依据船工临时签的证明开卷。',
    '库房回执未到，守档人依规开卷，而渠道中另有一名违规者已被停职。',
    '即便少一枚印也仍然可以开卷，守档人一律照办。',
    '库房回执尚未送达，守档人等候库房回执送达，但他此刻仍依规开卷。',
    '库房回执未到，守档人擅自开卷。外地茶商因自行定价受罚。',
])
def test_project_terms_do_not_let_a_reversed_decision_through(outcome):
    with pytest.raises(ValueError, match='制度授权'):
        validate_use(decision(), outcome, operation='少一枚印就退件。', stage='scene_design')
    with pytest.raises(ValueError, match='制度授权'):
        check_conflict(decision(), outcome, stage='scene_design')


def test_exception_must_be_in_the_actual_source_and_the_local_event():
    text = '库房回执未到，守档人收到署长紧急特许令，依规开卷并记入当日簿册。'
    validate_use(decision(extra=EXEMPT), text, operation=text, stage='scene_design')
    in_rule = decision()
    in_rule['evidence'].append({'ref': 'input:world_design:/members/0/body/rule', 'value': SOURCE + '。' + EXEMPT})
    validate_use(in_rule, text, operation=text, stage='scene_design')
    with pytest.raises(ValueError, match='制度授权'):
        validate_use(decision(), text, operation=text, stage='scene_design')
    with pytest.raises(ValueError, match='例外'):
        check_conflict(decision(extra=EXEMPT), text.replace('并记入当日簿册', '并声明无需事后登记'), stage='scene_design')
    with pytest.raises(ValueError, match='制度授权'):
        check_conflict(decision(extra=EXEMPT), text.replace('收到署长紧急特许令', '没有紧急特许令'), stage='scene_design')


@pytest.mark.parametrize('penalty', ['船工因此被停职。', '因此船工被问责。', '守档人因上月迟到被停职。', '守档人因此险些被停职。'])
def test_cross_field_penalty_belongs_to_the_breaching_executor(penalty):
    wrong = '库房回执未送达，守档人仍擅自开卷。'
    with pytest.raises(ValueError, match='制度授权'):
        validate_use({**decision(), 'authority_aftermath': penalty}, wrong, operation=wrong, stage='scene_design')
    validate_use({**decision(), 'authority_aftermath': '守档人因此被停职。'}, wrong, operation=wrong, stage='scene_design')


def test_partial_waiver_cannot_excuse_another_missing_credential():
    rule = decision(extra='持有署长紧急特许令时可免验第二枚印，借阅者仍须提交库房回执。')
    good = '少一枚印，库房回执已送达；守档人收到署长紧急特许令后依规开卷。'
    validate_use(rule, good, operation=good, stage='scene_design')
    wrong = '少一枚印，库房回执也未送达；守档人收到署长紧急特许令后依规开卷。'
    with pytest.raises(ValueError, match='制度授权'):
        validate_use(rule, wrong, operation=wrong, stage='scene_design')


def test_generic_bureaucratic_decision_is_not_a_project_specific_use():
    text = '办事人员根据规定和审批程序，决定依法拒绝开卷。'
    with pytest.raises(ValueError, match='落点未保留'):
        validate_use(decision(), text, operation=text, stage='plot_design')


def test_unrelated_action_is_not_a_governed_decision():
    check_conflict(decision(), '灶房尚未收到青菜，厨师仍将白饭端上桌。', stage='scene_design')


class AuthorityModel(flow.NetworkDesignModel):
    def __init__(self, outcome: str, field: str) -> None:
        super().__init__()
        self.outcome = outcome
        self.field = field

    def generate(self, messages, **params):
        result = super().generate(messages, **params)
        stage = json.loads(messages[-1]['content']).get('stage')
        if stage == 'scene_design':
            raw = json.loads(result.text)
            if 'products' in raw:
                body = raw['products']['members'][0]['body']
                if self.field in ('breach_with_consequence', 'breach_result_lost'):
                    body['conflict'] = '[FAKE] 岸亭回执未送达，渡吏仍违令擅自开闸放船。'
                    body['planned_result'] = '[FAKE] 渡吏因此被停职调查，港务官将放行案登记并追责。'
                elif self.field == 'separate_fields':
                    body['conflict'] = '[FAKE] 岸亭回执未送达，渡吏登记缺据，船工在闸前等候核验。'
                    body['planned_result'] = '[FAKE] 守闸人依据港规，立即开闸放船。'
                else:
                    body[self.field] = self.outcome
                result.text = json.dumps(raw, ensure_ascii=False)
        elif stage == 'state_transition' and self.field == 'breach_with_consequence':
            raw = json.loads(result.text)
            if 'products' in raw and raw['products'].get('patches'):
                raw['products']['patches'][0]['planned_result'] += '。渡吏因此被停职调查。'
                result.text = json.dumps(raw, ensure_ascii=False)
        return result


@pytest.mark.parametrize('good,field', [(True,'conflict'), (True,'breach_with_consequence'), (False,'conflict'), (False,'planned_result'), (False,'separate_fields'), (False,'breach_result_lost')])
def test_project_job_tests_the_scene_decision_against_the_independently_frozen_world(tmp_path: Path, monkeypatch, good, field):
    flow.catalogue(tmp_path, monkeypatch)
    flow.reference.available_method(tmp_path, monkeypatch, scopes=('book',))
    monkeypatch.setattr(flow.test_planning, 'Planner', flow.TwoScenes)
    outcome = ('[FAKE] 岸亭回执未送达，渡吏拒绝放行，给船工补开一份书面回执。' if good else
               '[FAKE] 岸亭回执未送达、双印令也不齐，港规仍要求渡吏无条件立即放行，守闸人依据这条港规当场开闸放船。')
    model = AuthorityModel(outcome,field)
    with flow.Store(tmp_path/'[FAKE]-authorization', create=True, test_mode=True) as store:
        new_project(store, flow.NEED)
        book = finish_design(store,model)
        if good:
            chapter = finish_design(store,model,'chapter',book.outputs['proposal_id'])
            app = chapter.outputs['application']
            session = app['material_design']['work_session']
            flow.verify_chain(session)
            design = scene_materials(store,app['chapters'][0]['scenes'][0]['scene_id'])
            [review] = [r for r in scene_checks(design) if r.get('network_design_key') == KEY]
            [writing] = [r for r in writer_checks(design) if r['id'] == review['id']]
            expected = '[FAKE] 岸亭回执未送达，渡吏仍违令擅自开闸放船。' if field == 'breach_with_consequence' else outcome
            assert writing['observable'] == review['binding']['observable'] == expected
        else:
            _, result = start(store, model, 'chapter', book.outputs['proposal_id'], policy=policy())
            assert result.status == 'BLOCKED' and '制度授权' in result.reason, result.reason
            assert any(row['key'] == KEY and row['required'] for row in packets(model,'scene_design')[-1]['network_design_candidates'])
            assert store.connection.execute('SELECT COUNT(*) FROM plan_applications').fetchone()[0] == 1


def test_writing_job_receives_the_frozen_program_exception(tmp_path: Path, monkeypatch):
    exception = '持有港务官紧急特许令时可先开闸并事后登记'
    unrelated = '持有食堂餐券时可先享用晚饭'
    base_limit = flow.LIMIT
    monkeypatch.setattr(flow, 'LIMIT', base_limit + exception + '。' + unrelated + '。')
    flow.catalogue(tmp_path, monkeypatch)
    flow.reference.available_method(tmp_path, monkeypatch, scopes=('book',))
    monkeypatch.setattr(flow.test_planning, 'Planner', flow.TwoScenes)
    model = flow.NetworkDesignModel()
    with flow.Store(tmp_path / '[FAKE]-exception-writing', create=True, test_mode=True) as store:
        new_project(store, flow.NEED)
        book = finish_design(store, model)
        chapter = finish_design(store, model, 'chapter', book.outputs['proposal_id'])
        scene_id = chapter.outputs['application']['chapters'][0]['scenes'][0]['scene_id']
        [review] = [r for r in scene_checks(scene_materials(store, scene_id)) if r.get('network_design_key') == KEY]
        assert exception not in review['method_artifact']['excerpts'][1]
        job = flow.start_job(store, flow.JobRequest('write', scene_ids=[scene_id], budget=flow.Budget(20, 200000, 6000)))
        result = flow.resume_job(store, job.id, model, flow.config(store))
        assert result.status == 'WAITING', result.reason
        [guide] = [json.loads(item['text']) for messages in model.calls
                   for item in json.loads(messages[-1]['content']).get('items', [])
                   if item['source'] == 'material:' + review['id']]
        decision_limit = guide['check']
        assert '岸亭回执未送达' in decision_limit and exception in decision_limit
        assert unrelated not in decision_limit
