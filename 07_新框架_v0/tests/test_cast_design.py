from copy import deepcopy
from types import SimpleNamespace

import pytest

from nw.cards import _body, decide_card, read_card, save_card
from nw.materials import cast_design, narration
from nw.materials.phase_contract import validate_phase
from nw.materials.phase_projection import method_checks
from nw.materials.phase_schema import schema
from nw.planning import _translate
from nw.store import Store
from nw.story_models import CardRef
from nw.task_models import canonical, content_sha256
from test_narration_design import case, guide


def actor(entry='withheld'):
    body = {'name': '阿禾', 'role': '渡口抄录员', 'want': '追回遗失的旧册', 'visibility': 'public',
            'background': '幼时抄错过水位名册', 'voice': '报页码，再报姓名', 'behavior': '受盘问先比对页码',
            'creation_reason': '主角要查前夜过闸者，抄录员有交接旧册的职责', 'scene_function': '移交过闸名册',
            'independent_goal': '要在父亲受罚前找出丢失的一页', 'boundaries': '只认识亲见的过闸者',
            'casting': {'standing': 'supporting', 'entry': entry, 'public_identity': '渡口抄录员',
                        'need_ref': 'brief:text', 'need_quote': '查清过闸者'}}
    if entry == 'withheld':
        body['casting'].update(clue='袖里露出半枚潮印', secret='北汛密使', trigger='两枚潮印吻合')
    if entry == 'other':
        body['casting'].update(introducer='yan', introducer_basis='验过渡口值勤名册', introducer_source='prior')
    return body


def test_writer_brief_retains_current_directions_and_does_not_disclose_future_casting():
    brief = {'version':3, 'text':'去渡口找旧册。抄录员其实是北汛密使！两枚潮印吻合才说明来历。',
             'constraints':'用第一人称。\n不得让北汛密使提前暴露。'}
    visible = cast_design.writer_brief(brief, [{'body':actor()}])
    assert visible == {'version':3, 'text':'去渡口找旧册。', 'constraints':'用第一人称。'}
    assert '北汛密使' in brief['text'] and '两枚潮印吻合' in brief['text']
    assert cast_design.writer_brief(brief, []) == brief


def staged(entry='withheld'):
    session, records, scene, context = case()
    context.update(narration_policy=narration.ACCESS_POLICY, brief={'text': '查清过闸者'})
    scene['narrative_person'] = 'first'
    context['approved_cards'] = [r for r in context['approved_cards'] if r['card_id'] != 'lin']
    records['character_design']['products']['members'][0]['body']['background'] = '昨晚验过渡口值勤名册，认得她的签字。'
    records['character_design']['products']['members'].append({'key': 'lin', 'kind': 'character', 'body': actor(entry)})
    for record in records.values():
        record['sha256'] = content_sha256(record['products'])
    session['context'] = context
    return session, records, context


def staged_with_approved(directory, *keys):
    session, records, context = staged()
    characters = records['character_design']['products']
    with Store(directory, create=True, test_mode=True) as store:
        store.init_project('隔离已知人物身份')
        for row in characters['members']:
            if row['key'] not in keys:
                continue
            ref = save_card(store, {'card_id': row['key'], 'kind':'character',
                                    'origin':'model', 'body':row['body']}, None)
            decide_card(store, ref, 'approved', '前一阶段已确认该人物')
            context['approved_cards'].append(read_card(store, ref))
    characters['members'] = [row for row in characters['members'] if row['key'] not in keys]
    records['character_design']['sha256'] = content_sha256(characters)
    return session, records, context


def beat(mode, owner, ref, quote, text, witnesses=None):
    r = guide('current', mode, owner, ref, quote, text)
    if witnesses is not None:
        r['narration']['witnesses'] = witnesses
    return r


def validate(records, context, *guides):
    value = {'_uses': [], 'guidance': list(guides)}
    validate_phase({'stage': 'expression_design', 'products': value}, 'expression_design', records, [], context)
    records['expression_design']['products'] = value


def test_complete_cards_match_actual_upstream_need_and_legacy_roundtrip(tmp_path):
    _, records, context = staged('other')
    legacy = records['character_design']['products']['members'][0]
    records = {k: records[k] for k in ('type_selection', 'type_adaptation', 'world_design')}
    context['approved_cards'].append({'card_id': legacy['key'], **{k: legacy[k] for k in ('kind', 'body')}})
    material = {'members': [{'key': 'lin', 'kind': 'character', 'body': actor('other')}],
                'states': [], 'capabilities': [], '_uses': []}
    raw = {'stage': 'character_design', 'products': material}
    validate_phase(raw, 'character_design', records, [], context)
    altered = deepcopy(raw)
    altered['products']['members'][0]['body']['casting']['need_quote'] = '待作者指定'
    with pytest.raises(ValueError, match='真实前置'):
        validate_phase(altered, 'character_design', records, [], context)
    altered['products']['members'][0]['body'] = actor('other')
    altered['products']['members'][0]['body']['casting']['introducer_basis'] = '在天外见过她'
    with pytest.raises(ValueError, match='关系依据'):
        validate_phase(altered, 'character_design', records, [], context)
    altered['products']['members'][0]['body'] = actor('other')
    altered['products']['members'][0]['body']['casting']['introducer'] = 'lin'
    with pytest.raises(ValueError, match='另一位'):
        validate_phase(altered, 'character_design', records, [], context)
    shape = schema('character_design', [], narration=narration.ACCESS_POLICY, allow_requests=False)
    fields = shape['properties']['products']['properties']['members']['items']['anyOf'][0]['properties']['body']
    assert set(cast_design.PERSON_FIELDS) | {'casting'} <= set(fields['required'])
    assert 'casting' not in schema('character_design', [], narration=narration.POLICY,
        allow_requests=False)['properties']['products']['properties']['members']['items']['anyOf'][0]['properties']['body']['required']
    with Store(tmp_path, create=True, test_mode=True) as store:
        store.init_project('隔离人物卡验证')
        for key, body in [('lin', actor()), ('guest', {'name': '旧卡', 'role': '药师', 'want': '护印'})]:
            save_card(store, {'card_id': key, 'kind': 'character', 'origin': 'model', 'body': body}, None)
    with Store(tmp_path, test_mode=True) as store:
        assert read_card(store, CardRef('lin', 1))['body'] == actor()
        assert 'casting' not in read_card(store, CardRef('guest', 1))['body']
    body = actor('other')
    assert _translate(body, {'yan': CardRef('pinned-yan', 1)})['casting']['introducer'] == 'pinned-yan'
    with pytest.raises(ValueError, match='剧情作用'):
        _body('character', {**body, 'independent_goal': body['scene_function']})


def test_intro_is_placed_once_in_disclosure_order_and_requires_actual_speaker_and_audience():
    _, records, context = staged('other')
    line = beat('speech', 'yan', 'cast:lin:entry', '渡口抄录员', '我指着值班名册，告诉他这位正是渡口抄录员。', ['lin'])
    validate(records, context, line)
    with pytest.raises(ValueError, match='介绍者'):
        validate(records, context, {**line, 'narration': {**line['narration'], 'owner':'lin', 'witnesses':['yan']}})
    scene_product = records['scene_design']['products']
    next_scene = deepcopy(scene_product['members'][0])
    next_scene['key'] = 'earlier_time'
    scene_product['members'].append(next_scene)
    scene_product['chapters'][0]['scenes'].append({'card': 'earlier_time', 'index': 2, 'story_order': -10})
    scopes = narration.scene_bases(records, context)
    assert 'cast:lin:entry' in scopes['scene'] and 'cast:lin:entry' not in scopes['earlier_time']
    context['cast_previous_appearances'] = {'lin': [1, 0]}
    assert all('cast:lin:entry' not in s for s in narration.scene_bases(records, context).values())


def test_hidden_entrance_reveal_and_guard_work_on_writer_and_reviewer_projections():
    session, records, context = staged()
    intro = beat('perception', 'yan', 'cast:lin:entry', '袖里露出半枚潮印', '我看见她袖里露出半枚潮印。')
    goal = records['scene_design']['products']['members'][0]['body']['goal']
    proof = beat('action','yan','scene:scene:goal',goal,'我按住两块缺角铜片，两枚潮印吻合。',['lin'])
    reveal = beat('speech','lin','cast:lin:reveal','北汛密使','她收起铜片，终于承认自己是北汛密使。',['yan'])
    with pytest.raises(ValueError, match='略过'):
        validate(records, context, proof)
    for invalid in ([intro, reveal], [reveal, intro, proof]):
        with pytest.raises(ValueError, match='凭据'):
            validate(records, context, *invalid)
    false_proof = deepcopy(proof)
    false_proof['observable'] = '我还不能确认两枚潮印吻合。'
    with pytest.raises(ValueError, match='凭据'):
        validate(records, context, intro, false_proof, reveal)
    with pytest.raises(ValueError, match='泄露'):
        validate(records, context, {**intro, 'observable': '袖里露出半枚潮印，她就是北汛密使。'})
    validate(records, context, intro)
    checks = method_checks(session, 'scene')
    hidden = next(c for c in checks if c['id'].startswith('work:cast-identity:'))
    visible = [dict(id=c['id'], **c['binding']) for c in checks if c['profile'] != 'prose_review']
    assert hidden['method_artifact']['secret'] == '北汛密使' and '北汛密使' not in canonical(visible)
    for own in (False, True):
        assert '北汛密使' not in canonical(cast_design.writer_card(actor(), own=own))
    with pytest.raises(ValueError, match='写作包'):
        cast_design.guard_writer_package([{'card_id':'lin','body': actor()}], [], visible, {'unrelated_method': '北汛密使'})
    draft = SimpleNamespace(text='北汛密使抖了抖袖口，让我看见半枚潮印。', id='draft')
    rows = [{'id': hidden['id'], 'status': 'pass', 'evidence': []}]
    cast_design.assess_hidden([hidden], rows, draft)
    assert rows[0]['status'] == 'failed'
    validate(records, context, intro, proof, reveal)
    final = method_checks(session, 'scene')
    cast_design.guard_writer_package([{'card_id':'lin','body': actor()}], [],
        [dict(id=c['id'], **c['binding']) for c in final if c['profile'] != 'prose_review'], {'visible': '北汛密使'})
    assert next(c for c in final if c['id'].startswith('work:cast-identity:'))['method_artifact']['reveal'].endswith(':2')


@pytest.mark.parametrize('actor_key,holder,claim,predicate,revealed', [
    ('lin', 'yan', 'fact', 'identity_status:渡口', True),
    ('yan', 'yan', 'fact', 'identity_status:渡口', False),
    ('lin', 'lin', 'fact', 'identity_status:渡口', False),
    ('lin', 'READER', 'fact', 'identity_status:渡口', False),
    ('lin', 'yan', 'belief', 'identity_status:渡口', False),
    ('lin', 'yan', 'fact', '误听称呼', False),
])
def test_only_knowledge_of_this_persons_confirmed_identity_unlocks_later_scene(tmp_path, actor_key, holder, claim, predicate, revealed):
    session, records, context = staged_with_approved(tmp_path, 'yan', 'lin')
    fact = {'holder': holder, 'entity_id': actor_key, 'predicate': predicate, 'claim': claim,
            'value': {'identity':'北汛密使'}, 'story_order':0, 'disclosure_order':[0,0,0]}
    context['accepted_state'].append(fact)
    intro = beat('perception','yan','cast:lin:entry','袖里露出半枚潮印','她袖里露出半枚潮印，我认出这位北汛密使。')
    cards = [{'card_id':'lin','body':actor()}]
    visible_facts = [fact] if holder == 'yan' else []
    if revealed:
        validate(records, context, intro)
        cast_design.guard_writer_package(cards, visible_facts, [], {'known':'北汛密使'})
        assert next(c for c in method_checks(session,'scene') if c['id'].startswith('work:cast-identity:'))[
            'method_artifact']['previously_known']
    else:
        with pytest.raises(ValueError, match='泄露'):
            validate(records, context, intro)
        with pytest.raises(ValueError, match='写作包'):
            cast_design.guard_writer_package(cards, visible_facts, [], {'known':'北汛密使'})


def test_introducer_can_recognise_someone_on_scene_before_reporting_the_identity():
    _, records, context = staged('other')
    person = records['character_design']['products']['members'][-1]['body']['casting']
    person.update(introducer_source='on_scene', introducer_basis='值勤牌上有她的相片')
    records['character_design']['sha256'] = content_sha256(records['character_design']['products'])
    line = beat('speech','yan','cast:lin:entry','渡口抄录员','我把值勤牌递回去，称她为渡口抄录员。',['lin'])
    goal = records['scene_design']['products']['members'][0]['body']['goal']
    saw = beat('perception','yan','scene:scene:goal',goal,'值勤牌上有她的相片，我又对照了眉间的痣。')
    with pytest.raises(ValueError, match='先当场见证'):
        validate(records, context, line, saw)
    validate(records, context, saw, line)


def test_first_appearance_comes_from_the_branch_selected_versions_not_all_scene_rows(tmp_path):
    cards = [{'card_id':'current','version':1,'kind':'scene','body':{'pov':'lin','characters':['yan']}}]
    with Store(tmp_path, create=True, test_mode=True) as store:
        store.init_project('隔离出场顺序')
        later = store.add_chapter(3, '回述旧闸')
        early = store.add_chapter(1, '另一候选分支')
        for chapter, ident, order in [(later, 'current', 0), (early, 'retired', 5)]:
            store.add_scene(chapter.id, 2, canonical({'story': {'scene_ref': {'card_id':ident, 'version':1},
                                                                      'story_order':order}}))
        assert cast_design.previous_appearances(store, cards) == {'lin': [3,2], 'yan': [3,2]}


@pytest.mark.parametrize('existing,holder', [('lin', 'yan'), ('yan', 'yan'), ('yan', 'READER')])
def test_new_character_cannot_inherit_an_old_holders_or_subjects_identity_evidence(tmp_path, existing, holder):
    _, records, context = staged_with_approved(tmp_path, existing)
    context['accepted_state'] = [{'holder':holder, 'entity_id':'lin', 'predicate':'identity_status:渡口',
        'claim':'fact', 'value':{'identity':'北汛密使'}, 'story_order':0, 'disclosure_order':[0,0,0]}]
    assert 'fact:0' not in narration.scene_bases(records, context)['scene']
    intro = beat('perception','yan','cast:lin:entry','袖里露出半枚潮印','她袖里露出半枚潮印，我认出这位北汛密使。')
    with pytest.raises(ValueError, match='泄露'):
        validate(records, context, intro)


def test_previously_disclosed_reader_identity_is_only_allowed_inside_its_reviewed_aside(tmp_path):
    session, records, context = staged_with_approved(tmp_path, 'lin')
    context['accepted_state'] = [{'holder':'READER', 'entity_id':'lin', 'predicate':'identity_status:渡口',
        'claim':'fact', 'value':{'identity':'北汛密使'}, 'story_order':0, 'disclosure_order':[0,0,0]}]
    aside = beat('summary', None,'fact:0','北汛密使','那位北汛密使也站在队尾。')
    intro = beat('perception','yan','cast:lin:entry','袖里露出半枚潮印','她袖里露出半枚潮印，我以为是账房戳记。')
    validate(records, context, aside, intro)
    checks = method_checks(session,'scene')
    private = next(r for r in checks if r['id'].startswith('work:cast-identity:'))
    [allowed_id] = private['method_artifact']['reader_asides']
    visible = [dict(id=r['id'], **r['binding']) for r in checks if r['profile'] != 'prose_review']
    card = {'card_id':'lin','body':actor()}
    packet = {'items':[{'source':'material:'+allowed_id, 'text': '那位北汛密使也站在队尾。'}]}
    cast_design.guard_writer_package([card], [], visible, packet)
    packet['items'].append({'source':'other', 'text':'其实她是北汛密使'})
    with pytest.raises(ValueError, match='写作包'):
        cast_design.guard_writer_package([card], [], visible, packet)
    text = '那位北汛密使也站在队尾。'
    draft = SimpleNamespace(id='d', text=text)
    rows = [{'id': allowed_id, 'status':'pass', 'evidence':[{'id':'d','start':0,'end':len(text)}]},
            {'id':private['id'], 'status':'pass', 'evidence':[]}]
    cast_design.assess_hidden(checks, rows, draft)
    assert rows[-1]['status'] == 'pass'
    draft.text += '我一眼认出了北汛密使。'
    cast_design.assess_hidden(checks, rows, draft)
    assert rows[-1]['status'] == 'failed'
