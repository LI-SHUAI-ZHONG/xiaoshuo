"""Isolated, manually reviewed reference fixtures exercise the real library and planning input."""
from copy import deepcopy
import json

from nw.studio.cast_samples import genre_cast_samples
from nw.studio.corpus_catalog import DOMAINS, FIELDS, OVERVIEW
from nw.studio.corpus_cast import cast_distribution
from nw.studio.corpus_index import empty_document
from nw.studio.library import LibraryService
from nw.studio.production_inputs import freeze_wizard, governance


def add_reference(library, title, types, extent='complete', *, approve=True):
    passages = ['阿霜递过路引，老许接了，又提到从未见面的秦师傅。', '被称作小霜的阿霜独自登舟。']
    text = f'# 第一章 {title}\n{passages[0]}\n# 第二章\n{passages[1]}'
    book = library.import_book({'title':title, 'filename':title+'.md', 'text':text})['id']
    library.review_book(book, {'types':types, 'decompose':False})
    doc = empty_document(text, extent=extent, note='隔离测试核过来源范围')
    doc['overview'] = dict.fromkeys(OVERVIEW, '送出路引再登舟')
    for no, passage in enumerate(passages, 1):
        start = text.index(passage)
        doc['evidence'].append({'id':f'q{no}', 'start':start, 'end':start+len(passage),
                                'quote':passage, 'explanation':'本章行动和称呼的依据'})
    for key,name,alias,quote in [('a','阿霜',None,'q1'),('x','小霜','a','q2'),('b','老许',None,'q1'),('c','秦师傅',None,'q1')]:
        doc['characters'].append({**dict.fromkeys(FIELDS['characters'],''), 'id':key, 'name':name,
                                  'canonical_id':alias, 'evidence_ids':[quote]})
    for key, chapter, level, people, quote in [('o',1,'overview',[],'q1'), ('e1',1,'detail',['a','b'],'q1'),
                                                ('e2',2,'detail',['x'],'q2')]:
        doc['events'].append({**dict.fromkeys(FIELDS['events'],''), 'id':key, 'unit_id':f'c{chapter:05}',
                              'granularity':level, 'parent_event_ids':[] if key=='o' else ['o'], 'story_order':chapter,
                              'summary':passages[chapter-1], 'result':'交出凭证' if chapter==1 else '登船',
                              'characters':people, 'evidence_ids':[quote]})
    for person,event,presence,standing,function in [('a',1,'onstage','protagonist','driver'),
            ('b',1,'onstage','supporting','handoff'),('c',1,'mentioned','unknown','unknown'),
            ('x',2,'onstage','protagonist','driver')]:
        q = f'q{event}'
        doc['threads'].append({'id':'r'+person, 'domain':'cast_roster', 'title':'核对'+person,'status':'resolved',
            'characters':[person], 'node_ids':[f'e{event}'], 'initial_state':'进入事件','final_state':'登记称呼',
            'explanation':'对照本段原句','evidence_ids':[q], 'details':{'presence':presence,
            'subject_kind':'individual','standing':standing,'function_kind':function,'chapter_function':passages[event-1],
            'appearance_evidence':q,'standing_evidence':q if standing!='unknown' else ''}})
    doc['domains']=[{'domain':key,'status':'observed' if key=='cast_roster' else 'uncertain',
                     'explanation':'只核对了本次两章人物证据','evidence_ids':['q1']} for key in DOMAINS]
    library.save_corpus(book, {'expected_version':0,'body':doc,'reviewed_units':['c00001','c00002']})
    if approve:
        library.review_corpus(book, {'version':1,'decision':'approve','note':'已按测试文本逐项核对','accept_limitations':True})
    return book


def test_unique_people_and_genre_ranges_survive_review_and_reopen(tmp_path):
    library = LibraryService(tmp_path)
    genre = ['GENRE_XUANYI']
    whole = add_reference(library,'渡口',genre)
    add_reference(library,'摘录',genre,'excerpt')
    add_reference(library,'未批准的稿',genre,approve=False)
    library = LibraryService(tmp_path)
    row = library.get_corpus(whole)
    stats = row['statistics']['cast_distribution']
    assert (stats['unique_count'], stats['mentioned_only_count']) == (2,1)
    assert stats['positions'] == {'protagonist':1,'supporting':1}
    assert [s['appearing_count'] for s in stats['chapters']] == [2,1]
    assert [s['first_count'] for s in stats['chapters']] == [2,0]
    assert stats['chapters'][1]['returning_count'] == 1 and stats['chapters'][1]['appearing_ids'] == ['a']
    sample = genre_cast_samples(library, genre)
    assert (sample['sample_count'],sample['complete_count'],sample['chapter_count']) == (2,1,4)
    assert sample['book_range'] == {'min':2,'max':2}
    assert sample['function_ranges']['handoff'] == {'min':1,'max':1}
    assert sample['chapter_bands']['ending']['first'] == {'min':0,'max':0}
    assert sample['chapter_bands']['opening']['chapter_count'] == 1
    assert sample['position_labels']['protagonist']=='主角'
    wizard = freeze_wizard({'title':'空印','idea':'追查空印','genre_ids':genre},library)
    frozen = governance(wizard)['world_design']['cast_sample_reference']
    assert frozen['book_range']==sample['book_range'] and len(frozen['sources'])==2
    library.review_book(whole, {'decision':'reject'})
    refreshed = governance(wizard,library=library)['world_design']['cast_sample_reference']
    assert refreshed['book_range'] is None and refreshed['sample_count']==1
    assert frozen['source_set_sha256'] != refreshed['source_set_sha256']
    assert genre_cast_samples(library,[])['chapter_ranges']['first'] is None
    other = next(g['id'] for g in library.genres()['genres'] if g['id'] not in genre)
    assert genre_cast_samples(library,[other])['sample_count'] == 0

    draft = deepcopy(row['body'])
    extra = deepcopy(draft['threads'][1])
    extra['id'] = 'crowd'
    extra['details']['subject_kind'] = 'group'
    draft['threads'].append(extra)
    assert 'crowd' not in cast_distribution(draft)['chapters'][0]['observation_ids']
    draft['threads'].pop()
    draft['threads'][-1]['details']['appearance_evidence']='q1'
    assert cast_distribution(draft)['chapters'][1]['appearing_count'] is None
    draft['schema_version']=4
    assert cast_distribution(draft) is None


def test_real_design_calls_receive_only_the_anonymous_cast_reference(tmp_path):
    from nw.call_budget import create_budget
    from nw.materials.work_session import drive_plan
    from nw.planning import prepare_plan_task
    from nw.store import Store
    from nw.story_state import adopt_story
    from nw.task_models import Budget
    from story_fixture import baseline
    from test_material_phase_flow import PhaseModel, template_catalog
    from test_novel_flow import config

    lib = LibraryService(tmp_path)
    add_reference(lib,'渡口证据',['GENRE_XUANYI'])
    wizard = freeze_wizard({'title':'印','idea':'谁揭下旧封条','genre_ids':['GENRE_XUANYI']},lib)
    governed = governance(wizard, library=lib)
    template_catalog(tmp_path)
    with Store(tmp_path/'story',create=True,test_mode=True) as store:
        store.init_project('隔离验证');store.add_brief('调查封条时的动作与状态变化')
        adopt_story(store,baseline(),{})
        model = PhaseModel()
        budget = create_budget(store,'cast-samples',Budget(32,90000,4000))
        req,payload = prepare_plan_task(store,1,'book',model,config(store),budget,'cast-samples',
                                        governance_inputs={'world_design':governed['world_design']})
        drive_plan(store,req,{**payload,'scope':'chapter'},model,config(store))
        packets = [json.loads(m[-1]['content']) for m in model.calls if '[MATERIAL_STEP]' in m[0]['content']]
    seen = {p['stage'] for p in packets if 'cast_sample_reference' in p}
    assert seen == {'world_design','character_design','plot_design','scene_design'}
    for packet in packets:
        if packet['stage'] in seen:
            hint = packet['cast_sample_reference']
            assert hint['book_range'] == {'min':2,'max':2}
            assert hint['chapter_bands']['opening']['functions']['handoff'] == [1,1]
            assert '阿霜' not in json.dumps(hint,ensure_ascii=False) and '渡口证据' not in str(hint)
