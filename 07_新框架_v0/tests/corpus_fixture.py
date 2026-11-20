"""[FAKE] Corpus observations for isolated engineering tests, never formal books."""
import json
import time
from types import SimpleNamespace

from nw.llm.base import GenResult
from nw.studio.corpus_catalog import DETAILS, OVERVIEW

SOURCE='# 第一章\n[FAKE] 甲提出问题，并记录一条线索。\n# 第二章\n[FAKE] 甲核对线索，给出回应并确认结果。\n'


def make_book(library, text=SOURCE):
    book=library.import_book({'filename':'[FAKE] corpus.md','title':'[FAKE] 多层结构测试','text':text})
    if book['status']=='pending_review':
        book=library.review_book(book['id'],{'types':['GENRE_XUANYI'],'decompose':False})
    return book


def runtime():
    return SimpleNamespace(provider='test-only',model='[FAKE] isolated-corpus',base_url='http://test-only.invalid',
                           timeout=1,params={})


def wait_job(library,book,ident,timeout=10):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        result=library.get_corpus_job(book,ident)
        if result['status'] not in ('running','pending'):
            worker=library._tasks.get(ident)
            if worker:worker.join(timeout=2)
            return library.get_corpus_job(book,ident)
        time.sleep(.01)
    raise AssertionError('isolated corpus job did not finish')


def start_analysis(library,monkeypatch,provider=None,**options):
    provider=provider or CorpusModel()
    monkeypatch.setattr(library,'_corpus_runtime',lambda:(runtime(),provider))
    book=make_book(library)
    result=library.start_corpus_job(book['id'],{'options':{'extent':'complete','note':'[FAKE] 仅测试完整性声明，不是真实完整作品',**options}})
    return book,wait_job(library,book['id'],result['id']),provider


def thread(domain,events,character,evidence,status='resolved'):
    return {'id':'T_'+domain,'domain':domain,'title':'[FAKE] '+domain,'status':status,
        'characters':[character] if character else [],'node_ids':[e['id'] for e in events],
        'initial_state':'[FAKE] 前态','final_state':'[FAKE] 后态','explanation':'[FAKE] 有多处测试证据，不代表文学判断',
        'details':{key:'[FAKE] '+label for key,label in DETAILS[domain].items()},'evidence_ids':list(evidence)}


class CorpusModel:
    name='test-only'
    def __init__(self):self.calls=[];self.fail_at=None;self.invalid_at=None;self.on_call=None

    def generate(self,messages,**params):
        payload=json.loads(messages[-1]['content']);self.calls.append(payload)
        if self.on_call:self.on_call(payload)
        if self.fail_at==len(self.calls):raise RuntimeError('[FAKE] transport outcome unknown')
        if self.invalid_at==len(self.calls):return GenResult('{"invented":true}','complete',{},'[FAKE]',{})
        phase=payload['phase'];prefix=payload.get('prefix','X')
        if phase in ('survey','detail'):
            known=payload['known_characters'];person=known[0]['id'] if known else prefix+'_C1'
            character=[] if known else [{'id':person,'name':'[FAKE] 甲','canonical_id':None,'role':'[FAKE] 核对者','goal':'[FAKE] 找到依据',
                'initial_state':'[FAKE] 未核对','final_state':'[FAKE] 核对完成','evidence_ids':[prefix+'_E1']}]
            span=payload['span'];unit=payload['unit'];quote=payload['source_text'][:400]
            evidence={'id':prefix+'_E1','start':span['start'],'end':span['start']+len(quote),
                'quote':quote,'explanation':'[FAKE] 当前原文片段'}
            scenes=[];unit_id=unit['id'];parents=[]
            if phase=='detail':
                unit_id=prefix+'_S1';parents=[e['id'] for e in payload['overview_events']]
                scenes=[{'id':unit_id,'level':'scene','title':'[FAKE] 观察场景','parent_id':unit['id'],
                    'start':span['start'],'end':span['end'],'boundary_basis':'analyst_inference','summary':'[FAKE] 测试场景'}]
            event={'id':prefix+'_Event1','unit_id':unit_id,'granularity':'overview' if phase=='survey' else 'detail',
                'parent_event_ids':parents,'story_order':span['start'],'summary':'[FAKE] 当前有证据事件','characters':[person],
                'goal':'[FAKE] 核对','conflict':'[FAKE] 信息不足','choice':'[FAKE] 选择检查','cost':'[FAKE] 测试成本',
                'result':'[FAKE] 取得回应','information_before':'[FAKE] 未确认','information_after':'[FAKE] 已确认',
                'emotion_before':'[FAKE] 存疑','emotion_after':'[FAKE] 明确','evidence_ids':[prefix+'_E1']}
            raw={'evidence':[evidence],'characters':character,'events':[event],'units':scenes}
        elif phase in ('overview','relations'):
            events=payload['events'];domain=payload.get('domain') or 'main_plot'
            refs=list(dict.fromkeys(eid for e in events for eid in e['evidence_ids']))
            person=events[0]['characters'][0]
            row=thread(domain,events,person,refs,'resolved' if payload['last_window'] else 'open')
            kind={'main_plot':'causes','subplot':'crosses','character_arc':'changes_character','hook':'responds',
                'foreshadow':'pays_off','information':'reveals','pacing':'emotional_shift'}[domain]
            available={e['id']:e for e in [*payload['frontier_events'],*events]}
            first=events[0];last=events[-1];links=[]
            prior=next((t for t in payload['open_threads'] if t['domain']==domain),None)
            if len(events)==1 and prior:
                previous=[available[k] for k in prior['node_ids'] if k in available and k!=last['id']
                          and available[k]['story_order']<=last['story_order']]
                if previous:first=max(previous,key=lambda e:e['story_order'])
            if first['id']==last['id'] and domain in ('hook','foreshadow') and payload['last_window']:
                row['status']='uncertain'
            if first['id']!=last['id']:
                links=[{'id':prefix+'_L1','kind':kind,'source':first['id'],'target':last['id'],'thread_id':row['id'],
                    'explanation':'[FAKE] 测试多处证据链接','certainty':'inferred',
                    'evidence_ids':list(dict.fromkeys([*first['evidence_ids'],*last['evidence_ids']]))}]
            raw={'threads':[row],'links':links}
            if phase=='overview':raw['overview']={k:'[FAKE] '+v for k,v in OVERVIEW.items()}
            elif payload['last_window']:
                raw['domains']=[{'domain':domain,'status':'observed','explanation':'[FAKE] 已核对此测试范围','evidence_ids':refs}]
        else:
            evidence=[{k:e[k] for k in ('book_id','start','end','quote','explanation')} for e in payload['evidence']]
            raw={'methods':[{'body':{'title':'[FAKE] 问题接力方法','tasks':['hook'],'scopes':['chapter'],'type_tags':payload['confirmed_types'],
                'applicability':['[FAKE] 已有剧情方向和前置'],'prerequisites':[{'key':'i1','input_kind':'plot_design','artifact':'[FAKE] 方向','requirement':'[FAKE] 已批准'}],
                'operations':[{'key':'p1','instruction':'[FAKE] 核对问题与回应','input_keys':['i1'],'output_keys':['o1']}],
                'outputs':[{'key':'o1','stage':'plot_design','field':'reader_plan','artifact_kind':'stage_product','description':'[FAKE] 问题及披露安排'}],
                'downstream':[{'output_key':'o1','consumer':'scene_design','usage':'[FAKE] 安排场景回应'}],
                'acceptance':[{'output_key':'o1','check':'[FAKE] 核对实际对应','evidence_required':'[FAKE] 场景与正文位置'}],
                'evidence':evidence,'non_applicability':['[FAKE] 缺前置时先补设计']},
                'basis':{'thread_ids':[payload['thread']['id']],'event_ids':payload['thread']['node_ids'],
                         'link_ids':[l['id'] for l in payload['links']],'explanation':'[FAKE] 仅测试完整结构到方法的来源记录'}}]}
        return GenResult(json.dumps(raw,ensure_ascii=False),'complete',{'test_only':True},'[FAKE] request',{'test_only':True})
