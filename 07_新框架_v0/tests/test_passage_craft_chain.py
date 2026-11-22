"""Exercise independent source techniques via normal import, chapter planning and writing."""
from copy import deepcopy
from dataclasses import asdict, replace
import json

import pytest

from nw.context.prior_prose import _reviewed_paragraphs
from nw.materials import narration_review, passage_craft, situated_passage
from nw.materials.evidence import scene_materials
from nw.materials.template_support import events
from nw.novel_flow import JobRequest, resume_job, start_job
from nw.passage_catalog import OBSERVATIONS
from nw.production_methods.selection import verify_sources
from nw.store import Store
from nw.story_state import adopt_story
from nw.story_delta import draft_ref
from nw.studio.corpus_catalog import corpus_catalog
from nw.studio.corpus_checks import graph_issues
from nw.studio.corpus_contract import normalize_document
from nw.studio.library import LibraryService
from nw.studio.production_inputs import freeze_wizard, governance
from nw.task_models import Budget
from story_fixture import baseline
from test_material_phase_flow import PhaseModel, template_catalog
from test_material_stage_roundtrip import StageModel
from test_material_workflow import choose
from test_novel_flow import author, config
import test_studio_corpus_passages as source_fixture
from test_material_action_review import draft, span


SOUND = '檐水敲上铁皮，桌边那截灯芯噼啪作响。'
OPERATION = '选择现场一个真实可闻的声音，让读者由它体会四周的安静。'


class SoundBook(source_fixture.SequenceModel):
    def generate(self, messages, **params):
        result = super().generate(messages, **params)
        phase = self.calls[-1]['phase']
        raw = json.loads(result.text)
        if phase == 'detail':
            assert 'sensory_evidence' in messages[0]['content']
            seq = raw['threads'][0]['details']['passage_sequence']
            sound = seq['beats'][1]
            seq.update(kind='sensory_evidence', condition='需要听见现场的陌生动静', boundary='观察者不在可听范围',
                       beats=[{**sound,'role':'detail'}])
        if phase == 'methods':
            raw['methods'][0]['body']['operations'][0]['instruction'] = OPERATION
        return replace(result,text=json.dumps(raw,ensure_ascii=False))


class SoundNovel(PhaseModel, StageModel):
    def __init__(self):
        super().__init__('fixture')
        self.reviews = 0

    def generate(self, messages, **params):
        result = super().generate(messages, **params)
        data = json.loads(messages[-1]['content'])
        stage = data.get('stage')
        if stage in ('plot_design','scene_design','expression_design') and data['scope']!='book':
            raw = json.loads(result.text)
            out = raw['products']
            if stage == 'plot_design':
                e = out['event_nodes'][0]
                out['event_techniques'] = [{'kind':'sensory_evidence','event':e['id'],'need_quote':e['goal']}]
            elif stage == 'scene_design':
                ref, = data['craft_candidates']
                selected, = out['selected_events']
                quote = events(data['inputs'])[selected['event']]['goal']
                need = {**selected,'kind':'sensory_evidence','need_quote':quote,'reason':'听得见灯芯的响声，是查验时现场安静的凭据。'}
                out['situated_needs'] = [need]
                out['craft_choices'] = [{**need,'source_ref':ref['ref']}]
            else:
                ref, = data['selected_craft_methods']
                assert ref['operations'] == [OPERATION]
                need, = data['situated_needs']
                guide = out['guidance'][-1]
                out['guidance'].append({**guide,'observable':SOUND,
                    'narration':{**guide['narration'],'mode':'perception','effect':'读者能听出屋里很静'}})
                n = len(out['guidance'])
                out['situated_beats'] = [{'scene':need['scene'],'kind':'sensory_evidence','marks':[
                    {'role':'sensation','beat':n,'quote':'灯芯噼啪作响'},{'role':'impression','beat':n,'quote':'屋里很静'}]}]
                out['craft_applications'] = [{'scene':need['scene'],'source_ref':ref['ref'],'operation':OPERATION,'beat':n,
                    'boundary_check':f"{need['need_quote']}时人就在桌旁，能听到灯芯的声音。"}]
            return replace(result,text=json.dumps(raw,ensure_ascii=False))
        if 'material_review' in data:
            self.reviews += 1
            raw = json.loads(result.text)
            current = data['draft']['text']
            check, = [c for c in data['material_review']['checks'] if c.get('craft_sources')]
            assert check['craft_sources'][0]['operation'] == OPERATION
            if self.reviews > 1:
                row = next(r for r in raw['material_checks'] if r['id'] == check['id'])
                start = current.index(SOUND)
                row.update(reason='【感官线索】灯芯噼啪作响\n【印象依据】灯芯噼啪作响\n【形成印象】近处细微的声音清楚可辨，读者才觉出屋里很静。'
                           '\n【来源1落点】灯芯噼啪作响\n【来源1适用】人就在桌旁，近处的细响才衬得出静。',
                           evidence=[{**data['material_review']['draft'],'start':start,'end':start+len(SOUND),'quote':SOUND}])
            return replace(result,text=json.dumps(raw,ensure_ascii=False))
        if 'items' in data or data.get('review'):
            package = data.get('context',data)
            items = [i['text'] for i in package['items'] if 'situated_roles' in i['text']]
            assert items and OPERATION not in messages[-1]['content']
            if data.get('review'):
                assert any(r.get('fix')==situated_passage.FIXES['situated_evidence'] for r in data['review']['material_checks'])
            return replace(result,text='[FAKE] 沈砚走进档案室核验旧印。'+(SOUND if self.reviews else '屋里很安静。'))
        if '{"operations"' in messages[0]['content']:
            raw = json.loads(result.text)
            for op in raw['operations']:
                op.setdefault('expected_old',None)
                op['evidence'][0]['end'] = data['draft']['text'].index('。')+1
            return replace(result,text=json.dumps(raw,ensure_ascii=False))
        return result


def test_current_approved_single_technique_reaches_prose_without_either_old_sequence(tmp_path,monkeypatch):
    template_catalog(tmp_path)
    lib = LibraryService(tmp_path)
    wizard = freeze_wizard({'title':'柜前的旧印','idea':'查验柜前旧印','genre_ids':['GENRE_XUANYI']},lib)
    monkeypatch.setattr(source_fixture,'SequenceModel',SoundBook)
    book, structure, method = source_fixture.start_passage_method(lib,monkeypatch,'focus_relay')
    refs = governance(wizard,library=lib)['world_design']['passage_references']
    assert len(refs)==1 and refs[0]['kind']=='sensory_evidence' and refs[0]['method_id']==method['id']
    source = lib._book_text(lib._staging_row(book))
    wrong = deepcopy(structure['body'])
    sample = next(r for r in wrong['threads'] if r['details'].get('passage_sequence'))
    cited = sample['details']['passage_sequence']['beats'][0]['evidence_id']
    quote = next(e for e in wrong['evidence'] if e['id']==cited)
    wrong['evidence'].append({**quote,'id':'Aside','text_role':'reader_address'})
    issues = graph_issues(normalize_document(wrong,source),len(source),content=source)
    assert any(i['field']=='events' and '题外' in i['message'] for i in issues)
    folder = tmp_path/'work'
    with Store(folder,create=True,test_mode=True) as store:
        store.init_project('[FAKE] 隔离章场');store.add_brief(wizard['idea']);adopt_story(store,baseline(),{})
        runtime = replace(config(store),source_driven=True)
        model = SoundNovel()
        design = start_job(store,JobRequest('design',budget=Budget(44,140000,4800),
                           governance_inputs={'world_design':{'passage_references':refs}})).id
        result = resume_job(store,design,model,runtime)
        assert result.step=='plan:book:confirm',result.reason
        result = resume_job(store,design,model,runtime,choose)
        assert result.step=='plan:chapter:confirm',result.reason
        result = resume_job(store,design,model,runtime,choose)
        assert result.status=='DONE',result.reason
        scene, = store.list('scene')
        writing = start_job(store,JobRequest('write',scene_ids=[scene.id],budget=Budget(16,140000,4800,1))).id
        done = resume_job(store,writing,model,runtime,author())
        assert done.status=='DONE' and model.reviews==2,done.reason
    with Store(folder,test_mode=True) as reopened:
        assert SOUND in reopened.get('draft',reopened.accepted(scene.id).draft_id).text
        session = scene_materials(reopened,scene.id)['work_session']
        verify_sources(reopened,session)
        lib.review_book(book,{'decision':'reject','note':'隔离验收撤回来源'})
        with pytest.raises(ValueError,match='STALE_PROJECT_METHOD'):
            verify_sources(reopened,session)


def test_every_decomposable_craft_has_one_production_owner():
    kinds = [k for m in passage_craft.MODULES for k in m.KINDS]
    assert len(kinds)==len(set(kinds))
    assert set(kinds)==set(OBSERVATIONS)
    assert set(corpus_catalog()['passage_sequences'])==set(kinds)|{'procedure_branch','focus_relay'}
    assert set(corpus_catalog()['passage_sequences'])==set(passage_craft.EVENT_KINDS)


@pytest.mark.parametrize('kind',['focus_relay','procedure_branch'])
def test_chapter_can_require_an_ordered_passage_without_a_reference_book(kind):
    from test_passage_sequence import EVENTS, expression, scene
    from nw.materials import passage_sequence
    plans = deepcopy(EVENTS)
    plot = plans['plot_design']['products']
    event, = plot['event_nodes']
    plot['event_techniques'] = [{'event':event['id'],'kind':kind,'need_quote':event['goal']}]
    passage_craft.validate('plot_design',plot,plans,{})
    chosen = scene(kind)
    with pytest.raises(ValueError,match='连续安排'):
        passage_craft.validate('scene_design',{**chosen,'passage_choices':[]},plans,{})
    passage_craft.validate('scene_design',chosen,plans,{})
    passage_sequence.validate_choices(chosen,plans,[])
    plans['scene_design'] = {'products':chosen}
    passage_craft.validate('expression_design',expression(kind),plans,{})
    passage_sequence.validate_sequences(expression(kind),chosen,[])


def test_source_review_must_locate_its_own_technique_on_a_shared_beat(draft):
    draft = replace(draft,text='窗边有风声，众人停笔。')
    check = {'id':'work:narration:s:1',
             'craft_sources':[{'kind':'sensory_evidence','operation':OPERATION,'boundary_check':'在窗边听见'}],
             'situated_checks':[{'kind':'sensory_evidence','role':'sensation'}],
             'people_design':[{'kind':'authority_response','role':'reaction'}]}
    for quote, status in [('众人停笔','failed'),('有风声','pass')]:
        row = {'status':'pass','reason':f'【感官线索】有风声\n【他人反应】众人停笔\n【来源1落点】{quote}\n【来源1适用】风声近得可辨，窗边的人能听见。',
               'evidence':[span(draft,0,len(draft.text))]}
        passage_craft.assess_sources([check],{check['id']:row},draft.id)
        assert row['status']==status


def test_method_can_land_on_the_earlier_half_of_a_pacing_change(draft):
    draft = replace(draft,text='其他人依次照办。轮到掌柜，他却把笔搁下了。')
    early = '其他人依次照办。'
    first = {'id':'before','craft_sources':[{'kind':'pace_switch','scene':'desk','beat':1,'operation':'概括重复办理',
                                             'boundary_check':'只有照章办理的人可以合写'}]}
    later = {'id':'after','paragraph_effects':[{'scene':'desk','from_beat':1,'kind':'pace_switch'}]}
    reason = '【来源1落点】依次照办\n【来源1适用】先前的几人照章办完，掌柜搁笔后才需要详看。'
    rows = {'before':{'status':'pass','reason':reason,'evidence':[span(draft,0,len(early))]},
            'after':{'status':'pass','reason':'【详略前】依次照办\n【详略后】把笔搁下','evidence':[span(draft,len(early),len(draft.text))]}}
    passage_craft.assess_sources([first,later],rows,draft.id)
    assert rows['before']['status']=='pass'
    rows['after']['reason'] = '【详略前】府上另有规矩'
    passage_craft.assess_sources([first,later],rows,draft.id)
    assert rows['before']['status']=='failed'


def test_shared_beat_keeps_the_receipt_factual_and_the_next_step_pending(draft):
    receipt, promise = '他把领件单收入袋中。','明早才轮到他领卷。'
    draft = replace(draft,text=receipt+promise)
    check = {'id':'work:narration:s:1','method_artifact':{'narration':{'owner':'clerk','mode':'action','time':'present'}},
             'binding':{'observable':json.dumps({'owner':'clerk','witnesses':['buyer']})},'reported_only':False,
             'passage_step':{'status':'pending'},'paragraph_pending':True,
             'paragraph_effects':[{'kind':'local_handoff','status':'eligible'}]}
    row = {'id':check['id'],'status':'pass','evidence':[span(draft,0,len(draft.text))],
           'reason':f'“{promise}”留下明早才能进行的手续。\n【已获条件】{receipt}\n【尚待兑现】{promise}'}
    limits = narration_review.reader_spans([check],[row],draft)
    first, second = sorted(limits,key=lambda r:r['start'])
    assert first['end']==len(receipt) and not first['reported_only']
    assert second['start']==len(receipt) and second['passage_status']=='pending'
    def claim(holder, bounds):
        op = {'claim':'fact','predicate':'receipt','holder':holder,'evidence':[bounds]}
        narration_review.check_state_audience([op],limits)
    claim('buyer',first)
    with pytest.raises(ValueError,match='MATERIAL_EVIDENCE'):
        claim('buyer',second)
    with pytest.raises(ValueError,match='MATERIAL_EVIDENCE'):
        claim('absent',first)


def test_prior_chapter_hides_private_paragraphs_without_hiding_public_corroboration(draft):
    public, private = '柜前的人都听见了报号。','直到那天，他仍未告诉旁人自己认出了旧签。'
    draft = replace(draft,text=public+'\n'+private)
    ident = 'work:narration:desk:1'
    visible = {'audience':'reader_only','owner':None}
    check = {'id':ident,'method_artifact':{'narration':{'owner':None,'time':'past'}},
             'binding':{'observable':json.dumps(visible)},'people_design':[{'role':'judgment'}]}
    row = {'id':ident,'status':'pass','evidence':[span(draft,0,len(draft.text))],
           'reason':'这一段向读者交代了没有说出口的认识。\n【判断原句】自己认出了旧签'}
    assert _reviewed_paragraphs(draft,{ident:visible},{'recommendation':'pass','material_checks':[row]},
                                {'draft':asdict(draft_ref(draft)),'checks':[check]})==[(len(public)+1,len(draft.text))]
