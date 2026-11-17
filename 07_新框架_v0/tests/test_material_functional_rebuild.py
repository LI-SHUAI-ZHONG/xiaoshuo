"""Usable source fields survive isolated metadata defects without inventing data."""
from nw.materials.adjudication import Adjudicator
from test_type_adjudication import catalog, genre, root


def test_adaptation_uses_its_own_identity_instead_of_the_referenced_type(tmp_path):
    value = {'adaptation_id': 'ADAPT_ONE', 'type_id': 'GENRE_ONE', 'status': 'active'}
    db, rows, _ = catalog(tmp_path, {'类型表达适配总表.json': [value]})
    try:
        assert root(rows, '类型表达适配总表.json')['key'] == 'ADAPT_ONE'
    finally:
        db.close()


def test_active_definition_survives_quarantined_confidence_without_changing_original(tmp_path):
    value = genre()
    value['confidence'] = 999
    db, rows, raw = catalog(tmp_path, {'主类型.json': [value]})
    try:
        owner = root(rows, '主类型.json')
        assert raw.review(owner)['state'] == 'blocked'
        rebuilt = Adjudicator(db, tmp_path).review(owner)
        assert rebuilt['state'] == 'design_ready'
        repair = rebuilt['source_retranslation']
        assert repair['original_state'] == 'blocked'
        assert repair['quarantined_fields'][0]['original_value'] == 999
        assert 'confidence' not in rebuilt['contract']['evidence']
        assert raw.records[owner['id']][1]['confidence'] == 999
    finally:
        db.close()


def test_combination_keeps_actual_dependency_rules_when_only_score_is_invalid(tmp_path):
    adaptation = {'adaptation_id': 'ADAPT_ONE', 'type_id': 'GENRE_ONE',
                  'description': '该类型的受限视角表达选择', 'preferred_expressions': ['只写当前观察者所知'],
                  'avoid_expressions': ['无来源泄露秘密'], 'not_guaranteed': ['不保证每场使用'],
                  'status': 'active', 'confidence': 999}
    combo = {'combination_id': 'COMBO_ONE', 'primary_type_id': 'GENRE_ONE', 'type_ids': ['GENRE_ONE'],
             'adaptation_ids': ['ADAPT_ONE'], 'description': '通过受限视角兑现规则探索', 'status': 'active'}
    db, rows, _ = catalog(tmp_path, {'主类型.json': [genre()], '类型表达适配总表.json': [adaptation],
                                   '类型组合总表.json': [combo]})
    try:
        result = Adjudicator(db, tmp_path).review(root(rows, '类型组合总表.json'))
        assert result['state'] == 'design_ready'
        deps = result['contract']['dependency_contracts']
        dep = next(r for r in deps if r['source_ref']['key'] == 'ADAPT_ONE')
        assert dep['effective_original']['avoid_expressions'] == ['无来源泄露秘密']
        assert 'confidence' not in dep['effective_original']
        assert any(f['label'] == 'avoid_expressions' for f in result['contract']['obligations'])
    finally:
        db.close()


def test_missing_meaning_is_not_restored_by_discarding_invalid_metadata(tmp_path):
    value = genre()
    value.update(definition='类型一', confidence=999)
    db, rows, _ = catalog(tmp_path, {'主类型.json': [value]})
    try:
        assert not Adjudicator(db, tmp_path).review(root(rows, '主类型.json'))['can_offer_for_design']
    finally:
        db.close()


def test_template_dependency_is_still_blocked_even_with_an_invalid_score(tmp_path):
    combo = {'combination_id': 'COMBO_ONE', 'primary_type_id': 'GENRE_ONE', 'type_ids': ['GENRE_ONE'],
             'dynamic_rule_ids': ['RULE_ONE'], 'description': '组合仍需真实触发机制', 'status': 'active'}
    method = {'rule_id': 'RULE_ONE', 'status': 'template', 'confidence': 999}
    db, rows, _ = catalog(tmp_path, {'主类型.json': [genre()], '类型组合总表.json': [combo],
                                   '类型动态规则总表.json': [method]})
    try:
        assert not Adjudicator(db, tmp_path).review(root(rows, '类型组合总表.json'))['can_offer_for_design']
    finally:
        db.close()


def test_active_but_incomplete_dependency_blocks_score_only_reconstruction(tmp_path):
    combo = {'combination_id': 'COMBO_ONE', 'primary_type_id': 'GENRE_ONE', 'type_ids': ['GENRE_ONE'],
             'dynamic_rule_ids': ['RULE_ONE'], 'description': '组合不能绕过原始动态规则的语义缺口',
             'status': 'active', 'confidence': 999}
    method = {'rule_id': 'RULE_ONE', 'status': 'active'}
    db, rows, _ = catalog(tmp_path, {'主类型.json': [genre()], '类型组合总表.json': [combo],
                                   '类型动态规则总表.json': [method]})
    try:
        result = Adjudicator(db, tmp_path).review(root(rows, '类型组合总表.json'))
        assert not result['can_offer_for_design']
        assert any('RULE_ONE' in text for text in result['missing'])
    finally:
        db.close()


def test_functional_rebuild_does_not_restore_nested_legacy_authority(tmp_path):
    value=genre(validation_requirements={'minimum':'必须验证真实效果',
        'runtime_calling_layer':{'authority':'OLD_APPROVED_MUST_NOT_LEAK'}})
    value['confidence']=999
    db,rows,_=catalog(tmp_path,{'主类型.json':[value]})
    try:
        result=Adjudicator(db,tmp_path).review(root(rows,'主类型.json'))
        import json
        assert 'OLD_APPROVED_MUST_NOT_LEAK' not in json.dumps(result['contract'],ensure_ascii=False)
    finally:
        db.close()


def test_mutual_exclusions_are_boundaries_and_do_not_form_execution_cycles(tmp_path):
    rules=[{'rule_id':name,'rule_scope':'资源变化后重新选择行动','trigger_concepts':['资源变化'],
            'candidate_effects':[{'description':'增加一种可选行动'}], 'preconditions':['当前资源已变化'],
            'selection_constraints':['仍须由人物选择'], 'not_guaranteed':['不保证选择发生'],
            'excludes_rules':[other],'status':'active'} for name,other in [('RULE_A','RULE_B'),('RULE_B','RULE_A')]]
    db,rows,_=catalog(tmp_path,{'类型动态规则总表.json':rules})
    try:
        engine=Adjudicator(db,tmp_path)
        for row in [r for r in rows if r['kind']=='record']:
            result=engine.review(row)
            assert result['can_offer_for_design'],result['missing']
            assert not result['contract']['obligations'] or all(
                f['owner_id']==row['id'] for f in result['contract']['obligations'])
    finally:
        db.close()


def test_complete_candidate_effect_is_usable_with_its_exact_parent_method(tmp_path):
    rule={'rule_id':'RULE_ONE','rule_scope':'资源变化后重新选择行动','trigger_concepts':['资源变化'],
          'candidate_effects':[{'description':'增加一种可选行动'}], 'preconditions':['资源已变化'],
          'selection_constraints':['仍须由人物选择'], 'not_guaranteed':['不保证选择发生'],'status':'active'}
    effect={'effect_id':'EFFECT_ONE','rule_id':'RULE_ONE','target_id':'角色当前目标',
            'change_field':'attention','candidate_value':'重新审视目标','status':'active'}
    combo={'combination_id':'COMBO_ONE','primary_type_id':'GENRE_ONE','type_ids':['GENRE_ONE'],
           'dynamic_rule_ids':['RULE_ONE'],'candidate_effect_ids':['EFFECT_ONE'],
           'description':'通过条件化方法提出注意方向候选','status':'active'}
    db,rows,_=catalog(tmp_path,{'主类型.json':[genre()],'类型组合总表.json':[combo],
            '类型动态规则总表.json':[rule],'类型动态候选效果.json':[effect]})
    try:
        result=Adjudicator(db,tmp_path).review(root(rows,'类型组合总表.json'))
        assert result['can_offer_for_design'],result['missing']
        assert any(r['role']=='parent_bound_auxiliary' for r in result['contract']['dependency_contracts'])
    finally:
        db.close()


def test_complete_combination_candidate_can_enter_proposal_without_becoming_active(tmp_path):
    combo={'combination_id':'COMBO_ONE','primary_type_id':'GENRE_ONE','type_ids':['GENRE_ONE'],
           'description':'通过明确规则的代价形成类型困境','status':'candidate','selection_status':'candidate'}
    db,rows,raw=catalog(tmp_path,{'主类型.json':[genre()],'类型组合总表.json':[combo]})
    try:
        owner=root(rows,'类型组合总表.json')
        assert raw.review(owner)['state']=='reference'
        result=Adjudicator(db,tmp_path).review(owner)
        assert result['can_offer_for_design']
        assert result['contract']['effective_original']['status']=='candidate'
        assert result['source_retranslation']['adoption_scope']=='proposal_only'
    finally:
        db.close()


def test_empty_declared_avoid_list_does_not_discard_actual_expression_preferences(tmp_path):
    adaptation={'adaptation_id':'ADAPT_ONE','type_id':'GENRE_ONE','status':'active','confidence':999,
                'preferred_expressions':['通过修行资源呈现体力消耗'],'avoid_expressions':[],
                'not_guaranteed':['不保证人物必然采取该行动']}
    db,rows,_=catalog(tmp_path,{'主类型.json':[genre()],'类型表达适配总表.json':[adaptation]})
    try:
        assert Adjudicator(db,tmp_path).review(root(rows,'类型表达适配总表.json'))['can_offer_for_design']
    finally:
        db.close()
