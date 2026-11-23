"""Client configuration and persisted, per-version method usage receipts."""
import json

from nw.production_methods.policy import DEFAULT_TASKS,normalize
from nw.production_methods.sources import MethodReader, matching_methods
from nw.store import now
from nw.task_models import canonical


class ProductionMethodMixin:
    def validate_method_choice(self, target: dict, choice: dict) -> None:
        from nw.production_methods.selection import validate_choice
        validate_choice(MethodReader(self.studio.workspace), target, choice)

    def refresh_methods(self, ident: str, token: str, body: dict) -> dict:
        from nw.production_methods.refresh import refresh_pending
        if body:
            raise ValueError('刷新方法候选不需要提交确认内容')
        with self._lock:
            novel = self.db.get(ident)
            gate = next((row for row in self.gates(ident)['gates'] if row['id'] == token), None)
            if gate is None or gate['target'].get('kind') != 'production_method_selection':
                raise ValueError('选材节点已变化，请打开当前待确认步骤')
            with self.open_store(novel) as store:
                latest, changed = refresh_pending(store, gate['job_id'], token)
        return {'gate': {**gate, 'id': latest['token'], 'token': latest['token'], 'target': latest},
                'changed': changed}

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
                selection = payload.get('production_method_selection', {})
                ai_selected = selection.get('mode') in ('ai', 'recommendations')
                if ai_selected and row['validation'] != 'VALID':
                    continue
                for item in selected:
                    method=item['method'];app=next((a for a in products.get('_method_applications',[]) if a['method_id']==method['id']),None)
                    evidence = {}
                    if ai_selected:
                        if app is None:
                            continue
                        evidence['selection_origin'] = 'ai'
                        if selection['mode'] == 'ai':
                            from nw.production_methods.contracts import at
                            evidence['design_needs'] = [
                                {**b, 'value': at(selection['demand'][b['kind']], b['path']), 'ref': selection['upstream_refs'][b['kind']]}
                                for b in app['design_basis']]
                    uses.append({'task_id':row['id'],'stage':payload['stage'],'scope':payload['scope'],
                        **evidence,
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
        types=novel['wizard'].get('genre_ids',[])
        try:
            available=[{'id':r['id'],'version':r['version'],'title':r['body']['title'],'tasks':r['body']['tasks'],
                        'scopes':r['body']['scopes'],'type_tags':r['body']['type_tags']}
                       for r,_ in matching_methods(MethodReader(self.studio.workspace),types)] if types else []
        except ValueError:available=[]
        return {'policy':novel['wizard'].get('production_methods',{}),'current_job_policy':current,
            'project_type_ids':novel['wizard'].get('genre_ids',[]),
            'method_references':novel['wizard'].get('method_references',[]),
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
            configuration = body['policy']
            types = novel['wizard'].get('genre_ids', [])
            if isinstance(configuration, dict):
                if 'recommended_slots' in configuration:
                    raise ValueError('推荐候选版本由类型资料库自动核定')
                preferences = {row['id']: row['version'] for row in novel['wizard'].get('method_references', [])}
                configuration = {**configuration, 'preferred_methods': preferences}
            if (isinstance(configuration, dict) and novel['wizard'].get('auto_recommendations')
                    and configuration.get('recommendation_mode') == 'auto'):
                from nw.studio.method_recommendations import freeze_automatic_policy

                policy = freeze_automatic_policy(MethodReader(self.studio.workspace), types, configuration)
            else:
                policy = normalize(configuration, types=types)
            wizard={**novel['wizard'],'production_methods':policy}
            if policy and not wizard.get('genre_ids'):wizard['genre_ids']=policy['type_ids']
            with self.db.connect() as conn:
                conn.execute('UPDATE novels SET wizard_json=?,updated_at=? WHERE id=?',(canonical(wizard),now(),ident))
            self.db.event(ident,'method_configuration','后续制作方法配置已保存；当前任务保留原冻结配置。',
                          {'policy':policy,'reason':body['reason'].strip()})
        return self.method_usage(ident)
