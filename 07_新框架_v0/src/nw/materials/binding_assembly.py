"""Assembly cannot replace execution in the source's reviewed workflow step."""
from nw.materials.binding import COMMON
from nw.materials.binding_reviews import POLICY,require,reviewed_source
from nw.materials.phase_routes import ORDER,EXTERNAL_REQUIRES
from nw.materials.work_catalog import SourceDesk


def freeze_required_sources(desk: SourceDesk,materials: list[dict],context: dict) -> None:
    for material in materials:
        if material['request']['disposition']!='required':continue
        source=desk.read(material['source']['id']);review=desk.binding_review(source)
        if review is None:
            raise ValueError('MATERIAL_WAITING_INPUTS: required source workflow binding needs_review: '+source['source']['id'])
        context['material_source_snapshots'][source['source']['id']]=source
        context['binding_reviews'][source['source']['id']]=review


def configured_sources(value: dict) -> set[str]:
    """Read the existing book/scene binding shapes, excluding explicit deferrals."""
    result=set()
    def add(ident: str,body: object) -> None:
        if isinstance(body,dict) and body.get('disposition') not in ('deferred','not_applicable'):
            result.add(ident)
    for key,body in value.get('material_bindings',{}).items():
        if not isinstance(body,dict):continue
        if COMMON<=body.keys() or 'disposition' in body:add(key,body)
        else:
            for ident,binding in body.items():add(ident,binding)
    for ident,body in value.get('process_bindings',{}).items():add(ident,body)
    return result


def validate_assembly(value: dict,products: dict,sources: list[dict],context: dict) -> None:
    if context.get('binding_policy')!=POLICY:return
    snapshots={**{s['source']['id']:s for s in context.get('method_sources',[])},
        **{s['source']['id']:s for s in sources},**context.get('material_source_snapshots',{})}
    uses={(r['stage'],u['source_id']) for r in products.values() for u in r['products'].get('_uses',[])}
    uses.update(('bind_scope',u['source_id']) for u in value.get('_uses',[]))
    for ident in configured_sources(value):
        require(ident in snapshots,'binding assembly lacks the actual original source snapshot')
        review=reviewed_source(snapshots[ident],context.get('binding_reviews',{}),
            test_mode=context.get('binding_test_mode') is True)
        require(review is not None,'binding assembly has no source/workflow use review')
        stages={u['stage'] for u in review['uses'] if context.get('scope') in
            u.get('scopes',['book','volume','chapter','scene','replan'])}
        require(bool(stages),'binding assembly lacks the required project scope inputs')
        if stages & set(ORDER):
            require(any((stage,ident) in uses for stage in stages & set(ORDER)),
                'binding assembly added a method not executed in its reviewed step: '+ident)
        elif stages=={'retrieval'}:
            control=context.get('retrieval_control',{})
            require(control.get('source',{}).get('source',{}).get('id')==ident and
                control.get('review',{}).get('sha256')==review['sha256'],
                'binding assembly cannot replace the pre-step retrieval control')
        else:
            require(stages<=EXTERNAL_REQUIRES.keys(),
                'binding assembly has an unknown execution consumer')
            # Writer/review/acceptance configuration is not evidence of execution.
