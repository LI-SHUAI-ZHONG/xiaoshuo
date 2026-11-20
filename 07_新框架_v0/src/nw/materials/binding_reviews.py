"""Reviewed source uses; discovery labels never grant execution admission."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

from nw.task_models import canonical,content_sha256

POLICY='workflow-source-binding-v1'
ROOT=Path(__file__).resolve().parents[4]
BUNDLED=Path(__file__).resolve().parents[3]/'fixtures/material_semantics/workflow_bindings.json'
WORKFLOWS={'08_工作流设计/小说工作流设计_v1.md',
           '08_工作流设计/05_小说资料全量融入计划_v1.md'}


def allows_stage_candidate(source: dict, stage: str, context: dict) -> bool:
    """Reuse existing qualification for proposals in the original workflow."""
    if not context.get('current_source_set') or source['source']['id'] in context.get('binding_reviews', {}):
        return False
    from nw.materials.phase_routes import ORDER, phase_order, route_method
    if stage not in ORDER or stage not in phase_order(context['scope']):
        return False
    ref = source['source']
    if source.get('source_state') != 'design_ready' or source.get('use_mode') != 'project_method':
        return False
    if any(source.get('source_issues', {}).values()):
        return False
    if ref.get('profile') in {'metadata','legacy','editor','character_editor','prose_review',
                               'scope_review','continuity','material_selection','material_conversion'}:
        return False
    if ref.get('path','').endswith('/类型连接.txt'):
        from nw.materials.steps.type_connections import allows_adaptation
        return stage == 'type_adaptation' and allows_adaptation(source,context.get('type_selection',{}))
    from nw.materials.network_workflow import prepared_static_source
    if prepared_static_source(source, stage, context):
        return True
    return stage in route_method(source)['stages']


def require(ok: bool,reason: str) -> None:
    if not ok:raise ValueError('MATERIAL_BINDING: '+reason)


def validate_review(source: dict,review: dict,*,test_mode: bool=False) -> dict:
    require(isinstance(review,dict) and review.get('policy')==POLICY,'missing original-workflow binding review')
    fixture=review.get('scope')=='isolated_protocol_fixture'
    require(not fixture or test_mode,'fixture interpretation is forbidden outside an isolated test store')
    require(review.get('scope') in {'source_workflow_review','isolated_protocol_fixture'},'unknown binding review authority')
    pin=source['source'];expected=review.get('source',{})
    require(all(expected.get(k)==pin.get(k) for k in ('id','sha256','file_sha256')),
            'binding review belongs to another source/version')
    require(review.get('original_text_sha256')==content_sha256(source['original_text']),
            'binding original text changed')
    quotes=review.get('source_quotes')
    require(isinstance(quotes,list) and bool(quotes) and all(isinstance(q,str) and len(q.strip())>=8
            and q in source['original_text'] for q in quotes),'binding lacks exact original clauses')
    uses=review.get('uses');require(isinstance(uses,list) and bool(uses),'binding review has no actual use')
    from nw.materials.phase_routes import ORDER,EXTERNAL_REQUIRES
    for use in uses:
        require(isinstance(use,dict) and use.get('stage') in (*ORDER,*EXTERNAL_REQUIRES,'retrieval')
                and all(isinstance(use.get(k),str) and len(use[k].strip())>=8
                    for k in ('purpose','prerequisites','products','downstream_check')),
                'review must specify purpose, prerequisites, products and downstream check')
    clauses=review.get('clause_reviews')
    require(isinstance(clauses,list) and bool(clauses),'binding review lacks clause-level scope')
    for clause in clauses:
        left,right=clause.get('text_start'),clause.get('text_end')
        require(type(left) is int and type(right) is int and 0<=left<right<=len(source['original_text'])
                and sha256(source['original_text'][left:right].encode('utf-8')).hexdigest()==clause.get('sha256')
                and clause.get('status') in {'reviewed','needs_review','not_project_instruction'} and clause.get('reason'),
                'binding review clause scope/version is invalid')
    refs=review.get('workflow_refs')
    require(isinstance(refs,list) and (fixture or bool(refs)),'binding lacks original workflow evidence')
    for ref in refs:
        require(ref.get('path') in WORKFLOWS,'binding cites an unapproved workflow substitute')
        raw=(ROOT/ref['path']).read_bytes();text=raw.decode('utf-8-sig')
        require(sha256(raw).hexdigest()==ref.get('sha256'),'original workflow version changed')
        require(isinstance(ref.get('quote'),str) and len(ref['quote'].strip())>=8
                and ref['quote'] in text,'binding workflow quote is missing or altered')
    require(review.get('sha256')==content_sha256({k:v for k,v in review.items() if k!='sha256'}),
            'binding review content changed')
    return review


def load_reviews(workspace: Path,*,test_mode: bool=False) -> dict:
    result={}
    paths=[BUNDLED,workspace/'materials/workflow_binding_reviews.json']
    for path in paths:
        if not path.is_file():continue
        data=json.loads(path.read_text(encoding='utf-8'))
        require(data.get('policy')==POLICY and isinstance(data.get('reviews'),list),'invalid binding review ledger')
        for entry in data['reviews']:
            if entry.get('scope')=='isolated_protocol_fixture':
                if not test_mode:continue
            ident=entry.get('source',{}).get('id')
            require(isinstance(ident,str) and ident not in result,'ambiguous source binding review')
            result[ident]=entry
    return result


def reviewed_source(source: dict,reviews: dict,*,test_mode: bool=False,stage: str | None=None,
                    scope: str | None=None) -> dict | None:
    review=reviews.get(source['source']['id'])
    if review is None:return None
    validate_review(source,review,test_mode=test_mode)
    if stage is not None and not any(u['stage']==stage and
            (scope is None or scope in u.get('scopes',['book','volume','chapter','scene','replan']))
            for u in review['uses']):return None
    return deepcopy(review)


def validate_execution_binding(stage: str,source: dict,context: dict) -> dict | None:
    if context.get('binding_policy')!=POLICY:return None
    review=reviewed_source(source,context.get('binding_reviews',{}),
        test_mode=context.get('binding_test_mode') is True,stage=stage,scope=context.get('scope'))
    require(review is not None or allows_stage_candidate(source,stage,context),
            'source use has no reviewed binding or eligible original for this workflow step')
    return review


def model_review(review: dict,contract: dict,stage: str) -> dict:
    decisions=[]
    for clause in contract['obligations']:
        ref=clause['source_ref']
        scope=next((c for c in review['clause_reviews'] if c['text_start']==ref['text_start']
            and c['text_end']==ref['text_end'] and c['sha256']==ref['clause_sha256']),None)
        decisions.append({'id':clause['id'],'status':scope['status'] if scope else 'needs_review',
            'reason':scope['reason'] if scope else '原句未有用途审核',
            'semantic_role':scope.get('semantic_role') if scope else None})
    return {'source_id':review['source']['id'],'review_sha256':review['sha256'],
        'authority':'reviewed_use_not_project_effect_pass','uses':[u for u in review['uses'] if u['stage']==stage],
        'clause_decisions':decisions}


def verify_session_bindings(session: dict,workspace: Path,*,test_mode: bool=False) -> None:
    from nw.materials.binding_assembly import configured_sources,validate_assembly
    uses=[(r['stage'],u['source_id']) for r in session['stages'] for u in r['products'].get('_uses',[])]
    selection=next((row['products'] for row in session['stages'] if row['stage']=='type_selection'),{})
    context={**session['context'],'type_selection':selection}
    control=context.get('retrieval_control')
    binder=next((r['products'] for r in session['stages'] if r['stage']=='bind_scope'),{})
    configured=configured_sources(binder)
    if not uses and not control and not configured:return
    require(context.get('binding_policy')==POLICY,'historical candidate routes need review before new execution')
    fresh=load_reviews(workspace,test_mode=test_mode)
    sources={**context.get('material_source_snapshots',{}),**{s['source']['id']:s for s in session['sources']}}
    if context.get('current_source_set'):
        from nw.materials.source_set import selection_status
        selected=selection_status(workspace)
        require(selected is not None and selected['sha256']==context['current_source_set'],
                'the selected material version changed')
    from nw.materials.network_workflow import POLICY as NETWORK_POLICY, resolve_type_scope
    if context.get('network_prerequisite_policy') == NETWORK_POLICY:
        from nw.materials.type_network import POLICY as TYPE_NETWORK_POLICY

        typed = context.get('type_network_policy') == TYPE_NETWORK_POLICY
        families = {} if typed else None
        require(context.get('network_type_scope') == resolve_type_scope(workspace, selection, families=families),
                'dynamic network type scope differs from the selected original types')
        if typed:
            require(context.get('type_network_families') == families, 'verified main-type families changed')
            bases = context.get('type_network_bases', {})
            offered = {ident for row in session['stages'] if row['stage'] == 'type_adaptation'
                       for ident in row['source_ids'] if ident in bases}
            if offered:
                from nw.materials.type_network_catalog import edge_proof
                from nw.materials.work_catalog import SourceDesk

                desk = SourceDesk(workspace, test_mode=test_mode)
                for ident in sorted(offered):
                    require(edge_proof(sources[ident], desk.read(bases[ident]['static_id'])) == bases[ident],
                            'type adaptation static source changed or could no longer be verified')
    if control:
        review=reviewed_source(control['source'],fresh,test_mode=test_mode,stage='retrieval')
        require(review is not None and canonical(review)==canonical(control['review']),'retrieval control changed')
        from nw.materials.work_catalog import SourceDesk
        SourceDesk(workspace,test_mode=test_mode).verify([control['source']])
    for ident in configured:
        require(ident in sources,'binding assembly lacks its frozen original')
        current=reviewed_source(sources[ident],fresh,test_mode=test_mode)
        require(current is not None and canonical(current)==canonical(context.get('binding_reviews',{}).get(ident)),
            'configured source/workflow review changed or disappeared')
    if configured:
        from nw.materials.work_catalog import SourceDesk
        SourceDesk(workspace,test_mode=test_mode).verify([sources[i] for i in configured])
        validate_assembly(binder,{r['stage']:r for r in session['stages'] if r['stage']!='bind_scope'},
            list(sources.values()),{**context,'binding_test_mode':test_mode})
    for stage,ident in uses:
        current=reviewed_source(sources[ident],fresh,test_mode=test_mode,stage=stage,scope=context.get('scope'))
        expected=context.get('binding_reviews',{}).get(ident)
        require(canonical(current)==canonical(expected) and
                (current is not None or ident not in fresh and allows_stage_candidate(sources[ident],stage,context)),
                'source/workflow binding review changed or disappeared')
        validate_execution_binding(stage,sources[ident],{**context,'binding_test_mode':test_mode})


def audit_bindings(workspace: Path,*,details: bool=False) -> dict:
    """Account for reviewed uses without calling them project usage or effect passes."""
    from collections import Counter
    from nw.materials.work_catalog import SourceDesk
    desk=SourceDesk(workspace);rows=[];states=Counter();issues=[]
    use_count=creative=controls=0
    for row in desk.rows:
        entry=desk.binding_reviews.get(row['id']);status='discovery_only';uses=[]
        if entry is not None:
            try:
                source=desk.read(row['id']);entry=validate_review(source,entry)
                status='reviewed_use_available';uses=entry['uses'];use_count+=len(uses)
                creative+=any(u['stage']!='retrieval' for u in uses)
                controls+=any(u['stage']=='retrieval' for u in uses)
            except ValueError as exc:
                issues.append({'source_id':row['id'],'reason':str(exc)});status='review_stale'
        states[status]+=1
        rows.append({'source_id':row['id'],'key':row['key'],'profile_for_discovery':row['profile'],
            'source_qualification':row['state'],'source_sha256':row['sha256'],
            'binding_state':status,'review_sha256':entry.get('sha256') if entry else None,
            'reviewed_uses':deepcopy(uses),'project_use_status':'not_measured_by_source_audit',
            'prose_effect_status':'unverified'})
    result={'policy':POLICY,'status':'IN_PROGRESS','source_owners':len(rows),
        'binding_states':dict(states),'reviewed_uses':use_count,'creative_method_sources':creative,
        'retrieval_control_sources':controls,'issues':issues,'model_calls':0,
        'source_qualification_changed':False,'project_or_prose_verified_by_this_audit':0,
        'authority':'source_use_review_coverage_not_full_semantic_or_execution_success'}
    if details:result['rows']=rows
    return result
