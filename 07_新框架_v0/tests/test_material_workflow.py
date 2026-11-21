from hashlib import sha256
import json

import pytest

from nw.acceptance import accept_batch
from nw.chapter_state import chapter_state
from nw.context.story import StoryScope, build_story_context, scene_scope
from nw.experiments.ab import Experiment
from nw.materials.catalog import build_catalog, list_catalog
from nw.materials.reviews import Review, _REVIEWS
from nw.materials.unit_catalog import index_units
from nw.novel_flow import JobRequest, resume_job, start_job
from nw.store import Store
from nw.story_state import adopt_story, current_head
from nw.task_models import Budget
from story_fixture import baseline, draft_for, proposal
from test_material_catalog import _manifest
from test_novel_flow import Model, author, config
from test_selection import method


def anchor_pin(tmp_path, monkeypatch):
    root = tmp_path / 'source'
    data = '| M1.1 | 道具_完整 | 道具处于完整状态 | 道具未被损坏 | 物质 |\n'.encode()
    mf = _manifest(root, tmp_path, [('anchor.txt', 'anchors', data)])
    build_catalog(tmp_path, root, mf)
    index_units(tmp_path, None)
    row = list_catalog(tmp_path, None, 'M1.1')['fragments'][0]
    source = list_catalog(tmp_path, None, None)['sources'][0]
    ident = row['fragment_id']
    monkeypatch.setitem(_REVIEWS, ident, Review(source['file_sha256'], row['sha256'], 'anchor',
                         '物件的完整状态', '仅本场可见的未损物件', '本场物件与观察动作'))
    from fake_binding_reviews import install_review_fixtures
    install_review_fixtures(tmp_path)
    return {'id': ident, 'file_sha256': source['file_sha256'], 'sha256': row['sha256'],
            'disposition': 'required', 'reason': '首场检验封条原样'}


class MaterialModel(Model):
    def __init__(self, *, failure=''):
        super().__init__()
        self.failure = failure

    def generate(self, messages, **params):
        result = super().generate(messages, **params)
        prompt, payload = messages[0]['content'], json.loads(messages[1]['content'])
        if 'candidate_cards' in prompt:
            parsed = json.loads(result.text)
            if payload['scope'] != 'book':
                ident = payload['materials'][0]['source']['id']
                for item in parsed['candidate_cards']:
                    item['material_bindings'] = {'scene': {ident: {
                        'function': '检查封条', 'parameter': '完好', 'observable': '入井时看到封条边角完整',
                        'check': '观察在接触前发生', 'observer': 'yan',
                        'object': '封条', 'beat': '入井', 'timing': '接触前', 'condition': '未损坏'}}}
                    if self.failure == 'defer-all':
                        item['material_bindings']['scene'][ident] = {'disposition': 'deferred', 'reason': '以后再写'}
            result.text = json.dumps(parsed, ensure_ascii=False)
        elif '{"recommendation"' in prompt:
            parsed = json.loads(result.text)
            target = payload['draft']
            text = target['text']
            contract = payload['material_review']
            start = text.index('沈')
            end = start + 2 if self.failure == 'keyword' else len(text)
            if self.failure == 'old-draft':
                contract['draft']['version'] -= 1
            parsed['material_checks'] = [
                {'id': check['id'], 'status': 'failed' if self.failure == 'failed' else 'pass',
                 'reason': '进门时先看边角，再伸手检查', 'evidence': [{
                     **contract['draft'], 'start': start, 'end': end,
                     'quote': text[start:end] if self.failure != 'quote' else '错误引用'}]}
                for check in contract['checks']]
            for row,check in zip(parsed['material_checks'],contract['checks']):
                if check.get('source_contract'):
                    row['source_checks']=[{'id':field['id'],'status':'pass','reason':'[FAKE] 原义要求在当前实际段落中得到执行',
                        'evidence':row['evidence']} for field in check['source_contract'].get('obligations',[])]
            result.text = json.dumps(parsed, ensure_ascii=False)
        elif '只输出正文' in prompt and '修订' not in prompt:
            assert any(item['source'].startswith('material:') for item in payload['items'])
            result.text = '[FAKE] 沈砚借灯先看封条，四角齐全。他这才伸手。'
        return result


def choose(step, data):
    return {'action': 'approve', 'root': data['candidates'][0]['root']['card_id'], 'reason': '核对资料与场景'}


def design(store, pin, provider):
    from fake_binding_reviews import install_review_fixtures
    install_review_fixtures(store.directory.parent)
    ident = start_job(store, JobRequest('design', budget=Budget(32, 45000, 2000), materials=[pin])).id
    first=resume_job(store, ident, provider, config(store))
    assert first.step == 'plan:book:confirm',first.reason
    second = resume_job(store, ident, provider, config(store), choose)
    assert second.step == 'plan:chapter:confirm', second.reason
    result = resume_job(store, ident, provider, config(store), choose)
    assert result.status == 'DONE', result.reason
    return result.outputs['application']['chapters'][0]['scenes'][0]['scene_id']


def test_adopted_material_survives_design_review_acceptance_and_restart(tmp_path, monkeypatch):
    pin = anchor_pin(tmp_path, monkeypatch)
    path = tmp_path / 'demo'
    provider = MaterialModel()
    with Store(path, create=True, test_mode=True) as store:
        store.init_project('暗井')
        store.add_brief('追查封条')
        adopt_story(store, baseline(), {})
        scene = design(store, pin, provider)
        job = start_job(store, JobRequest('write', scene_ids=[scene], budget=Budget(12, 45000, 2000))).id
        ready = resume_job(store, job, provider, config(store))
        assert ready.step == 'batch:confirm', ready.reason
        assert ready.outputs['gate']['scenes'][0]['material_checks'][0]['id'] == pin['id']
        calls = len(provider.calls)
    with Store(path, test_mode=True) as reopened:
        assert resume_job(reopened, job, provider, config(reopened), author()).status == 'DONE'
        assert len(provider.calls) == calls and len(reopened.list('accepted')) == 1


def test_accepted_stable_identity_anchor_can_be_traced_after_reopening(tmp_path, monkeypatch):
    from nw.materials import library_adjudication
    from nw.materials.adjudication import build_adjudications
    from nw.materials.route_catalog import route
    from nw.story_delta import read_delta

    text = '| ID1.1 | 身份_职业_学徒 | 学徒身份 | 学习阶段 | 身份 |\n'
    source_root = tmp_path / 'source'
    monkeypatch.setitem(library_adjudication._PINNED, 'anchors', sha256(text.encode()).hexdigest())
    manifest = _manifest(source_root, tmp_path, [('anchor.txt', 'anchors', text.encode())])
    build_catalog(tmp_path, source_root, manifest)
    index_units(tmp_path, None)
    build_adjudications(tmp_path)
    ident = list_catalog(tmp_path, None, 'ID1.1')['fragments'][0]['fragment_id']
    source = route(tmp_path, ident)['source']
    pin = {**{key: source[key] for key in ('id', 'file_sha256', 'sha256')},
           'disposition': 'required', 'reason': '调查中继续体现已在学习阶段的身份'}
    paragraphs = ['[FAKE] 门内灯光很暗。', '沈砚托住活板，让师父先查看榫口，自己跟着学。']

    class IdentityModel(Model):
        def generate(self, messages, **params):
            from nw.llm.base import GenResult

            prompt = messages[0]['content']
            payload = json.loads(messages[-1]['content'])
            if '[MATERIAL_STEP]' in prompt or '[MATERIAL_ASSEMBLY]' in prompt:
                return super().generate(messages, **params)
            if '只输出正文' in prompt and '修订' not in prompt:
                return GenResult('\n\n'.join(paragraphs), 'complete', {}, 'test', {})
            if '{"operations"' in prompt:
                return GenResult('{"operations":[]}', 'complete', {}, 'test', {})
            response = super().generate(messages, **params)
            if 'candidate_cards' in prompt and payload['scope'] != 'book':
                parsed = json.loads(response.text)
                for candidate in parsed['candidate_cards']:
                    candidate['material_bindings'] = {'scene': {ident: {
                        'function': '师徒分工', 'parameter': '仍处于学习阶段',
                        'observable': '沈砚扶住活板，跟着师父学验榫口',
                        'check': '主动等师父示范并学习，身份持续成立',
                        'observer': 'yan', 'object': '沈砚', 'beat': '帮师父验榫口',
                        'timing': '验榫口时', 'condition': '师父在场验榫口',
                        'source_scope': {
                            clause['id']: {'disposition': 'required', 'reason': '实际核对学习阶段'}
                            for clause in payload['materials'][0]['review']['contract']['obligations']},
                    }}}
                response.text = json.dumps(parsed, ensure_ascii=False)
            elif '{"recommendation"' in prompt:
                parsed = json.loads(response.text)
                start = len(paragraphs[0]) + 2
                evidence = {**payload['material_review']['draft'], 'start': start,
                            'end': start + len(paragraphs[1]), 'quote': paragraphs[1]}
                for check in parsed['material_checks']:
                    check['reason'] = '验榫口时他只托板观看，师父示范，他跟着学，现有学徒身份仍成立'
                    check['evidence'] = [evidence]
                    for clause in check.get('source_checks', []):
                        clause['evidence'] = [evidence]
                    if 'layer_check' in check:
                        check['layer_check']['evidence'] = [evidence]
                response.text = json.dumps(parsed, ensure_ascii=False)
            return response

    path = tmp_path / 'demo'
    provider = IdentityModel()
    with Store(path, create=True, test_mode=True) as store:
        store.init_project('学徒试稿')
        store.add_brief('学徒查到旧榫口')
        adopt_story(store, baseline(), {})
        scene = design(store, pin, provider)
        prior = current_head(store)
        job = start_job(store, JobRequest('write', scene_ids=[scene], budget=Budget(12, 45000, 2000))).id
        result = resume_job(store, job, provider, config(store), author())
        assert result.status == 'DONE', result.reason
        head = current_head(store)
        assert head.revision == prior.revision + 1

    with Store(path, test_mode=True) as store:
        state = chapter_state(store, head, 1)
        assert not read_delta(store, state['drafts'][0]['delta_id']).operations
        assert state['changes'] == []
        assert 'identity_anchor_checks' not in chapter_state(store, prior, 1)
        checks = state['identity_anchor_checks']
        assert {row['check_id'] for row in checks} >= {ident}
        clauses = [row for row in checks if row['check_id'].startswith('work:semantic:')]
        assert len(clauses) == 3
        assert len({row['source_checks'][0]['obligation']['id'] for row in clauses}) == 3
        for check in checks:
            assert check['source']['key'] == 'ID1.1'
            assert check['source']['id'] == ident and check['source']['sha256'] == source['sha256']
            assert check['draft_ref'] == state['drafts'][0]['draft_ref']
            assert store.get('run', check['review_run_id']).kind == 'review'
            assert check['evidence'][0]['quote'] == paragraphs[1]
            assert check['paragraph_evidence'] == [{
                'prose_location': f'{scene}#paragraphs[1]',
                'start': len(paragraphs[0]) + 2,
                'end': len('\n\n'.join(paragraphs)),
                'paragraph_sha256': sha256(paragraphs[1].encode()).hexdigest(),
            }]
            assert check['source_checks']
            assert all(row['paragraph_evidence'] == check['paragraph_evidence'] for row in check['source_checks'])


@pytest.mark.parametrize('method', (
    'word-choice', 'prop-boundary', 'supporting-disclosure', 'dilemma', 'branch-reversal',
    'body-signal', 'foreshadow-reveal', 'scene-transition', 'conflict-round', 'dialogue-turn',
    'belief-challenge', 'exploration', 'cooperation', 'memory-trigger', 'crafting-result', 'decision-cost',
))
def test_selected_embedded_prose_method_reaches_writer_review_and_revision(tmp_path, monkeypatch, method):
    from nw.llm.base import GenResult
    from nw.materials import library_adjudication, phase_routes
    from nw.materials.adjudication import build_adjudications
    from nw.materials.work_catalog import SourceDesk

    text = ('## 板块50 词汇控制\n\n### 通用动词限制使用\n\n'
            '【定义】限制使用走/看/说/拿/放/做/有/是等通用动词。\n'
            '【判定标准】每段对话中，“说”最多使用1次（其余用精确动词替代或省略）\n')
    key = '板块50 词汇控制#通用动词限制使用'
    writer_use = '标明说话人的“说”，最多一次'
    review_use = '区别台词中的词和标记说话人的“说”'
    excluded = '板块50 词汇控制#精确动词鼓励使用'
    if method == 'prop-boundary':
        key = '28.2_道具功能边界'
        text = ('## 板块28 核心道具\n\n### ' + key + '\n\n'
                '【定义】道具能做什么和不能做什么的明确界定。\n'
                '【指令】首次出现让读者感到道具作用范围，后续通过使用逐步精确化。\n')
        writer_use = '读者能看到的最小效果'
        review_use = '早期证据需指向这项新用途'
        excluded = '28.3_道具代价机制'
    elif method == 'supporting-disclosure':
        key = '121.11_配角信息承载功能'
        text = ('## 板块121 配角运用\n\n### ' + key + '\n\n'
                '【定义】配角通过实际行动揭示自己接触的世界规则。\n'
                '【指令】依身份所知及当前出场节奏披露已经掌握的信息。\n')
        writer_use = '把说出口、能被察觉和仍然不知道的内容分开'
        review_use = '来源、听者及读者各自掌握的证据'
        excluded = '121.11_配角之间的互动关系'
    elif method == 'dilemma':
        key = '43.4_道德困境'
        text = ('## 板块43 冲突体系\n\n### ' + key + '\n\n'
                '【定义】两难选择，无论选哪个都要支付代价。\n'
                '【指令】人物在本场已知的两项价值之间取舍。\n')
        writer_use = '实际付出和仍然受影响的对象'
        review_use = '哪项价值被优先保住'
        excluded = '43.1_资源争夺'
    elif method == 'branch-reversal':
        key = '42.6_岔路设计与回撤机制'
        text = ('## 板块42 情节结构\n\n### ' + key + '\n\n'
                '【定义】关键节点展示多个选项，选择后关闭其他。\n'
                '【指令】岔路通过选择表现角色，回撤让选择的代价被再次确认。\n')
        writer_use = '只写真正还原的部分'
        review_use = '逐段核对可以重选什么'
        excluded = '42.8_失败设计'
    elif method == 'body-signal':
        key = '7.4_情感与身体反应'
        text = ('## 板块7 情感运用\n\n### ' + key + '\n\n'
                '【定义】情感通过可观察的身体信号被读者感知。\n'
                '【写作指令】用一个触发前后的身体动作呈现情感变化。\n')
        writer_use = '既有握持、呼吸或姿态在触发后怎样变了'
        review_use = '引用触发、可观察反应及紧接着的行动'
        excluded = '7.2_情感在对话中的呈现'
    elif method == 'foreshadow-reveal':
        key = '板块45 伏笔与反转#伏笔揭示'
        text = ('## 板块45 伏笔与反转\n\n### 伏笔揭示\n\n'
                '【定义】伏笔被揭晓的方式。\n'
                '【判定标准】揭示时读者回溯伏笔，情感和认知并重。\n')
        writer_use = '之前看见的哪一处细节此刻有了含义'
        review_use = '初次留下的细节、揭示依据和本场得到的答案'
        excluded = '板块45 伏笔与反转#伏笔休眠期'
    elif method == 'scene-transition':
        key = '板块46 场景结构#场景过渡'
        text = ('## 板块46 场景结构\n\n### 场景过渡\n\n'
                '【定义】场景之间的连接方式。\n'
                '【判定标准】过渡不应超过1句或1个短段落。\n')
        writer_use = '一处能辨认的新地点、时间或观察者'
        review_use = '定位上场结束与本场启动处'
        excluded = '板块91 场景结构检查#场景过渡'
    elif method == 'conflict-round':
        key = '板块47 场景冲突#对抗回合'
        text = ('## 板块47 场景冲突\n\n### 对抗回合\n\n'
                '【定义】持续对抗由多个回合构成。\n'
                '【判定标准】各回合有行动、反应和局势变化。\n')
        writer_use = '本次响应怎样改变下一步还能做什么'
        review_use = '按行动、对方回应和实际局势变化定位每个回合'
        excluded = '板块93 冲突规则检查#对抗回合数'
    elif method == 'dialogue-turn':
        key = '板块57 对话技术#非直接回答'
        text = ('## 板块57 对话技术\n\n### 非直接回答\n\n'
                '【定义】每场对话至少1次非直接回答。\n'
                '【判定标准】当角色不想回答或还没有准备好回答时使用。\n')
        writer_use = '延后答复时留实际未决的事'
        review_use = '辨认这次答到哪一步、还有什么未回答'
        excluded = '板块57 对话技术#潜台词设计'
    elif method == 'belief-challenge':
        key = '板块69 心智模型#信念系统挑战'
        definition = '外部事件或信息与角色既有信念产生不可调和的矛盾。'
        text = ('## 板块69 心智模型\n\n### 信念系统挑战\n\n'
                f'【定义】{definition}\n【设计指令】{definition}\n\n'
                '### 信念系统崩溃\n\n【定义】当核心信念被挑战且无法回避时。\n')
        writer_use = '让具体反例碰到原信念支持的做法'
        review_use = '核对原先信念、实际到达的反证和人物的可见反应'
        excluded = '板块69 心智模型#信念系统崩溃'
    elif method == 'exploration':
        key = '板块83 环境交互#探索'
        text = ('## 板块83 环境交互\n\n### 探索\n\n'
                '【定义】进入未知区域获取信息或资源。\n'
                '【判定标准】探索的“归来后”阶段最容易被忽略，但正是它决定了探索的意义和连载的持续动力。\n\n'
                '### 改造\n\n【定义】主动改变环境以适合自身需求。\n'
                '【判定标准】改造是角色的力量在环境中的延伸。\n')
        writer_use = '沿人物确实走到的参照写发现'
        review_use = '有归来后场时回查所得改变了谁的选择'
        excluded = '板块83 环境交互#改造'

    elif method == 'cooperation':
        key = '板块86 社会交互#合作'
        text = ('## 板块86 社会交互\n\n### 合作\n\n'
                '【定义】共同行动以达成共同目标。\n'
                '【判定标准】规则\\*\\*：合作是“正和博弈”——双方都能获益\n\n'
                '### 同盟\n\n【定义】建立合作关系。\n')
        writer_use = '把各自负责的行动接起来完成同一目标'
        review_use = '分别找共同目标、两方投入及已证收益'
        excluded = '板块86 社会交互#同盟'

    elif method == 'memory-trigger':
        key = '158.3_回忆设计'
        text = ('## 板块158 角色认知阶梯\n\n### ' + key + '\n\n'
                '【定义】通过角色的记忆片段揭示过去信息，为当下的行为和判断提供深层依据。\n'
                '【指令】\n'
                '- 回忆触发必须具体：一个物品、一个气味、一个声音、一个动作触发回忆\n'
                '- 回忆后必须有当下连接：回忆结束后，角色的行为或判断发生了具体变化\n\n'
                '### 158.2_三种认知反转\n\n【定义】角色对已有判断的反转。\n')
        writer_use = '用当场可感的一件事触发回忆'
        review_use = '引用触发物、回忆中新增的实际信息'
        excluded = '158.2_三种认知反转'

    elif method == 'crafting-result':
        key = '30.3_道具制造_制作工艺'
        text = ('## 板块30 道具操作\n\n### ' + key + '\n\n'
                '【定义】道具的创造过程和所需条件。\n'
                '【指令】\n'
                '\\*\\*写作规则\\*\\*：制造/制作过程不是“一键合成”，必须有步骤和细节。'
                '制造过程的篇幅与制造物的重要性成正比——核心道具的制造可能需要一个完整篇章。\n\n'
                '### 30.4_道具维护与升级\n\n【定义】道具的保养和改进。\n')
        writer_use = '从已定材料和工序写到本场完成的中间物或成品'
        review_use = '核对材料、工序、人物能力和完成证据'
        excluded = '30.4_道具维护与升级'

    elif method == 'decision-cost':
        key = '板块73 决策规则#决策成本'
        text = ('## 板块73 决策规则\n\n### 决策成本\n\n'
                '【定义】每个决定消耗的时间、精力、情感和物质。\n'
                '【判定标准】规则\\*\\*：决策成本让“做决定”本身成为可感知的事件\n\n'
                '### 决策时机\n\n【定义】角色在什么时候做决定。\n')
        writer_use = '把决定过程实际用掉的时间、精力、情感或物质'
        review_use = '逐项查付出了什么、由谁承担、发生何时'
        excluded = '板块73 决策规则#决策时机'

    root = tmp_path / 'source'
    digest = sha256(text.encode()).hexdigest()
    monkeypatch.setitem(library_adjudication._PINNED, 'library', digest)
    monkeypatch.setattr(phase_routes, '_LIBRARY_SHA256', digest)
    manifest = _manifest(root, tmp_path, [('library.txt', 'library', text.encode())])
    build_catalog(tmp_path, root, manifest)
    index_units(tmp_path, None)
    build_adjudications(tmp_path)
    source = next(row for row in SourceDesk(tmp_path).rows if row['key'] == key)
    pin = {**{name: source[name] for name in ('id','file_sha256','sha256')},
           'disposition': 'required', 'reason': '检查调查动作和说话人提示'}

    class ProseModel(Model):
        def __init__(self):
            super().__init__()
            self.prose_calls = []

        def generate(self, messages, **params):
            prompt = messages[0]['content']
            payload = json.loads(messages[-1]['content'])
            if prompt.startswith('根据冻结的工作包') or prompt.startswith('按作者约束和本场任务写正文'):
                revising = prompt.startswith('根据冻结的工作包')
                self.prose_calls.append('revise' if revising else 'write')
                assert prompt.count('### ' + key) == 1
                assert writer_use in prompt
                assert '### ' + excluded not in prompt
                return GenResult('[FAKE] 沈砚攥住钥匙，把灯挪近门缝。', 'complete', {}, 'test', {})
            response = super().generate(messages, **params)
            if '{"recommendation"' in prompt:
                already_reviewed = 'review' in self.prose_calls
                self.prose_calls.append('review')
                assert prompt.count('### ' + key) == 1
                assert review_use in prompt
                if method in ('exploration', 'cooperation', 'memory-trigger', 'crafting-result', 'decision-cost'):
                    assert '### ' + excluded not in prompt
                if not already_reviewed:
                    raw = json.loads(response.text)
                    raw.update(recommendation='revise', notes='[FAKE] 调整动作中的照应')
                    response.text = json.dumps(raw, ensure_ascii=False)
            elif 'candidate_cards' in prompt and payload['scope'] != 'book':
                raw = json.loads(response.text)
                for candidate in raw['candidate_cards']:
                    for record in payload.get('materials', []):
                        if record['source']['id'] != pin['id']:
                            continue
                        obligations = record['review']['contract']['obligations']
                        candidate['material_bindings'] = {'scene': {pin['id']: {
                            'function': '具体表现抓住钥匙',
                            'parameter': '按确认的动作方式和力度选动词',
                            'observable': '沈砚攥住钥匙，挪近灯光',
                            'check': '动作有具体方式，同时核对提示语',
                            'source_scope': {item['id']: {'disposition': 'required', 'reason': '本场采用'}
                                             for item in obligations},
                        }}}
                response.text = json.dumps(raw, ensure_ascii=False)
            return response

    provider = ProseModel()
    with Store(tmp_path / 'demo', create=True, test_mode=True) as store:
        store.init_project('动作表达核对')
        store.add_brief('沈砚把钥匙握紧后借灯调查')
        adopt_story(store, baseline(), {})
        scene = design(store, pin, provider)
        # These fixtures carry more per-stage evidence into the isolated review.
        context_limit = 90000 if method in ('cooperation', 'decision-cost') else 45000
        job = start_job(store, JobRequest('write', scene_ids=[scene], budget=Budget(12, context_limit, 2000))).id
        result = resume_job(store, job, provider, config(store), author())
        assert result.status == 'DONE', result.reason
        assert provider.prose_calls == ['write','review','revise','review']
        assert len(store.drafts(scene)) == 2 and len(store.list('accepted')) == 1


@pytest.mark.parametrize('failure', ('quote', 'keyword', 'old-draft', 'failed'))
def test_invalid_material_evidence_blocks_acceptance(tmp_path, monkeypatch, failure):
    pin = anchor_pin(tmp_path, monkeypatch)
    provider = MaterialModel(failure=failure)
    with Store(tmp_path / 'demo', create=True, test_mode=True) as store:
        store.init_project('暗井')
        store.add_brief('追查封条')
        adopt_story(store, baseline(), {})
        scene = design(store, pin, provider)
        job = start_job(store, JobRequest('write', scene_ids=[scene], budget=Budget(12, 45000, 2000, 0))).id
        result = resume_job(store, job, provider, config(store), author())
        assert result.status == 'BLOCKED' and 'MATERIAL_EVIDENCE' in result.reason
        assert not store.list('accepted')


def test_manual_batch_cannot_bypass_material_review(tmp_path, monkeypatch):
    pin = anchor_pin(tmp_path, monkeypatch)
    with Store(tmp_path / 'demo', create=True, test_mode=True) as store:
        store.init_project('暗井')
        store.add_brief('追查封条')
        adopt_story(store, baseline(), {})
        scene = design(store, pin, MaterialModel())
        head = current_head(store)
        request = proposal(store, head, draft_for(store, scene, '[FAKE] 封条完好。'), [])
        with pytest.raises(ValueError, match='independent material review'):
            accept_batch(store, [request], head, 'manual-test')
        assert current_head(store) == head
        assert not store.list('accepted')


def test_reviewed_source_requires_exact_version_and_explicit_scope(tmp_path, monkeypatch):
    pin = anchor_pin(tmp_path, monkeypatch)
    with Store(tmp_path / 'demo', create=True, test_mode=True) as store:
        store.init_project('暗井')
        store.add_brief('追查封条')
        adopt_story(store, baseline(), {})
        budget = Budget(3, 45000, 2000)
        with pytest.raises(ValueError, match='STALE_MATERIAL'):
            start_job(store, JobRequest('design', budget=budget, materials=[{**pin, 'sha256': '0' * 64}]))
        monkeypatch.delitem(_REVIEWS, pin['id'])
        with pytest.raises(ValueError, match='MATERIAL_UNQUALIFIED'):
            start_job(store, JobRequest('design', budget=budget, materials=[pin]))
        result = start_job(store, JobRequest('design', budget=budget,
                                            materials=[{**pin, 'disposition': 'deferred'}]))
        assert result.id


def test_both_blind_test_arms_keep_the_required_material(tmp_path, monkeypatch):
    pin = anchor_pin(tmp_path, monkeypatch)
    provider = MaterialModel()
    with Store(tmp_path / 'demo', create=True, test_mode=True) as store:
        store.init_project('暗井')
        store.add_brief('追查封条')
        adopt_story(store, baseline(), {})
        scene = design(store, pin, provider)
        method(store, 'inspect', tag='调查证物')
        experiment = Experiment(store)
        arms = experiment.start_story(scene, provider, 'test', {}, budget=Budget(2, 45000, 2000), seed=12)
        assert arms['status'] == 'READY'
        sent = [json.loads(messages[-1]['content'])['items'] for messages in provider.calls[-2:]]
        required = f"material:{pin['id']}"
        assert [sum(row['source'] == required for row in items) for items in sent] == [1, 1]
        assert sorted(sum(row['source'] == 'rule:inspect' for row in items) for items in sent) == [0, 1]
        experiment.choose(1, arms['experiment_id'], reason='隔离对照')
        assert experiment.reveal(arms['experiment_id'])['verified']


def test_required_material_needs_a_selected_scene_or_an_author_deferral(tmp_path, monkeypatch):
    pin = anchor_pin(tmp_path, monkeypatch)
    provider = MaterialModel(failure='defer-all')
    with Store(tmp_path / 'demo', create=True, test_mode=True) as store:
        store.init_project('暗井')
        store.add_brief('追查封条')
        adopt_story(store, baseline(), {})
        job = start_job(store, JobRequest('design', budget=Budget(32, 45000, 2000), materials=[pin])).id
        assert resume_job(store, job, provider, config(store)).step == 'plan:book:confirm'
        result = resume_job(store, job, provider, config(store), choose)
        assert result.status == 'BLOCKED' and result.step == 'plan:chapter:propose'
        assert 'MATERIAL_DESIGN' in result.reason and 'M1.1' in result.reason
        assert not store.list('scene')


def test_reusing_an_approved_scene_card_cannot_drop_its_material_gate(tmp_path, monkeypatch):
    pin = anchor_pin(tmp_path, monkeypatch)
    with Store(tmp_path / 'demo', create=True, test_mode=True) as store:
        store.init_project('暗井')
        store.add_brief('追查封条')
        adopt_story(store, baseline(), {})
        scene = design(store, pin, MaterialModel())
        approved = store.get('scene', scene)
        scope = scene_scope(store, scene)
        clone = store.add_scene(approved.chapter_id, 2, json.dumps({'story': {
            'scene_ref': scope.scene_ref, 'story_order': scope.story_order}}))
        blank = store.add_scene(approved.chapter_id, 3, '{}')
        with pytest.raises(ValueError, match='original materialized scene'):
            build_story_context(store, clone.id, scene_scope(store, clone.id), 45000)
        explicit = StoryScope(scope.branch_id, scope.revision, scope.story_order, scope.scene_ref)
        with pytest.raises(ValueError, match='original materialized scene'):
            build_story_context(store, blank.id, explicit, 45000)


def test_legacy_character_check_uses_the_frozen_character_card_in_first_scene(tmp_path, monkeypatch):
    from nw.materials import routing

    root = tmp_path / 'source'
    data = '#### 检查1：人物设定一致\n- 对照人物设定检查行为、能力和声音。\n'.encode()
    manifest = _manifest(root, tmp_path, [('execution.txt', 'execution', data)])
    registry = json.loads(manifest.read_text(encoding='utf-8'))
    registry['catalog_inputs'][0]['layer'] = 'legacy_contract'
    manifest.write_text(json.dumps(registry), encoding='utf-8')
    build_catalog(tmp_path, root, manifest)
    index_units(tmp_path, None)
    source = list_catalog(tmp_path, None, None)['sources'][0]
    row = list_catalog(tmp_path, source['source_id'], None)['fragments'][0]
    ident = row['fragment_id']
    monkeypatch.setattr(routing, 'CHARACTER_EDITOR', ident)
    monkeypatch.setitem(_REVIEWS, ident, Review(source['file_sha256'], row['sha256'], 'character_editor',
                         '人物设定一致', '已采用的人物卡', '动作或台词及理由'))
    pin = {'id': ident, 'file_sha256': source['file_sha256'], 'sha256': row['sha256'],
           'disposition': 'required', 'reason': '核对首场沈砚行动与设定'}

    class CharacterModel(MaterialModel):
        def generate(self, messages, **params):
            prompt = messages[0]['content']
            payload = json.loads(messages[-1]['content'])
            if '只输出正文' in prompt:
                assert all('character_editor' not in item['text'] for item in payload['items'])
                output = Model.generate(self, messages, **params)
                output.text = '[FAKE] 沈砚没有伸手掀封条，他先把木片探进纸角，托出了旧印的半枚字形。'
                return output
            output = super().generate(messages, **params)
            if 'candidate_cards' in prompt and payload['scope'] != 'book':
                proposed = json.loads(output.text)
                for candidate in proposed['candidate_cards']:
                    if ident not in candidate['material_bindings']['scene']:continue
                    candidate['material_bindings']['scene'][ident] = {
                        'function': '检查调查动机', 'parameter': '沈砚查封条',
                        'observable': '发现物件后主动调查', 'check': '行为符合目标', 'character': 'yan',
                    }
                output.text = json.dumps(proposed, ensure_ascii=False)
            elif '{"recommendation"' in prompt:
                contract = payload['material_review']
                assert 'comparison' not in contract
                card = contract['checks'][0]['character_card']
                assert card['ref']['kind'] == 'card' and card['ref']['version'] == 1
                assert card['body']['name'] == '沈砚'
                scene = next(json.loads(item['text']) for item in payload['context']['items']
                             if item['source'].startswith('scene:'))
                assert card['ref']['id'] == scene['pov']
            return output

    with Store(tmp_path / 'demo', create=True, test_mode=True) as store:
        store.init_project('暗井')
        store.add_brief('追查封条')
        adopt_story(store, baseline(), {})
        provider = CharacterModel()
        scene = design(store, pin, provider)
        job = start_job(store, JobRequest('write', scene_ids=[scene], budget=Budget(12, 45000, 2000))).id
        result = resume_job(store, job, provider, config(store), author())
        assert result.status == 'DONE', result.reason
        assert len(store.list('accepted')) == 1

