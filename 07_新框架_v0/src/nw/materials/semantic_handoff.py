"""Deliver source-bound upstream requirements to their actual named consumer."""
from copy import deepcopy

from nw.materials.phase_routes import REQUIRES,product_ref
from nw.materials.semantic_application import concrete,output_value,require
from nw.task_models import content_sha256


def handoffs_for(stage: str,products: dict) -> list[dict]:
    result=[]
    for origin,record in products.items():
        for criterion in record['products'].get('_criteria',[]):
            bindings=criterion.get('layer_application',{}).get('bindings',[])
            for clause in criterion['clauses']:
                if clause['consumer']!=stage or clause['applicability']!='applies':continue
                handoff={'id':'handoff:'+content_sha256({'origin':product_ref(record),
                    'source_id':criterion['source_id'],'clause_id':clause['id'],'consumer':stage}),
                    'source_id':criterion['source_id'],'clause_id':clause['id'],
                    'contract_sha256':criterion['contract_sha256'],'origin':product_ref(record),
                    'requirement':deepcopy(clause),
                    'actual_inputs':[{'path':r,'value':deepcopy(output_value(r,record['products']))}
                                     for r in clause['output_refs']]}
                if related := [row for row in bindings if row['clause_id']==clause['id']]:
                    handoff['network_layer_bindings']=deepcopy(related)
                result.append(handoff)
    return result


def input_stages(stage: str,products: dict,*,dynamic_screening: bool=False) -> list[str]:
    names=list(products) if stage=='bind_scope' else list(REQUIRES[stage])
    if stage=='state_propagation' and dynamic_screening:
        names[:0]=['type_selection','type_adaptation']
    for row in handoffs_for(stage,products):
        origin=row['origin']['stage']
        if origin not in names:names.append(origin)
    return names


def validate_handoffs(stage: str,value: dict,products: dict,context: dict | None = None) -> None:
    expected={r['id']:r for r in handoffs_for(stage,products)}
    from nw.materials.world_market import POLICY as MARKET_POLICY
    from nw.materials.world_history import POLICY as HISTORY_POLICY, check_history_receipt
    world_sources = {}
    if expected and context and (context.get('world_market_policy') == MARKET_POLICY
                                 or context.get('world_history_policy') == HISTORY_POLICY):
        world_sources = {row['source']['id']: row['source']['key'] for row in context.get('method_sources', [])
                          if row['source']['id'] in context.get('world_network_bases', {})}
    receipts=value.get('_receipts',[]);seen=set()
    require(isinstance(receipts,list),'downstream receipts must be an explicit list')
    for row in receipts:
        require(isinstance(row,dict) and set(row)=={'id','operation','output_refs'}
                and row['id'] in expected and row['id'] not in seen and concrete(row['operation'])
                and isinstance(row['output_refs'],list) and bool(row['output_refs']),
                'downstream must execute each received source clause on actual products')
        fields = [output_value(ref, value) for ref in row['output_refs']]
        handoff = expected[row['id']]
        if key := world_sources.get(handoff['source_id']):
            from nw.materials.world_market_receipts import check_market_receipt
            check_market_receipt(handoff, fields, products, context, key)
            check_history_receipt(handoff, row['output_refs'], value, products, context, key)
        seen.add(row['id'])
    require(seen==expected.keys(),'source-bound upstream requirements disappeared at their named consumer')
