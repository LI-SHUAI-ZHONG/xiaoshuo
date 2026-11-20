"""[FAKE] Model replies for an isolated full-text reference and a different new novel."""
from copy import deepcopy
import json

from corpus_fixture import CorpusModel, make_book, runtime, wait_job
from nw.production_methods.contracts import at
from nw.studio.library import LibraryService
from project_methods_fixture import ProjectModel


SOURCE = ('# 第一章\n[FAKE] 暮塔记录官敲金铃并照影碑，只有两处互相印证，值守人才能放出灯签。\n'
          '# 第二章\n[FAKE] 暮塔的金铃响了，影碑却裂了。值守人扣住灯签，留下复验笔录。\n')
BRIEF = '[FAKE] 悬疑。调查临川渡放行记录被调包一案，潮刻可见，应让证据能被旁人复核。'
RULE = '[FAKE] 临川渡仅在闸簿封蜡和潮刻相符时放行货船，渡吏须登记两项核验结果。'
LIMIT = '[FAKE] 河雾遮住潮刻时，渡吏须扣船等站头复测，不得仅凭蜡印放行。'
FOG_RULE = '[FAKE] 临川渡在浓雾中以闸簿蜡印与岸亭回执双证放行，渡吏须登记回执编号。'
FOG_LIMIT = '[FAKE] 岸亭回执未送达时暂停放行，值守人须在闸簿登记待验原因。'
FOG_BRIEF = BRIEF.replace('潮刻可见', '潮刻常年不可见')
TAXON = 'GENRE_XUANYI'


class WorldCorpusModel(CorpusModel):
    def __init__(self, scopes, *, two_methods=False):
        super().__init__()
        self.scopes = scopes
        self.two_methods = two_methods

    def generate(self, messages, **params):
        result = super().generate(messages, **params)
        packet = json.loads(messages[-1]['content'])
        raw = json.loads(result.text)
        if packet['phase'] in ('detail', 'survey'):
            source = packet['source_text']
            event = raw['events'][0]
            if '影碑却裂了' in source:
                event.update(goal='[FAKE] 复核灯签放行条件', conflict='[FAKE] 金铃有声，影碑破裂',
                             choice='[FAKE] 扣住灯签并登记复验', result='[FAKE] 无法完成双证，灯签扣留')
            else:
                event.update(goal='[FAKE] 检查放出灯签的依据', conflict='[FAKE] 单有金铃不能放签',
                             choice='[FAKE] 敲金铃并照影碑以对照两项凭据', result='[FAKE] 双证一致可放出灯签')
        if packet.get('domain') == 'world_rules':
            raw['threads'][0]['details'] = {
                'rule': '[FAKE] 金铃与影碑记录必须同时成立方可放出灯签。',
                'scope': '[FAKE] 约束暮塔记录官和掌管灯签的值守人。',
                'boundary': '[FAKE] 即便金铃响起，影碑破裂时也须扣签、留下复验笔录。',
                'decision_effect': '[FAKE] 两处核验决定放签或扣留，后一次受阻留下可查记录。'}
        if packet['phase'] != 'methods':
            result.text = json.dumps(raw, ensure_ascii=False)
            return result
        body = raw['methods'][0]['body']
        body.update(title='[FAKE] 把双证门槛和验核失败落实为可追查的规则',
                    tasks=['world_rules'], scopes=self.scopes,
                    applicability=['[FAKE] 调查依赖可复查的制度限制，且失败必须产生可见的事件后果。'],
                    non_applicability=['[FAKE] 角色行事完全自由且无证据边界时不能套用双证门槛。'])
        body['prerequisites'] = [
            {'key': key, 'input_kind': kind, 'artifact': artifact,
             'requirement': '[FAKE] 对照本步需求以及本项目上游已经形成的设计选择。'}
            for key, kind, artifact in [('task', 'brief', '调查需求'), ('genre', 'type_selection', '本书类型'),
                                        ('approach', 'type_adaptation', '可见线索与限制')]]
        body['operations'] = [{'key': 'design', 'instruction': '[FAKE] 据项目调查渠道设计两项可验证凭据，写明失败时的程序与代价。',
                               'input_keys': ['task', 'genre', 'approach'], 'output_keys': ['gate']}]
        body['outputs'] = [{'key': 'gate', 'stage': 'world_design', 'field': 'members', 'artifact_kind': 'world',
                            'description': '[FAKE] 本书世界卡中的准入规则、可见凭据及失效边界。'}]
        body['downstream'] = [{'output_key': 'gate', 'consumer': stage, 'usage': '[FAKE] 把制度限制落实到具体选择、调查代价和可见证据。'}
                              for stage in ('plot_design', 'scene_design', 'writer', 'review')]
        body['acceptance'] = [{'output_key': 'gate', 'check': '[FAKE] 对照场景中的证据和行动能否成立。',
                              'evidence_required': '[FAKE] 世界卡的两项凭据、失效边界、实际场景与正文。'}]
        if self.two_methods:
            other = deepcopy(raw['methods'][0])
            other['body']['title'] = '[FAKE] 由公开扣留记录驱动事后复验'
            other['body']['applicability'] = ['[FAKE] 放行失败的记录可在不同地点重新核查。']
            raw['methods'].append(other)
        result.text = json.dumps(raw, ensure_ascii=False)
        return result


def source_methods(workspace, monkeypatch, *, approve=True, scopes=('book', 'chapter'), two_methods=False):
    library = LibraryService(workspace)
    provider = WorldCorpusModel(list(scopes), two_methods=two_methods)
    monkeypatch.setattr(library, '_corpus_runtime', lambda: (runtime(), provider))
    book = make_book(library, SOURCE)
    job = library.start_corpus_job(book['id'], {'options': {'extent': 'complete', 'note': '[FAKE] 两章参考短篇全文。'}})
    result = wait_job(library, book['id'], job['id'])
    assert result['status'] == 'completed', result['error']
    library.review_corpus(book['id'], {'version': 1, 'decision': 'approve', 'note': '[FAKE] 已核对两次核验的前后因果。'})
    job = library.start_corpus_job(book['id'], {'kind': 'methods', 'options': {'thread_ids': ['T_world_rules']}})
    result = wait_job(library, book['id'], job['id'])
    assert result['status'] == 'completed', result['error']
    methods = library.list_methods()['methods']
    if approve:
        methods = [library.review_method(method['id'], {'version': 1, 'decision': 'approve',
                   'note': '[FAKE] 核对完整参考文本、实例及单书方法的适用边界。'}) for method in methods]
        for method in methods:
            assert method['available'], method['issues'] + method['source_issues']
    return library, methods


def available_method(workspace, monkeypatch, **options):
    library, [method] = source_methods(workspace, monkeypatch, **options)
    return library, method


class WorldModel(ProjectModel):
    def __init__(self, *, invalid='', taxon=TAXON):
        super().__init__()
        self.invalid, self.taxon = invalid, taxon
        self.chapter_index = 1

    def generate(self, messages, **params):
        result = super().generate(messages, **params)
        data = json.loads(messages[-1]['content'])
        stage = data.get('stage')
        guides = [json.loads(item['text']) for item in data.get('items', [])
                  if item['source'].startswith('material:method:')]
        if guides:
            record = '岸亭回执' if '岸亭回执' in guides[0]['observable'] else '潮刻'
            result.text = f'[FAKE] 渡吏举起封蜡要放船。船工按住闸板，索要{record}。值簿上第二格空着，船只得留到复验。'
            return result
        if stage not in ('type_selection', 'type_adaptation', 'world_design', 'plot_design', 'scene_design'):
            return result
        raw = json.loads(result.text)
        if 'products' not in raw:
            return result
        products = raw['products']
        if stage == 'type_selection':
            products['selection'][0].update(id=self.taxon, label='悬疑' if self.taxon == TAXON else '奇幻')
            products['concepts'][0]['type_refs'] = [self.taxon]
        elif stage == 'type_adaptation':
            products['adaptations'][0]['parameters']['investigation'] = (
                '[FAKE] 潮刻被雾遮蔽，要改查独立留存的旁证。' if '常年不可见' in data['brief']['text']
                else '[FAKE] 依据能看见的潮刻，核验放行记录是否被改。')
            if self.invalid == 'unusable':
                products['adaptations'][0]['parameters']['investigation'] = '[FAKE] 匿名证人所在位置绝不能留下可以追查的公开记录。'
        elif stage == 'world_design' and data.get('production_method_selection', {}).get('mode') == 'inherit_world':
            products['members'] = deepcopy(data['production_method_selection']['approved_world_members'])
            if self.invalid == 'expose_private':
                products['members'][0]['body']['visibility'] = 'public'
        elif stage == 'world_design' and data.get('production_methods'):
            page = data['production_method_selection']['page']
            if self.invalid == 'unusable' or self.invalid == 'first_page_gap' and page == 1:
                result.text = json.dumps({'stage': stage, 'world_method_gap': {
                    'design_basis': [{'kind': 'type_adaptation', 'path': ['adaptations', 0, 'parameters', 'investigation']}],
                    'exclusions': [{'method_id': candidate['method']['id'],
                                    'reason': '[FAKE] 该方法依赖可追查的公开凭据，本步无法使用这些凭据。'}
                                   for candidate in data['production_methods']],
                    'missing': '[FAKE] 需要能在不披露证人行踪的条件下核验调查授权的方法。'}}, ensure_ascii=False)
                return result
            spec = data['production_methods'][0]
            upstream = spec['inputs']['approach']['value']['adaptations'][0]['parameters']['investigation']
            rule, limit = (FOG_RULE, FOG_LIMIT) if '被雾遮蔽' in upstream else (RULE, LIMIT)
            if self.invalid == 'verbatim':
                rule = spec['method']['body']['evidence'][0]['quote']
            world = products['members'][0]
            world['body'].update(title='[FAKE] 临川渡通行门槛', rule=rule, limits=limit)
            if self.invalid == 'expose_private':
                world['body']['visibility'] = 'author_only'
            places = [{'path': ['members', 0, 'body', k], 'value': world['body'][k]} for k in ('rule', 'limits')]
            if self.invalid == 'label':
                places = [{'path': ['members', 0, 'key'], 'value': world['key']}]
            basis = ['adaptations', 0, 'parameters', 'investigation']
            if self.invalid == 'unrelated_basis':
                basis = ['adaptations', 0, 'id']
            products['_method_applications'] = [{'method_id': spec['method']['id'],
                'design_basis': [{'kind': 'type_adaptation', 'path': basis}],
                'operations': [{
                'key': 'design', 'explanation': '[FAKE] 按渡口的可见证据与调包疑点设计两方核验，并给人物留下能复查的失败记录。'}],
                'outputs': [{'key': 'gate', 'placements': places, 'scene_guidance': []}]}]
            if self.invalid == 'unoffered':
                offered = {candidate['method']['id'] for candidate in data['production_methods']}
                products['_method_applications'][0]['method_id'] = next(key for key in self.known_ids if key not in offered)
        elif stage in ('plot_design', 'scene_design') and data.get('method_handoffs'):
            if stage == 'plot_design' and data['scope'] == 'volume':
                products['members'].append({'key': 'crossing_volume', 'kind': 'volume',
                    'body': {'title': '[FAKE] 临川渡案', 'goal': '[FAKE] 确认扣船原因', 'turn': '[FAKE] 发现回执遗失'}})
            if stage == 'scene_design':
                products['chapters'][0]['index'] = self.chapter_index
                products['chapters'][0]['scenes'][0]['story_order'] = self.chapter_index
            for receipt in products['_method_receipts']:
                delivery = next(incoming for incoming in data['method_handoffs'] if incoming['id'] == receipt['id'])
                outputs = delivery['output']['placements']
                rule = next(row['value'] for row in outputs if row['path'][-1] == 'rule')
                clue = '岸亭回执' if '岸亭回执' in rule else '潮刻'
                operation = f'[FAKE] 船工索要{clue}的第二份核验记录，迫使渡吏承认闸簿不能单独放行。'
                if stage == 'plot_design':
                    places = []
                    for index, direction in enumerate(products['directions']):
                        choice = (operation if index == 0 else
                                  f'[FAKE] 渡吏扣住货船，请另一位值守人携{clue}的副本与闸簿当场复核。')
                        direction['choice'] = choice
                        places.append({'path': ['directions', index, 'choice'], 'value': choice})
                else:
                    places = []
                    for index, member in enumerate(products['members']):
                        if member['kind'] == 'scene':
                            member['body']['goal'] = operation
                            places.append({'path': ['members', index, 'body', 'goal'], 'value': operation})
                    for row in receipt['scene_guidance']:
                        row.update(observable=f'[FAKE] 船工查验{clue}与闸簿的记录能否互相印证。',
                                   check='[FAKE] 从本场可见行为核验放行或扣船的依据和代价。')
                receipt.update(operation=operation, placements=places)
            for receipt in products['_method_receipts']:
                for place in receipt['placements']:
                    place['value'] = deepcopy(at(products, place['path']))
        result.text = json.dumps(raw, ensure_ascii=False)
        return result
