"""Only a source-pinned, explained retranslation can replace defective fields."""
from nw.materials.adjudication import Adjudicator
from nw.materials import retranslations
from nw.materials.route_catalog import _UNITS
from test_material_layers import layer_catalog


def test_definition_based_retranslation_preserves_defect_and_replaces_wrong_domain(tmp_path,monkeypatch):
    db,root=layer_catalog(procedural=True)
    definition=dict(db.execute(_UNITS+" WHERE u.kind='definition'").fetchone())
    monkeypatch.setitem(retranslations.REPAIRS,root['id'],{
        'file_sha256':root['file_sha256'],'sha256':root['sha256'],
        'definition_id':definition['id'],'definition_sha256':definition['sha256'],
        'evidence_scope':'book','reason':'根据原定义中的跨章语言比较修复错位的执行指令'})
    result=Adjudicator(db,tmp_path).review(root)
    assert result['profile']=='scope_review'
    assert result['contract']['evidence_scope']['kind']=='book'
    assert result['contract']['obligations'][0]['id']==definition['id']
    assert len(result['contract']['obligations'])==1
    assert result['source_retranslation']['excluded_fields']
    assert result['source_retranslation']['original_state']=='design_ready'
    assert result['source_retranslation']['method']=='definition_grounded_retranslation'
    assert result['layer_contract']['execution']['domain']=='narration'


def test_retranslation_pin_does_not_transfer_to_other_source_versions(tmp_path,monkeypatch):
    db,root=layer_catalog(procedural=True)
    monkeypatch.setitem(retranslations.REPAIRS,root['id'],{'file_sha256':'f'*64,'sha256':root['sha256']})
    result=Adjudicator(db,tmp_path).review(root)
    assert not result.get('source_retranslation')
