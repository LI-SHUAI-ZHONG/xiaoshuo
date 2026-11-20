"""Client configuration and persisted, per-version method usage receipts."""
import json

from nw.production_methods.policy import DEFAULT_TASKS,normalize
from nw.production_methods.sources import MethodReader
from nw.store import now
from nw.task_models import canonical


class ProductionMethodMixin:
    @staticmethod
    def validate_method_choice(target: dict,choice: dict) -> None:
        if choice.get('action')!='approve':return
        selected=choice.get('method_ids');ready={c['method']['id']:c for c in target['candidates'] if not c['missing']}
        if not isinstance(selected,list) or any(not isinstance(key,str) or key not in ready for key in selected) or len(set(selected))!=len(selected) or len(selected)>target['max_methods']:
            raise ValueError('请选择当前有效且前置就绪的方法')
        if not set(target['required_tasks'])<={t for key in selected for t in ready[key]['method']['body']['tasks']}:
            raise ValueError('所选方法须覆盖当前必需制作职责')

    def method_usage(self,ident: str) -> dict:
        novel=self.db.get(ident);uses=[];reviews=[];current={}
        with self.open_store(novel) as store:
            if novel['job_id']:
                row=store.connection.execute('SELECT request_json FROM novel_jobs WHERE id=?',(novel['job_id'],)).fetchone()
                current=json.loads(row[0]).get('production_method_policy',{}) if row else {}
            rows=store.connection.execute('''SELECT t.id,t.validation,t.result_json,m.package_json
                FROM task_calls t JOIN input_manifests m ON m.id=t.manifest_id
                WHERE json_type(m.package_json,'$.study_input.production_methods')='array'
                ORDER BY t.rowid''').fetchall()
            for row in rows:
                payload=json.loads(row['package_json'])['study_input'];value=json.loads(row['result_json']) or {}
                selected=payload['production_methods'];products=value.get('products',{})
                for item in selected:
                    method=item['method'];app=next((a for a in products.get('_method_applications',[]) if a['method_id']==method['id']),None)
                    uses.append({'task_id':row['id'],'stage':payload['stage'],'scope':payload['scope'],
                        'method_id':method['id'],'method_version':method['version'],'title':method['body']['title'],
                        'structure_origin':method['structure_origin'],'validation':row['validation'],
                        'application':app,'inputs':{k:{'kind':v['kind'],'ref':v['ref']} for k,v in item['inputs'].items()}})
                for receipt in products.get('_method_receipts',[]):
                    uses.append({'task_id':row['id'],'stage':payload['stage'],'scope':payload['scope'],
                                 'kind':'downstream_receipt','receipt':receipt,'validation':row['validation']})
            for row in store.connection.execute("SELECT id,output_text FROM runs WHERE kind='review' ORDER BY rowid"):
                try:value=json.loads(row['output_text'])
                except (ValueError,TypeError):continue
                for check in value.get('material_checks',[]):
                    if str(check.get('id','')).startswith('method:'):reviews.append({'review_run_id':row['id'],**check})
        try:
            available=[{'id':r['id'],'version':r['version'],'title':r['body']['title'],'tasks':r['body']['tasks'],
                        'scopes':r['body']['scopes'],'type_tags':r['body']['type_tags']}
                       for r in MethodReader(self.studio.workspace).approved() if r['available'] and r['structure_origin']]
        except ValueError:available=[]
        return {'policy':novel['wizard'].get('production_methods',{}),'current_job_policy':current,
            'project_type_ids':novel['wizard'].get('genre_ids',[]),
            'default_tasks':DEFAULT_TASKS,'available_methods':available,'uses':uses,'review_checks':reviews,
            'note':'送达、有效执行、作者批准设计和正文证据分别保存；出现记录不代表文学效果通过。'}

    def configure_methods(self,ident: str,body: dict) -> dict:
        if set(body)!={'policy','reason'} or not isinstance(body.get('reason'),str) or not body['reason'].strip():
            raise ValueError('请填写本次方法调度配置与修改原因')
        with self._lock:
            worker=self._workers.get(ident)
            if worker and worker.is_alive():raise ValueError('请先暂停当前制作，等待调用保存后修改后续配置')
            novel=self.db.get(ident)
            if novel['status']=='done':raise ValueError('已完稿项目不能修改制作配置')
            policy=normalize(body.get('policy'),types=novel['wizard'].get('genre_ids',[]))
            wizard={**novel['wizard'],'production_methods':policy}
            if policy and not wizard.get('genre_ids'):wizard['genre_ids']=policy['type_ids']
            with self.db.connect() as conn:
                conn.execute('UPDATE novels SET wizard_json=?,updated_at=? WHERE id=?',(canonical(wizard),now(),ident))
            self.db.event(ident,'method_configuration','后续制作方法配置已保存；当前任务保留原冻结配置。',
                          {'policy':policy,'reason':body['reason'].strip()})
        return self.method_usage(ident)
