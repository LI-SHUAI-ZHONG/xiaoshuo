"""Explicit protocol fixtures only; never import this from production code."""


def _leaf(value,path=''):
    ignored={'id','key','kind','status','source_id','source_ids','rule_id','task_id','ref','sha256'}
    if isinstance(value,dict):
        for key,item in value.items():
            if not key.startswith('_') and key not in ignored:
                yield from _leaf(item,path+'/'+key.replace('~','~0').replace('/','~1'))
    elif isinstance(value,list):
        for index,item in enumerate(value):yield from _leaf(item,path+'/'+str(index))
    elif isinstance(value,str) and value.strip():yield path


def criteria_for(data,products):
    used={r['source_id'] for r in products.get('_uses',[])};result=[]
    paths=list(_leaf(products))
    for contract in data.get('source_contracts',[]):
        if contract['source_id'] not in used:continue
        clauses=[]
        for obligation in contract['obligations']:
            issues=[i for i in contract.get('source_issues',{}).get('compilation',[])
                    if obligation['id'] in i.get('obligation_ids',[])]
            review=next((r for r in data.get('source_use_reviews',[]) if r['source_id']==contract['source_id']),None)
            decision=next((d for d in review['clause_decisions'] if d['id']==obligation['id']),None) if review else None
            if decision and decision['status']=='reviewed':
                issues=[i for i in issues if i['kind'] not in {'unclassified_original_field',
                    'unclassified_original_section','uninterpreted_original_text'}]
            if decision and decision['status']=='needs_review':
                issues.append({'kind':'binding_interpretation_needs_review'})
            clauses.append({'id':obligation['id'],'applicability':'source_unresolved' if issues else 'applies',
                'reason':(issues[0]['kind']+'：原始字段尚不完整，本次隔离测试不补造该项原义' if issues else
                          '[FAKE] 当前任务使用本条原义设计所选调查方案，结果引用实际项目字段'),
                'input_refs':[] if issues else ['brief:/text'],'output_refs':[] if issues else paths[:1],
                'operation':'' if issues else '[FAKE] 依据这条原义安排现有人物的调查步骤和限制',
                'observable':'' if issues else '[FAKE] 本场人物先观察封条阻碍再采取对应调查行动',
                'check':'' if issues else '[FAKE] 独立审稿对照这条原义与实际动作结果逐项核验',
                'consumer':'review'})
        layer={'trigger':'[FAKE] 当前人物需要检查封条但不能破坏证据',
               'operation':'[FAKE] 将当前原义对应到所选人物的调查动作设计',
               'result':'[FAKE] 保留阻碍与后果并形成可以继续调查的实际结果',
               'verification':'[FAKE] 用当前版本稿件逐条核对原义和本次项目转译'}
        result.append({'source_id':contract['source_id'],'contract_sha256':contract['sha256'],
            'clauses':clauses,'layer_application':layer if contract.get('application_required') else {}})
    return result
