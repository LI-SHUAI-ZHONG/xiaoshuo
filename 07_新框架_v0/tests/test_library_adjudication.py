"""Semantic-contract regression tests, isolated from all real catalog files."""
from hashlib import sha256
import json
import sqlite3

import pytest

from nw.materials.catalog import _SCHEMA, _fragment_rows
from nw.materials.fragments import Fragment
from nw.materials.library_adjudication import LibraryAdjudicator
from nw.materials.route_catalog import _FRAGMENTS, _UNITS
from nw.materials.unit_catalog import _SCHEMA as UNIT_SCHEMA, _row_units


LIBRARY_SHA = '1e4c7720fbc745ab952cd749c6faad03cff26c9a8e3f9bce5c4c5a6da91a36ed'
ANCHOR_SHA = '9b7ea71e53613a453fe71fa0a862411f65f22328a38ee7b97db7fd5bab7be759'


def catalog(text: str, key: str, *, family: str = 'library', kind: str = 'library_entry') -> tuple:
    db = sqlite3.connect(':memory:')
    db.row_factory = sqlite3.Row
    db.executescript(_SCHEMA + UNIT_SCHEMA)
    payload = text.encode('utf-8')
    digest = LIBRARY_SHA if family == 'library' else ANCHOR_SHA
    db.execute('INSERT INTO sources VALUES (?,?,?,?,?,?,?)',
               ('source', f'{family}.txt', digest, family, 'baseline', len(payload), 'INDEXED'))
    db.executemany('INSERT INTO fragments VALUES (?,?,?,?,?,?,?,?,?,?)',
                   _fragment_rows('source', payload, [Fragment(0, len(payload), kind, key)]))
    raw = db.execute('SELECT id,kind,key,byte_start,line_start,sha256,payload FROM fragments').fetchone()
    db.executemany('INSERT INTO material_units VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', _row_units(raw))
    root = dict(db.execute(_FRAGMENTS).fetchone())
    return db, root, LibraryAdjudicator(db)


def test_meaningful_original_contract_retains_all_boundaries() -> None:
    text = '''### 10.1_能量总量
【定义】角色可调用的能量储备，是能力发挥的基础。
【调用条件】本场使用角色的能量时。
【指令】总量必须有明确起点；战斗中变化必须有修炼、恢复或消耗的前因。
【例外处理】原文特殊恢复机制须单独说明来源。
【禁止清单】不能无因增加储备。
【判定标准】前后储备变化与消耗量一致。
'''
    db, root, adjudicator = catalog(text, '10.1_能量总量')
    result = adjudicator.review(root)
    assert result['state'] == 'design_ready'
    assert result['can_offer_for_design'] is True
    assert result['profile'] == 'world'
    assert result['contract']['owner_id'] == root['id']
    assert '前因' in result['contract']['directives'][0]['text']
    assert result['contract']['conditions'] and result['contract']['exceptions']
    assert result['contract']['checks'] and result['contract']['exclusions']
    assert result['source_refs'][0]['sha256'] == root['sha256']
    json.dumps(result, ensure_ascii=False)


def test_child_definition_has_root_contract_and_never_independent_readiness() -> None:
    db, root, adjudicator = catalog('''### 1.1_主角
【定义】承担核心视角与弧光的角色。
【指令】主角能力提升必须支付代价。
''', '1.1_主角')
    child = dict(db.execute(_UNITS + " WHERE u.kind='definition'").fetchone())
    result = adjudicator.review(child)
    assert result['state'] == 'context'
    assert result['owner_state'] == 'design_ready'
    assert result['owner_id'] == root['id']
    assert result['can_offer_for_design'] is False
    assert result['contract'] == adjudicator.review(root)['contract']


def test_real_semantic_conflict_blocks_whole_root_and_child_points_to_it() -> None:
    db, root, adjudicator = catalog('''### 106.1_全篇语言风格统一
**定义**：叙述语言（非对话）的风格在全篇保持一致。检查方法：对比不同章节的叙述语言。
**指令**：在场景中触发角色的全篇语言风格统一状态，通过指定身体信号呈现
**判定标准**：读者能否在1秒内通过身体信号识别出角色的全篇语言风格统一状态
''', '106.1_全篇语言风格统一')
    result = adjudicator.review(root)
    assert result['state'] == 'blocked'
    assert result['conflicts'][0]['kind'] == 'semantic_domain_conflict'
    assert len(result['conflicts'][0]['source_refs']) >= 2
    child = dict(db.execute(_UNITS + " WHERE u.kind='definition'").fetchone())
    assert adjudicator.review(child)['owner_state'] == 'blocked'


def test_placeholder_definition_is_not_promoted_by_template_fields() -> None:
    db, root, adjudicator = catalog('''## 板块87 规划师模式
### 输入
【定义】本章的规划输入信息。
【指令】本章的规划输入信息。
【示例】按流程执行
### 自检
【定义】规划完成后的检查。
【指令】规划完成后的检查。
''', '板块87 规划师模式', kind='library_block')
    result = adjudicator.review(root)
    assert result['state'] == 'reference'
    assert result['can_offer_for_design'] is False
    assert result['missing']


def test_subsections_cannot_borrow_a_neighbor_real_rule() -> None:
    db, root, adjudicator = catalog('''## 板块49 句子控制
### 句子长度控制
【定义】同一段落长短句交替。
【指令】同一段落避免连续三个同样长度句子。
### 短句使用时机
【定义】特定场景优先使用短句。
【指令】特定场景优先使用短句。
''', '板块49 句子控制', kind='library_block')
    assert adjudicator.review(root)['state'] == 'reference'


def test_embedded_foreign_contract_is_a_scope_conflict() -> None:
    db, root, adjudicator = catalog('''### 119.10_读者自反时刻
**定义**：读者反思自己与角色的选择差异。
**设计指令**：通过角色行为表现选择差异。
- **板块**：120.1
**定义**：视角切换的不同层级。
**设计指令**：切换后立即重置视角。
''', '119.10_读者自反时刻')
    assert any(c['kind'] == 'mixed_contract_scope' for c in adjudicator.review(root)['conflicts'])


def test_anchor_uses_original_cells_and_excludes_inline_upgrade() -> None:
    text = '| M1.1 | 道具_完整 | 道具处于完整状态 | 道具未被使用/未被损坏 | 物质 | <details><summary>运行层升级</summary>SECRET_UPGRADE</details>\n'
    db, root, adjudicator = catalog(text, 'M1.1', family='anchors', kind='anchor')
    result = adjudicator.review(root)
    assert result['state'] == 'design_ready'
    assert result['profile'] == 'anchor'
    assert result['conditions'] == ['道具未被使用/未被损坏']
    assert 'SECRET_UPGRADE' not in json.dumps(result, ensure_ascii=False)
    child = dict(db.execute(_UNITS + " WHERE u.kind='condition'").fetchone())
    assert adjudicator.review(child)['owner_id'] == root['id']


def test_anchor_generic_trigger_requires_author_definition() -> None:
    db, root, adjudicator = catalog('| M1.18 | 道具_特殊状态_1 | 道具处于异常状态 | 特殊事件触发 | 物质 |\n',
                                     'M1.18', family='anchors', kind='anchor')
    result = adjudicator.review(root)
    assert result['state'] == 'reference'
    assert result['missing']


def test_anchor_name_and_condition_contradiction_is_evidenced() -> None:
    db, root, adjudicator = catalog('| M3.5 | 资源_耗尽 | 资源完全用完 | 资源储备>0 | 物质 |\n',
                                     'M3.5', family='anchors', kind='anchor')
    result = adjudicator.review(root)
    assert result['state'] == 'blocked'
    assert result['conflicts'][0]['source_refs']


def test_nonoriginal_or_upgrade_cannot_be_offered() -> None:
    db, root, adjudicator = catalog('### 1.1_主角\n【定义】核心视角人物。\n【指令】必须有执念。\n', '1.1_主角')
    altered = dict(root, origin='upgrade')
    assert adjudicator.review(altered) is None
    altered = dict(root, file_sha256='f' * 64)
    assert adjudicator.review(altered)['can_offer_for_design'] is False


def test_material_mutation_invalidates_evidence_hash() -> None:
    db, root, adjudicator = catalog('### 1.1_主角\n【定义】核心视角人物。\n【指令】必须有执念。\n', '1.1_主角')
    db.execute('UPDATE fragments SET payload=?', (b'mutated',))
    with pytest.raises(ValueError, match='hash'):
        adjudicator.review(root)


def test_upgrade_only_anchor_heading_is_excluded() -> None:
    db, root, adjudicator = catalog('### ID1.1\n\n【运行层升级】\n\n```json\n{}\n```\n',
                                     'ID1.1', family='anchors', kind='anchor')
    result = adjudicator.review(root)
    assert result['state'] == 'reference'
    assert result['profile'] == 'upgrade_review'
    assert result['contract']['upgrade_only'] is True


def test_full_chapter_check_cannot_be_proved_from_scene_draft() -> None:
    db, root, adjudicator = catalog('''## 板块91 场景结构检查
### 场景数量
【定义】每章是否恰好4个场景。
【判定标准】每章必须有4个场景，否则重排。
''', '板块91 场景结构检查', kind='library_block')
    result = adjudicator.review(root)
    assert result['state'] == 'reference'
    child = dict(db.execute(_UNITS + " WHERE u.kind='embedded_block'").fetchone())
    scoped = adjudicator.review(child)
    assert scoped['profile'] == 'scope_review'
    assert scoped['contract']['evidence_scope']['kind'] == 'chapter'


def test_unlabelled_original_mapping_and_checklist_are_not_lost() -> None:
    db, root, adjudicator = catalog('''### 板块162 审美与板块的映射关系
**162.1 各板块对应的审美维度**
| 板块 | 对应审美维度 |
| 板块2（角色属性） | 外貌审美、动作审美 |
**162.2 审美检查清单**
每章编辑模式检查：
- [ ] 场景是否有空间结构和光线来源？
## 资料库原版条目补全
''', '板块162 审美与板块的映射关系', kind='library_block')
    result = adjudicator.review(root)
    assert result['contract']['definition']
    assert result['contract']['checks']
    assert result['state'] == 'reference'
    assert '条目补全' not in str(result['contract'])


def test_narrative_parameter_cannot_become_character_motivation() -> None:
    db, root, adjudicator = catalog('''### 109.1_叙述者类型
**定义**：全书使用的叙述者类型，包括第一人称和第三人称有限。
**设计指令**：将叙述者类型作为角色决策的深层驱动，通过行为而非旁白呈现
''', '109.1_叙述者类型')
    result = adjudicator.review(root)
    assert result['state'] == 'blocked'
    assert result['conflicts'][0]['kind'] == 'semantic_domain_conflict'


def test_true_embedded_original_number_owns_its_bounded_fields() -> None:
    db, root, adjudicator = catalog('''### 119.10_读者自反时刻
**定义**：读者反思自己与角色选择的区别。
**设计指令**：通过行为呈现选择的差别。
## 视角切换标记
- **条目类型**：规则型
- **板块**：120.5
**定义**：视角切换时必须立即标明新观察者和位置。
**指令**：切换后第一句交代新观察者的位置与当前动作。
''', '119.10_读者自反时刻')
    embedded = dict(db.execute(_UNITS + " WHERE u.kind='embedded_entry'").fetchone())
    result = adjudicator.review(embedded)
    assert embedded['key'].startswith('120.5_')
    assert result['state'] == 'design_ready'
    assert result['owner_id'] == embedded['id']
    child = dict(db.execute(_UNITS + " WHERE u.kind='definition' AND u.locator LIKE 'embedded/%'").fetchone())
    child_result = adjudicator.review(child)
    assert child_result['state'] == 'context'
    assert child_result['owner_id'] == embedded['id']
    assert child_result['contract'] == result['contract']
    assert adjudicator.review(root)['state'] == 'blocked'


def test_character_misbelief_can_coherently_drive_a_decision() -> None:
    db, root, adjudicator = catalog('''### 117.1_认知错位
**定义**：角色A认为B是朋友，B实际是敌人。写作规则：认知错位是对话冲突的来源。
**设计指令**：将认知错位作为角色决策的深层驱动，通过行为而非旁白呈现
''', '117.1_认知错位')
    result = adjudicator.review(root)
    assert result['state'] == 'design_ready'
    assert result['conflicts'] == []


def test_reader_unknowns_cannot_directly_become_character_knowledge() -> None:
    db, root, adjudicator = catalog('''### 116.2_读者未知信息
**定义**：读者不知道的事，制造悬念。写作规则：读者未知信息是核心悬念的来源。
**设计指令**：将读者未知信息作为角色决策的深层驱动，通过行为而非旁白呈现
''', '116.2_读者未知信息')
    assert adjudicator.review(root)['state'] == 'blocked'


def test_literal_subsections_keep_local_and_cross_chapter_requirements_separate() -> None:
    db, root, adjudicator = catalog('''### 板块161 未写明的审美维度
**161.1 对比审美**
【定义】通过新旧、强弱、明暗的反差制造审美张力。
【调用条件】场景转换、角色对比、时间跨度处使用。
【指令】对比通过切换呈现，不能直接点明。
【判定标准】读者能从明暗变化中感到落差。
**161.2 节奏审美**
【定义】语言和叙事的快慢交替产生韵律。
【指令】重章后必须接轻章。
【判定标准】读者感知到章节之间的节奏变化。
''', '板块161 未写明的审美维度', kind='library_block')
    children = [dict(row) for row in db.execute(_UNITS + " WHERE u.kind='embedded_entry' ORDER BY u.byte_start")]
    assert [row['key'] for row in children] == ['161.1_对比审美', '161.2_节奏审美']
    local, whole_book = [adjudicator.review(row) for row in children]
    assert local['state'] == 'design_ready'
    assert '节奏' not in str(local['contract'])
    assert whole_book['state'] == 'design_ready'
    assert whole_book['profile'] == 'scope_review'
    assert whole_book['contract']['evidence_scope']['kind'] == 'cross_chapter'
    assert adjudicator.review(root)['state'] == 'reference'


def test_unnumbered_original_subsection_keeps_scoped_title_without_inventing_number() -> None:
    db, root, adjudicator = catalog('''## 板块49 句子控制
### 句子长度控制
【定义】长短句交替形成不同阅读速度。
【指令】避免连续三个相同长度句子。
### 短句使用时机
【定义】动作发生时短句加速。
【指令】动作冲突处使用短句，不能使因果丢失。
''', '板块49 句子控制', kind='library_block')
    children = [dict(row) for row in db.execute(_UNITS + " WHERE u.kind='embedded_block' ORDER BY u.byte_start")]
    assert [row['key'] for row in children] == ['板块49 句子控制#句子长度控制', '板块49 句子控制#短句使用时机']
    assert all(adjudicator.review(row)['state'] == 'design_ready' for row in children)
    assert adjudicator.review(root)['can_offer_for_design'] is False


def test_fenced_metadata_example_cannot_become_an_original_rule() -> None:
    db, root, adjudicator = catalog('''### 128.1_示例格式
【定义】下面展示资料记录的格式。
【指令】必须核对真实来源，不能把示例格式作为原始规则。
```markdown
## 假规则
- **条目类型**：规则型
- **板块**：120.5
**定义**：假定义。
**指令**：假指令必须通过。
```
''', '128.1_示例格式')
    assert db.execute("SELECT count(*) FROM material_units WHERE kind='embedded_entry'").fetchone()[0] == 0
