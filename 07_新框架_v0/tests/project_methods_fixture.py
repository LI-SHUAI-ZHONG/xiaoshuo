"""[FAKE] Isolated corpus-to-project design/write/review fixtures."""
from copy import deepcopy
import json

from nw.llm.base import GenResult
from nw.studio.library import LibraryService
from nw.production_methods.contracts import at
from corpus_fixture import start_analysis,wait_job
from test_material_phase_flow import PhaseModel,template_catalog
from test_novel_flow import config
from test_material_stage_roundtrip import StageModel


def seed_method(workspace,monkeypatch,*,tasks=None,scopes=None,input_kind='brief',types=None):
    library=LibraryService(workspace)
    book,job,_=start_analysis(library,monkeypatch);assert job['status']=='completed',job['error']
    library.review_corpus(book['id'],{'version':1,'decision':'approve','note':'[FAKE] 核对多层结构来源'})
    task=library.start_corpus_job(book['id'],{'kind':'methods','options':{'thread_ids':['T_hook']}})
    assert wait_job(library,book['id'],task['id'])['status']=='completed'
    method=library.list_methods()['methods'][0];body=deepcopy(method['body'])
    body.update(title='[FAKE] 先回应旧问题再提出新问题的具体设计方法',tasks=tasks or ['hook'],scopes=scopes or ['book','chapter'])
    body['prerequisites']=[{'key':'i1','input_kind':input_kind,'artifact':'[FAKE] 本项目已批准前置','requirement':'[FAKE] 已明确调查目标、问题与约束，不能自行补猜'}]
    body['operations']=[{'key':'op1','instruction':'[FAKE] 对照调查目标设计回应与升级的因果关系','input_keys':['i1'],'output_keys':['o1']}]
    body['outputs']=[{'key':'o1','stage':'plot_design','field':'directions','artifact_kind':'stage_product','description':'[FAKE] 本项目每种可选剧情方向的具体问题和回应设计'}]
    body['downstream']=[{'output_key':'o1','consumer':consumer,'usage':'[FAKE] 承接具体问题、选择与回应，再设计可见的场景呈现'} for consumer in ['scene_design','writer','review']]
    body['acceptance']=[{'output_key':'o1','check':'[FAKE] 核对旧问题的回应与新问题是否有具体事件依据','evidence_required':'[FAKE] 本项目剧情方向、场景卡及实际正文引文'}]
    if types is not None:body['type_tags']=types
    saved=library.save_method({'body':body,'expected_version':1},method['id'])
    approved=library.review_method(saved['id'],{'version':2,'decision':'approve','note':'[FAKE] 方法与来源独立核对'})
    assert approved['available'],approved['issues']+approved['source_issues']
    return library,approved


class ProjectModel(PhaseModel):
    def __init__(self):
        super().__init__();self.omit_application=False;self.wrong_value=False;self.omit_receipt=False
        self.on_payload=None
        self.writer=StageModel('[FAKE] project-methods')

    def generate(self,messages,**params):
        payload=json.loads(messages[-1]['content'])
        if self.on_payload:self.on_payload(payload)
        if not any(marker in messages[0]['content'] for marker in ('[MATERIAL_STEP]','[MATERIAL_ASSEMBLY]')):
            self.calls.append(messages)
            generated=self.writer.generate(messages,**params)
            if '{"operations"' in messages[0]['content']:
                raw=json.loads(generated.text)
                for op in raw['operations']:op.setdefault('expected_old',None)
                generated.text=json.dumps(raw,ensure_ascii=False)
            return generated
        result=super().generate(messages,**params)
        if 'production_methods' not in payload:return result
        value=json.loads(result.text);products=value['products'];stage=payload['stage']
        apps=[];receipts=[]
        for item in payload['production_methods']:
            output=[]
            for spec in item['outputs']:
                field=spec['field'];places=[]
                if field=='directions':
                    for index,direction in enumerate(products[field]):
                        direction['choice']+='；[FAKE] 先以本案旧印证明回应换印问题，再追查登记者承担的代价'
                        places.append({'path':[field,index,'choice'],'value':direction['choice']})
                else:places=[{'path':[field],'value':products[field]}]
                output.append({'key':spec['key'],'placements':places,'scene_guidance':[]})
            apps.append({'method_id':item['method']['id'],'operations':[{'key':op['key'],
                'explanation':'[FAKE] 按本案已批准调查目标，用旧印的可见差异回应换印问题，并把新问题交给登记者调查'} for op in item['operations']],
                'outputs':output})
        for delivery in payload['method_handoffs']:
            available=products.get('members',[])
            scene_rows=[(i,m) for i,m in enumerate(available) if m['kind']=='scene'];guidance=[]
            if scene_rows:
                places=[]
                for i,member in scene_rows:
                    member['body']['goal']+='；[FAKE] 按父纲旧印证据先回应换印问题，再追查登记者'
                    places.append({'path':['members',i,'body','goal'],'value':member['body']['goal']})
                    guidance.append({'scene':member['key'],'observable':'[FAKE] 本场先借灯检查旧印，以可见的印痕回应换印疑问，再核对登记者',
                                     'check':'[FAKE] 用本场实际原文核对印痕、回应和进一步调查之间的因果关系'})
            else:
                field=next(key for key in products if not key.startswith('_') and products[key])
                places=[{'path':[field],'value':products[field]}]
            receipts.append({'id':delivery['id'],'operation':'[FAKE] 依据已批准父纲的换印调查目标，把问题回应与新疑问落实为本场目标和行动',
                             'placements':places,'scene_guidance':guidance})
        # Multiple deliveries can refine the same field: all receipts pin its final value.
        for receipt in receipts:
            for place in receipt['placements']:place['value']=deepcopy(at(products,place['path']))
        if self.wrong_value and apps:apps[0]['outputs'][0]['placements'][0]['value']='[FAKE] 实际产物中不存在的值'
        products['_method_applications']=[] if self.omit_application else apps
        products['_method_receipts']=[] if self.omit_receipt else receipts
        result.text=json.dumps(value,ensure_ascii=False)
        return result


def approve_method_gate(step,target):
    if target.get('kind')=='production_method_selection':
        return {'action':'approve','reason':'[FAKE] 已核对适用条件、原文实例及本项目前置版本',
                'method_ids':[item['method']['id'] for item in target['candidates'] if not item['missing']]}
    return None
