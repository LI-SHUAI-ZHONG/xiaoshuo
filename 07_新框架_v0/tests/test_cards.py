from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
from threading import Barrier

import pytest

from nw.store import Store

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / '07_新框架_v0' / 'fixtures' / 'story_seed' / 'manifest.json'
RULE = {'card_id': 'rule-a', 'kind': 'rule', 'origin': 'author',
        'body': {'title': '证人', 'role': 'method', 'original_meaning': '证人影响可复查性',
                 'applies_when': '有可复查证词', 'excludes_when': '没有证词',
                 'operation': '记录证人的选择', 'counterexample': '旁白宣布',
                 'check': '有可定位证词', 'explanation': '证据与猜测分开'}}


def test_card_version_compare_and_append(tmp_path: Path) -> None:
    from nw.cards import CardConflict, read_card, save_card

    with Store(tmp_path, create=True) as store:
        first = save_card(store, RULE, None)
    barrier = Barrier(2)

    def append(title: str):
        card = deepcopy(RULE)
        card['body']['title'] = title
        with Store(tmp_path) as store:
            barrier.wait(5)
            try:
                return save_card(store, card, first.version)
            except CardConflict:
                return None

    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(append, ('左', '右')))
    [new] = [r for r in results if r]
    assert new.version == 2
    with Store(tmp_path) as store:
        assert read_card(store, first)['body']['title'] == '证人'
        assert read_card(store, new)['status'] == 'proposal'
        with pytest.raises(CardConflict):
            save_card(store, RULE, None)


def test_disabled_rule_keeps_frozen_reference(tmp_path: Path) -> None:
    from nw.cards import decide_card, decision_history, eligible_rule_refs, read_card, read_decision, save_card

    with Store(tmp_path, create=True) as store:
        first = save_card(store, RULE, None)
        assert eligible_rule_refs(store) == []
        decide_card(store, first, 'trial', '试用')
        assert eligible_rule_refs(store) == [first]
        disabled = decide_card(store, first, 'disabled', '暂停使用')
        assert eligible_rule_refs(store) == []
        assert read_card(store, first)['body']['title'] == '证人'
    with Store(tmp_path) as store:
        assert [d.decision for d in decision_history(store, first)] == ['trial', 'disabled']
        assert read_decision(store, disabled.id).reason == '暂停使用'


def test_pending_rule_revision_keeps_last_author_decision(tmp_path: Path) -> None:
    from nw.cards import decide_card, eligible_rule_refs, read_card, save_card

    with Store(tmp_path, create=True) as store:
        first = save_card(store, RULE, None)
        decide_card(store, first, 'approved', '采纳这一版')
        second = save_card(store, RULE, first.version)
        assert eligible_rule_refs(store) == [first]
        decide_card(store, second, 'trial', '试用新版')
        assert eligible_rule_refs(store) == [second]
        decide_card(store, second, 'disabled', '暂停这条规则')
        assert eligible_rule_refs(store) == []
        assert read_card(store, first)['status'] == 'approved'


def test_scene_and_character_preserve_design_fields(tmp_path: Path) -> None:
    from nw.cards import read_card, save_card

    character = {'card_id': 'char-1', 'kind': 'character', 'origin': 'author',
                 'body': {'name': '沈砚', 'role': '弟子', 'want': '复核异常',
                          'background': '外门', 'ability_cost': '清晰记忆', 'boundaries': '不擅自署名',
                          'independent_goal': '换回遗物'}}
    scene = {'card_id': 'scene-1', 'kind': 'scene', 'origin': 'author',
             'body': {'title': '档案廊', 'goal': '取得有限证据', 'pov': '沈砚', 'location': '档案廊',
                      'characters': ['char-1'], 'character_goals': {'char-1': '保全痕迹'},
                      'length_flexibility': '对手戏可以延长'}}
    with Store(tmp_path, create=True) as store:
        for card in (character, scene):
            ref = save_card(store, card, None)
            assert read_card(store, ref)['body'] == {'visibility': 'author_only', **card['body']}
        scene['body']['character_goals'] = {'char-1': False}
        with pytest.raises(ValueError, match='body'):
            save_card(store, scene, 1)


def test_repository_card_cannot_forge_source_or_approved_state(tmp_path: Path) -> None:
    from nw.cards import save_card

    with Store(tmp_path, create=True) as store:
        with pytest.raises(ValueError, match='source'):
            save_card(store, dict(RULE, origin='repository'), None)
        with pytest.raises(ValueError, match='proposal'):
            save_card(store, dict(RULE, status='approved'), None)
        with pytest.raises(ValueError, match='body'):
            save_card(store, dict(RULE, body={'title': '缺字段'}), None)


def test_unsourced_model_rule_stays_proposal_until_sourced_or_adopted(tmp_path: Path) -> None:
    from nw.cards import decide_card, eligible_rule_refs, save_card

    with Store(tmp_path, create=True) as store:
        ref = save_card(store, dict(RULE, origin='model'), None)
        with pytest.raises(ValueError, match='source'):
            decide_card(store, ref, 'trial', '暂用')
        assert eligible_rule_refs(store) == []
        author = save_card(store, RULE, ref.version)
        decide_card(store, author, 'trial', '作者采纳并负责')
        assert eligible_rule_refs(store) == [author]


def test_rule_definition_instruction_conflict_stays_proposal(tmp_path: Path) -> None:
    from nw.cards import decide_card, eligible_rule_refs, read_card, read_links
    from nw.sources import import_rule_cards, read_span

    with Store(tmp_path, create=True) as store:
        refs = import_rule_cards(store, MANIFEST, root=ROOT)
        assert len(refs) == 8 and eligible_rule_refs(store) == []
        correction = next(r for r in refs if r.card_id == 'rule-106.1-correction')
        links = read_links(store, correction)
        assert {link.relation for link in links} == {'interprets', 'corrects'}
        definition = next(link.target for link in links if link.relation == 'interprets')
        instruction = next(link.target for link in links if link.relation == 'corrects')
        from nw.story_models import SourceRef
        assert '叙述距离' in read_span(store, SourceRef(**read_card(store, definition)['source_refs'][0]))
        assert '身体信号' in read_span(store, SourceRef(**read_card(store, instruction)['source_refs'][0]))
        assert read_card(store, correction)['status'] == 'proposal'
        assert read_links(store, instruction)[0].target == definition
        with pytest.raises(ValueError, match='source-only'):
            decide_card(store, instruction, 'approved', '不应采用')


def test_import_never_overwrites_source_or_existing_versions(tmp_path: Path) -> None:
    from hashlib import sha256

    from nw.cards import read_card, save_card
    from nw.sources import import_seed_cards, read_span
    from nw.story_models import SourceRef

    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    paths = [ROOT / item['path'] for item in manifest['sources']]
    before = [sha256(path.read_bytes()).hexdigest() for path in paths]
    with Store(tmp_path, create=True) as store:
        refs = import_seed_cards(store, MANIFEST, root=ROOT)
        assert len(refs) == 13
        assert {read_card(store, r)['kind'] for r in refs} == {'rule', 'character', 'scene'}
        assert {read_card(store, r)['status'] for r in refs} == {'proposal'}
        assert not store.list('scene') and not store.list('draft')
        assert store.connection.execute('SELECT COUNT(*) FROM source_spans').fetchone()[0] == 13
        scene = next(r for r in refs if r.card_id == 'chaohen-scene-01')
        card = read_card(store, scene)
        assert '第七息回亮' in read_span(store, SourceRef(**card['source_refs'][0]))
        card['body']['title'] = '作者后来修订'
        edited = save_card(store, card, scene.version)
        assert import_seed_cards(store, MANIFEST, root=ROOT) == refs
        assert read_card(store, edited)['body']['title'] == '作者后来修订'
    assert [sha256(path.read_bytes()).hexdigest() for path in paths] == before


def test_rule_import_accepts_explicit_author_original(tmp_path: Path) -> None:
    from nw.cards import read_card
    from nw.sources import import_rule_cards

    data = json.loads(MANIFEST.with_name('cards.json').read_text(encoding='utf-8'))
    data['cards'].append({**RULE, 'status': 'proposal', 'sources': []})
    (tmp_path / 'cards.json').write_text(json.dumps(data), encoding='utf-8')
    manifest = tmp_path / 'manifest.json'
    manifest.write_bytes(MANIFEST.read_bytes())
    with Store(tmp_path / 'db', create=True) as store:
        refs = import_rule_cards(store, manifest, root=ROOT)
        assert len(refs) == 9
        author = read_card(store, next(ref for ref in refs if ref.card_id == RULE['card_id']))
        assert author['origin'] == 'author' and not author['source_refs']
        assert author['status'] == 'proposal'


def test_bad_last_card_rolls_back_preceding_cards_and_spans(tmp_path: Path) -> None:
    from nw.sources import import_seed_cards

    data = json.loads(MANIFEST.with_name('cards.json').read_text(encoding='utf-8'))
    data['cards'][-1]['body']['pov'] = False
    (tmp_path / 'cards.json').write_text(json.dumps(data), encoding='utf-8')
    manifest = tmp_path / 'manifest.json'
    manifest.write_bytes(MANIFEST.read_bytes())
    with Store(tmp_path / 'db', create=True) as store:
        with pytest.raises(ValueError, match='body'):
            import_seed_cards(store, manifest, root=ROOT)
        for table in ('cards', 'source_spans', 'source_versions'):
            assert store.connection.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] == 0


def test_invalid_span_aborts_import_without_partial_cards(tmp_path: Path) -> None:
    from nw.sources import import_seed_cards

    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    manifest['sources'][0]['spans'][-1]['sha256'] = '0' * 64
    path = tmp_path / 'bad.json'
    (tmp_path / 'cards.json').write_bytes(MANIFEST.with_name('cards.json').read_bytes())
    path.write_text(json.dumps(manifest), encoding='utf-8')
    with Store(tmp_path / 'db', create=True) as store:
        with pytest.raises(ValueError, match='hash'):
            import_seed_cards(store, path, root=ROOT)
        assert not store.connection.execute('SELECT * FROM cards').fetchall()
        assert not store.connection.execute('SELECT * FROM source_versions').fetchall()
