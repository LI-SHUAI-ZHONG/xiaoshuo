"""Trace a two-chapter excerpt through corpus analysis, derivation and project selection."""
from copy import deepcopy
import json

import pytest

from corpus_fixture import CorpusModel, make_book, runtime, wait_job
from nw.production_methods.contracts import validate
from nw.production_methods.inputs import binding
from nw.production_methods.runtime import prompt
from nw.production_methods.sources import MethodReader
from nw.studio import corpus_jobs
from nw.studio.corpus_checks import graph_issues
from nw.studio.corpus_methods import prepare_method
from nw.studio.library import LibraryService
from nw.studio.method_recommendations import freeze_preferences, recommendations


FIRST='沈禾递给我一块铜牌，说：“我跑腿的，你替我送到北门，误班要扣钱。”我收下了牌。'
SECOND='我照铜牌背面的刻痕开门。巡长迎上来：“沈巡官，门开了！”沈禾这才摘下送件工的灰帽。'
SOURCE=f'# 第一章\n[FAKE] {FIRST}\n# 第二章\n[FAKE] {SECOND}\n'


class EncounterModel(CorpusModel):
    def generate(self,messages,**params):
        result=super().generate(messages,**params)
        payload=self.calls[-1]
        raw=json.loads(result.text)
        if payload['phase']=='survey' and raw['characters']:
            person=raw['characters'][0]
            person['name']='我'
            raw['characters'].append({**person,'name':'沈禾','id':person['id']+'_courier'})
        if payload['phase']=='detail':
            quote=FIRST if FIRST in payload['source_text'] else SECOND
            evidence=raw['evidence'][0]
            start=SOURCE.index(quote)
            evidence.update(quote=quote,start=start,end=start+len(quote))
            raw['events'][0]['characters']=[p['id'] for p in payload['known_characters']]
        if payload['phase']=='relations' and payload['domain'] in ('chapter_progress','cast_entry'):
            observation=raw['threads'][0]
            if payload['domain']=='chapter_progress':
                observation['details'].update(entry_condition='北门的牌没有送到',turn='沈禾委托，我答应代送',
                    change='我从旁观者成为持牌送件人',knowledge_change='我只听见她自称跑腿',
                    next_pressure='我要抵达北门',later_use='第二章我实际借第一章收下的牌开门')
                raw['links'][0].update(kind='enables',certainty='observed')
            else:
                observation['characters']=[p['id'] for p in payload['characters'] if p['name']=='沈禾']
                observation['details'].update(plot_need='有人需要将牌交到北门',position='',
                    function='交接凭证，稍后以巡官身份接收结果',own_reason='她说误班会扣钱，是否出于这个动机尚不明',
                    encounter='她提出代送，我接了牌',identity_access='起初我只听到她自称跑腿',claim_status='attributed',
                    later_reveal='第二章巡长当面称她为沈巡官，她摘下灰帽')
                raw['links'][0].update(kind='reveals',certainty='observed')
        if payload['phase']=='methods':
            body=raw['methods'][0]['body']
            assert {p['name'] for p in payload['participants']}=={'我','沈禾'}
            chapter=payload['thread']['domain']=='chapter_progress'
            task='chapter_outline' if chapter else 'character_arc'
            stage='plot_design' if chapter else 'character_design'
            body.update(tasks=[task],title='前章所得怎样成为行动条件' if chapter else '一次交接怎样引入有隐情的角色')
            body['prerequisites'][0].update(input_kind='parent_outline' if chapter else 'world_design',
                                            artifact='已批准的章前问题' if chapter else '已批准的职务和约束')
            body['outputs'][0].update(stage=stage,field='members',artifact_kind='chapter' if chapter else 'character',
                                      description='章首章末实际变化' if chapter else '角色自己的目的与当场职责')
        result.text=json.dumps(raw,ensure_ascii=False)
        return result


def test_encounter_and_progress_become_distinct_evidenced_design_methods(tmp_path,monkeypatch):
    library=LibraryService(tmp_path)
    model=EncounterModel()
    monkeypatch.setattr(library,'_corpus_runtime',lambda:(runtime(),model))
    book=make_book(library,SOURCE)['id']
    job=library.start_corpus_job(book,{'options':{'extent':'excerpt','note':'[FAKE] 两章局部'}})
    finished=wait_job(library,book,job['id'])
    assert finished['status']=='completed',finished['error']
    structure=library.review_corpus(book,{'version':1,'decision':'approve','note':'[FAKE] 仅核对该片段',
                                          'accept_limitations':True})
    assert all(ch['chapter_progress']==['T_chapter_progress'] and ch['cast_entry']==['T_cast_entry']
               for ch in structure['statistics']['chapter_ranges'])
    partial=deepcopy(structure['body'])
    progress=next(t for t in partial['threads'] if t['domain']=='chapter_progress')
    progress['node_ids']=progress['node_ids'][:1]
    progress['details']['later_use']=''
    partial['links']=[l for l in partial['links'] if l['thread_id']!=progress['id']]
    gaps=graph_issues(partial,len(SOURCE),structure['coverage'])
    assert any(r['severity']=='warning' and '共1章' in r['message'] for r in gaps)
    broken=deepcopy(structure['body'])
    thread=next(t for t in broken['threads'] if t['domain']=='cast_entry')
    broken['links']=[link for link in broken['links'] if link['thread_id']!=thread['id']]
    assert any('揭晓两处' in row['message'] and row['severity']=='error' for row in graph_issues(broken,len(SOURCE)))
    thread['details']['later_reveal']=''
    assert not any(row['severity']=='error' for row in graph_issues(broken,len(SOURCE)))
    swapped=deepcopy(structure['body'])
    later=next(e for e in swapped['events'] if e['id']==thread['node_ids'][-1])
    later['characters']=[p for p in later['characters'] if p not in thread['characters']]
    assert any('揭晓两处' in row['message'] for row in graph_issues(swapped,len(SOURCE)))
    subject=next(p for p in swapped['characters'] if p['id'] in thread['characters'])
    alias={**subject,'id':'later_name','canonical_id':subject['id'],'name':'沈巡官','evidence_ids':later['evidence_ids']}
    swapped['characters'].append(alias)
    later['characters'].append(alias['id'])
    assert not any(row['severity']=='error' for row in graph_issues(swapped,len(SOURCE)))

    job=library.start_corpus_job(book,{'kind':'methods','options':{'thread_ids':['T_chapter_progress','T_cast_entry']}})
    finished=wait_job(library,book,job['id'])
    assert finished['status']=='completed',finished['error']
    methods=library.list_methods()['methods']
    assert len(methods)==2
    for method in methods:
        library.review_method(method['id'],{'version':1,'decision':'approve','note':'[FAKE] 核对用途与引文'})
    reader=MethodReader(tmp_path)
    for method in methods:
        body=method['body']
        chapter=body['tasks']==['chapter_outline']
        slot,stage=('structure','plot_design') if chapter else ('character','character_design')
        result=recommendations(reader,slot,['GENRE_XUANYI'],[])['recommendations']
        assert [m['id'] for m in result]==[method['id']]
        pin=reader.snapshot(reader.get_method(method['id']))
        reader.verify(pin)
        if not chapter:
            assert pin['instance']['threads'][0]['details']['claim_status']=='attributed'
        kind=body['prerequisites'][0]['input_kind']
        assert binding(pin,stage,{})['missing']
        spec=binding(pin,stage,{kind:{'status':'approved','kind':kind,'value':'[FAKE] 本项目批准需求'}})
        assert not spec['missing']
        plan={'target':{'stage':stage},'selected':[spec]}
        assert '角色承担的工作' in prompt(plan)
        card={'key':'ferry','kind':'chapter' if chapter else 'character','body':{'goal':'[FAKE] 帮人把还船的单子送去销账'}}
        place={'path':['members',0,'body','goal'],'value':card['body']['goal']}
        output={'key':'o1','placements':[place],'scene_guidance':[]}
        application={'method_id':pin['id'],'operations':[{'key':'p1','explanation':'[FAKE] 从本书销账需要设计愿意帮忙的船工和凭据'}],
                     'outputs':[output]}
        products={'members':[card],'_method_applications':[application],'_method_receipts':[]}
        validate(products,stage,plan,[],set())
        output['placements']=[{'path':['members',0,'key'],'value':'ferry'}]
        with pytest.raises(ValueError,match='卡片设计内容'):
            validate(products,stage,plan,[],set())
        assert {e['quote'] for e in body['evidence']}=={FIRST,SECOND}
        basis=method['structure_origin']['basis']
        with pytest.raises(ValueError,match='承接关系|揭示关系'):
            prepare_method(library,structure,{'body':body,'basis':{**basis,'link_ids':[]}})
        with pytest.raises(ValueError,match='逐个对应细拆事件'):
            prepare_method(library,structure,{'body':{**body,'evidence':body['evidence'][:1]},'basis':basis})
        if not chapter:
            with pytest.raises(ValueError,match='摘录'):
                prepare_method(library,structure,{'body':{**body,'scopes':['chapter','book']},'basis':basis})
            # An identity disclosure may belong to plot_design.information even when chosen in the character slot.
            disclosure=deepcopy(body)
            disclosure['tasks']=['information']
            disclosure['outputs'][0].update(stage='plot_design',field='reader_plan',artifact_kind='stage_product')
            changed=library.save_method({'body':disclosure,'expected_version':1},method['id'])
            library.review_method(changed['id'],{'version':2,'decision':'approve','note':'[FAKE] 仍依据出场原句'})
            choices=recommendations(reader,'character',['GENRE_XUANYI'],[])['recommendations']
            assert choices[0]['uses'][0]['stage']=='plot_design'
            pins=freeze_preferences(reader,[{'slot':'character','id':changed['id'],'version':2}],['GENRE_XUANYI'])
            assert pins[0]['structure_origin']['observation_domains']==['cast_entry']

        scene={'key':'dock','kind':'scene','body':{'goal':'归还失单'}}
        receipt={'id':'handoff','operation':'[FAKE] 让收到船单的渡工当着领班的面决定核实凭据',
                 'placements':[{'path':['members',0,'body','goal'],'value':'归还失单'}],
                 'scene_guidance':[{'scene':'dock','observable':'[FAKE] 渡工看到船单后收起手中的锁链',
                                    'check':'[FAKE] 读者能指出谁见过凭据及怎样回应'}]}
        incoming=[{'id':'handoff','method':pin,'output':{'scene_guidance':[]}}]
        delivered={'members':[scene],'_method_receipts':[receipt]}
        validate(delivered,'scene_design',{'target':{},'selected':[]},incoming,{'dock','inn'})
        receipt['scene_guidance'][0]['scene']='inn'
        with pytest.raises(ValueError,match='实际采用'):
            validate(delivered,'scene_design',{'target':{},'selected':[]},incoming,{'dock','inn'})


def test_v3_job_keeps_its_original_domains_and_budget(tmp_path,monkeypatch):
    library=LibraryService(tmp_path)
    model=CorpusModel()
    model.fail_at=2
    monkeypatch.setattr(library,'_corpus_runtime',lambda:(runtime(),model))
    current=corpus_jobs.empty_document
    monkeypatch.setattr(corpus_jobs,'empty_document',lambda *args:{**current(*args),'schema_version':3})
    book=make_book(library)['id']
    job=library.start_corpus_job(book,{'options':{'extent':'complete','note':'[FAKE] 旧版','max_calls':15}})
    assert wait_job(library,book,job['id'])['status']=='paused'
    monkeypatch.setattr(corpus_jobs,'empty_document',current)
    model.fail_at=None
    library.control_corpus_job(book,job['id'],{'action':'resume','retry_failed':True})
    done=wait_job(library,book,job['id'])
    assert done['status']=='completed' and done['calls_used']==15
    assert len(library.get_corpus(book)['body']['domains'])==9
