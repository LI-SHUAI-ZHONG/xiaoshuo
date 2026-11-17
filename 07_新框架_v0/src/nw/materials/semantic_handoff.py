"""Deliver source-bound upstream requirements to their actual named consumer."""
from copy import deepcopy

from nw.materials.phase_routes import REQUIRES,product_ref
from nw.materials.semantic_application import concrete,output_value,require
from nw.task_models import content_sha256


def handoffs_for(stage: str,products: dict) -> list[dict]:
    result=[]
    for origin,record in products.items():
        for criterion in record['products'].get('_criteria',[]):
            for clause in criterion['clauses']:
                if clause['consumer']!=stage or clause['applicability']!='applies':continue
                result.append({'id':'handoff:'+content_sha256({'origin':product_ref(record),
                    'source_id':criterion['source_id'],'clause_id':clause['id'],'consumer':stage}),
                    'source_id':criterion['source_id'],'clause_id':clause['id'],
                    'contract_sha256':criterion['contract_sha256'],'origin':product_ref(record),
                    'requirement':deepcopy(clause),
                    'actual_inputs':[{'path':r,'value':deepcopy(output_value(r,record['products']))}
                                     for r in clause['output_refs']]})
    return result


def input_stages(stage: str,products: dict,*,dynamic_screening: bool=False) -> list[str]:
    names=list(products) if stage=='bind_scope' else list(REQUIRES[stage])
    if stage=='state_propagation' and dynamic_screening:
        names[:0]=['type_selection','type_adaptation']
    for row in handoffs_for(stage,products):
        origin=row['origin']['stage']
        if origin not in names:names.append(origin)
    return names


def validate_handoffs(stage: str,value: dict,products: dict) -> None:
    expected={r['id'] for r in handoffs_for(stage,products)}
    receipts=value.get('_receipts',[]);seen=set()
    require(isinstance(receipts,list),'downstream receipts must be an explicit list')
    for row in receipts:
        require(isinstance(row,dict) and set(row)=={'id','operation','output_refs'}
                and row['id'] in expected-seen and concrete(row['operation'])
                and isinstance(row['output_refs'],list) and bool(row['output_refs']),
                'downstream must execute each received source clause on actual products')
        for ref in row['output_refs']:output_value(ref,value)
        seen.add(row['id'])
    require(seen==expected,'source-bound upstream requirements disappeared at their named consumer')
