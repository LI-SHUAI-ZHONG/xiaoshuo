
import json

from nw.store import Store
from nw.story_state import adopt_story
from story_fixture import baseline
from test_cli import invoke
from test_novel_flow import Model
from test_providers import server


def test_cli_three_scene_story_roundtrip(tmp_path, server):
    endpoint, transport = server
    config = tmp_path / 'model.toml'
    config.write_text(f'[model]\nprovider="ollama"\nbase_url="{endpoint}"\nmodel="test"\n', encoding='utf-8')
    with Store(tmp_path / 'book', create=True) as store:
        store.init_project('钥匙')
        store.add_brief('追查封条', '受限第三人称')
        adopt_story(store, baseline(), {})
    model = Model()

    def respond(body):
        messages = body['messages']
        result = model.generate(messages)
        payload = json.loads(messages[-1]['content'])
        if 'candidate_cards' in messages[0]['content'] and payload['scope'] == 'chapter':
            proposal = json.loads(result.text)
            for candidate in proposal['candidate_cards']:
                template = next(row for row in candidate['members'] if row['kind'] == 'scene')
                for i in range(2, 5):
                    candidate['members'].append({**template, 'key': f'scene{i}'})
                    candidate['chapters'][0]['scenes'].append({'index': i, 'card': f'scene{i}', 'story_order': i})
            result.text = json.dumps(proposal, ensure_ascii=False)
        elif '{"operations"' in messages[0]['content'] and payload['disclosure_order'][:2] == [1, 1]:
            candidate = json.loads(result.text)
            character = next(card for card in payload['context']['settings'] if card['kind'] == 'character')
            candidate['operations'][0]['holder'] = character['card_id']
            result.text = json.dumps(candidate, ensure_ascii=False)
        return {'done': True, 'done_reason': 'stop', 'message': {'content': result.text}}

    transport['respond'] = respond

    def cli(*args):
        result = invoke(tmp_path, '--project', 'book', '--config', str(config), 'novel', *args)
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)

    def start(mode, limit, **fields):
        request = tmp_path / 'request.json'
        request.write_text(json.dumps({'mode': mode, **fields, 'budget': {
            'max_calls': limit, 'context_char_limit': 45000, 'output_limit': 2000}}), encoding='utf-8')
        return cli('start', '--request', str(request))['id']

    def choose(pending, action, **fields):
        choice = tmp_path / 'decision.json'
        choice.write_text(json.dumps({'step': pending['step'], 'token': pending['outputs']['gate']['token'],
                                      'action': action, 'reason': '逐场核对', **fields}), encoding='utf-8')
        return cli('resume', '--job', pending['id'], '--decision', str(choice))

    design = start('design', 2)
    pending = cli('resume', '--job', design)
    for scope in ('book', 'chapter'):
        assert pending['step'] == f'plan:{scope}:confirm'
        root = pending['outputs']['gate']['candidates'][0]['root']['card_id']
        pending = choose(pending, 'approve', root=root)
    assert pending['status'] == 'DONE'
    scenes = [item['scene_id'] for item in pending['outputs']['application']['chapters'][0]['scenes']]

    job = start('write', 12, scene_ids=scenes[:3])
    pending = cli('resume', '--job', job)
    assert pending['status'] == 'WAITING'
    assert len(model.calls) == 14
    assert '小钥匙' in model.calls[6][-1]['content']
    with Store(tmp_path / 'book') as store:
        assert not store.list('accepted')
    assert choose(pending, 'accept')['status'] == 'DONE'
    assert cli('show', '--job', job)['status'] == 'DONE'
    assert len(model.calls) == 14
    with Store(tmp_path / 'book') as store:
        assert len(store.list('accepted')) == 3
    assert len(list((tmp_path / 'book' / '正文').glob('*.md'))) == 3

    continuation = start('continue', 4)
    resumed = cli('resume', '--job', continuation)
    assert resumed['outputs']['scope']['scene_ids'] == [scenes[3]]
    assert '小钥匙' in model.calls[14][-1]['content']
