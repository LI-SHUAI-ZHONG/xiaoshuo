"""Explicit route-review protocol fixtures; these certify no real source meaning."""
from copy import deepcopy
import json

from nw.materials.binding_reviews import POLICY
from nw.materials.phase_routes import route_method,ORDER
from nw.materials.source_semantics import compile_semantics
from nw.task_models import content_sha256


def review_fixture(source,stages):
    contract=compile_semantics(source)
    review={'policy':POLICY,'scope':'isolated_protocol_fixture','source':deepcopy(source['source']),
        'original_text_sha256':content_sha256(source['original_text']),
        'source_quotes':[source['original_text']],'workflow_refs':[],
        'uses':[{'stage':stage,'purpose':'[FAKE] 隔离测试只校验既定步骤的协议与数据传递',
            'prerequisites':'[FAKE] 使用本测试给定的实际前置，不作为真实来源语义验收',
            'products':'[FAKE] 本步骤夹具已给定的实际字段及其输出引用',
            'downstream_check':'[FAKE] 校验本测试的版本、步骤及源条款覆盖，不宣称文学效果'} for stage in stages],
        'clause_reviews':[{'text_start':c['source_ref']['text_start'],'text_end':c['source_ref']['text_end'],
            'sha256':c['source_ref']['clause_sha256'],'status':'reviewed','semantic_role':c['kind'],
            'reason':'[FAKE] 仅用于该临时Store的审核协议夹具，不是生产用途确认'} for c in contract['obligations']]}
    review['sha256']=content_sha256(review)
    return review


def install_review_fixtures(workspace):
    from nw.materials.work_catalog import SourceDesk
    desk=SourceDesk(workspace);reviews=[]
    for row in desk.rows:
        source=desk.read(row['id'])
        if source['use_mode']!='project_method':continue
        stages=[s for s in route_method(source)['stages'] if s in ORDER]
        if stages:
            reviews.append(review_fixture(source,stages))
    path=workspace/'materials/workflow_binding_reviews.json'
    path.write_text(json.dumps({'policy':POLICY,'protocol_only_test_data':True,'reviews':reviews},ensure_ascii=False),encoding='utf-8')
