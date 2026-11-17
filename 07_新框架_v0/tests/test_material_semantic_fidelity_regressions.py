from nw.materials.semantic_fields import text_fields
from nw.materials.semantic_catalog import _fields


def test_explicit_empty_original_sections_are_accounted_without_inventing_a_rule():
    text='### 条目\n【定义】\n实际定义需要按具体对象使用。\n【调用条件】\n无\n【指令】\n- 无\n'
    clauses,_=text_fields(text)
    rows=_fields(text,text,{c['locator'] for c in clauses},'')
    assert not any(r['disposition'].startswith('unaccounted') for r in rows)
    assert len(clauses)==1


def test_a_real_sentence_before_a_rule_heading_must_not_be_dropped_as_formatting():
    text='**定义**：氛围类型与节奏类型匹配。\\*\\*匹配规则\\*\\*：\n'
    clauses,_=text_fields(text)
    assert any('氛围类型与节奏类型匹配' in c['value'] for c in clauses)
    assert not any(r['disposition'].startswith('unaccounted') for r in
        _fields(text,text,{c['locator'] for c in clauses},''))


def test_embedded_text_owner_prefix_does_not_hide_its_actual_clause_spans():
    from nw.materials.source_semantics import compile_semantics
    from nw.materials.semantic_catalog import _audit_record
    from nw.task_models import content_sha256
    text='**定义**：不同视角展示同一事件的不同侧面。\n**设计指令**：保持实际事件的因果一致。'
    pin={'id':'embedded-owner','locator':'/definition','sha256':'a'*64,'file_sha256':'b'*64,
         'byte_start':0,'byte_end':len(text.encode()),'line_start':1,'line_end':2}
    source={'source':pin,'source_state':'reference','original_text':text,
            'original_text_sha256':content_sha256(text),'application_layers':[],'source_issues':{}}
    context={'source_ref':pin}
    result=_audit_record(source,context,compile_semantics(source,context))
    assert result['fidelity_errors']==[]


def test_empty_bullet_is_accounted_but_keeps_its_original_missing_content_issue():
    text='【判定标准】\n\\- 场景内部不能全程匀速。\n\\- \r\n'
    clauses,issues=text_fields(text)
    assert len(clauses)==1
    assert any(i['kind']=='empty_original_bullet' and i['severity']=='repair' for i in issues)
    assert not any(r['disposition'].startswith('unaccounted') for r in
        _fields(text,text,{c['locator'] for c in clauses},''))
