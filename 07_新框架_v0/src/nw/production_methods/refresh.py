"""Refresh the pending selection using the already saved inputs for this plan."""
from copy import deepcopy
import json

from nw.call_control import execution_lock
from nw.materials.network_followup import DELTA_FIELDS
from nw.materials.phase_routes import phase_order
from nw.novel_calls import call_id
from nw.novel_store import Journal, job_row
from nw.production_methods.inputs import registry
from nw.production_methods.selection import build_target, check_bindings, gate_target, method_step
from nw.production_methods.sources import MethodReader
from nw.story_models import StateHead
from nw.task_models import canonical, content_sha256
from nw.tasks import read_input_manifest


def _prior_products(store: object, job_id: str, manifest_id: str, scope: str, stage: str,
                    *, planning_hierarchy: bool = False) -> dict:
    stages = phase_order(scope, planning_hierarchy=planning_hierarchy)
    preceding = set(stages[:stages.index(stage)])
    rows = store.connection.execute('''SELECT t.id, t.manifest_id, t.result_json,
            json_extract(m.package_json, '$.study_input.stage') AS stage,
            json_extract(m.payload_json, '$.settings.prompt_version') AS call_version
        FROM task_calls t JOIN input_manifests m ON m.id=t.manifest_id
        WHERE t.budget_id=? AND t.kind='material_work'
          AND json_extract(m.package_json, '$.base_plan_manifest')=?
          AND (json_extract(m.package_json, '$.study_input.stage')=?
               OR (t.validation='VALID' AND json_type(t.result_json, '$.products')='object'))
        ORDER BY t.rowid''', (job_id, manifest_id, stage))
    records = {}
    for row in rows:
        completed = row['stage']
        if completed == stage:
            raise ValueError('当前步骤已有调用记录，请沿用已经确认的资料版本')
        if completed not in preceding:
            continue
        _, frozen = read_input_manifest(store, row['manifest_id'])
        if frozen['study_input']['scope'] != scope:
            raise ValueError('本轮前置产物记录无法唯一确认，请检查任务状态')
        products = json.loads(row['result_json'])['products']
        version = row['call_version'] or ''
        basis = frozen['study_input'].get('static_relations_basis')
        if (completed == 'static_relations' and basis and completed in records
                and version in ('static-network-followup-v1', 'static-network-cast-repair-v1')
                and basis.get('ref', {}).get('task_id') == records['static_relations']['task_id']
                and set(products) == DELTA_FIELDS):
            merged = deepcopy(records['static_relations']['products'])
            for key, items in products.items():
                if items or key in merged:
                    merged[key] = [*merged.get(key, []), *deepcopy(items)]
            records['static_relations'] = {'stage': completed, 'task_id': row['id'], 'products': merged,
                                           'sha256': content_sha256(merged)}
            continue
        is_repair = (version == 'source-step-cast-repair-v1'
                     and completed in ('character_design', 'static_relations', 'plot_design'))
        if completed in records and not is_repair:
            raise ValueError('本轮前置产物记录无法唯一确认，请检查任务状态')
        records[completed] = {'stage': completed, 'task_id': row['id'], 'products': products,
                              'sha256': content_sha256(products)}
    if records.keys() != preceding:
        raise ValueError('本轮前置产物尚未完整保存，请稍后重试')
    return records


def refresh_pending(store: object, job_id: str, token: str) -> tuple[dict, bool]:
    connection = store.connection
    with execution_lock(store, f'novel:{job_id}') as acquired, connection:
        if not acquired:
            raise ValueError('当前任务正在保存，请稍后刷新候选')
        connection.execute('BEGIN IMMEDIATE')
        job = job_row(store, job_id)
        outputs = json.loads(job['output_json'])
        gate = outputs.get('gate', {})
        if (job['status'] != 'WAITING' or gate.get('kind') != 'production_method_selection'
                or gate.get('token') != token):
            raise ValueError('选材节点已变化，请打开当前待确认步骤')

        scope, stage = gate['scope'], gate['stage']
        revised = bool(gate.get('cast_revision'))
        key = method_step(scope, stage, cast_revision=revised)
        journal = Journal(store, job_id)
        row = journal.latest(key)
        before = gate_target(gate)
        if (job['step_key'] != key or not row or row['status'] != 'STARTED'
                or canonical(row['input']) != canonical(gate)
                or journal.gate_payload(key, before, gate['actions']) != gate):
            raise ValueError('最新待确认记录已变化，请打开当前待确认步骤')

        task = call_id(job_id, f'plan:{scope}:propose', 1)
        manifest_id = f'plan:{task}'
        _, package = read_input_manifest(store, manifest_id)
        hierarchical = package.get('planning_hierarchy', False)
        if (package['scope'] != scope or stage not in phase_order(scope, planning_hierarchy=hierarchical)
                or package['branch_head']['branch_id'] != job['branch_id']):
            raise ValueError('待确认节点与已保存的制作范围不一致')
        journal.head = StateHead(**package['branch_head'])
        journal.check_active(key)
        if revised:
            _, products = read_input_manifest(store, f'project-methods:{task}:{stage}:cast-repair:inputs')
        else:
            products = _prior_products(store, job_id, manifest_id, scope, stage, planning_hierarchy=hierarchical)
        check_bindings(before, registry(package, products))
        updated = build_target(MethodReader(store.directory.parent), package, stage, products)
        if revised:
            updated['cast_revision'] = True
        if canonical(updated) == canonical({k: v for k, v in before.items() if k != 'candidate_revision'}):
            return gate, False

        attempt = row['attempt'] + 1
        latest = journal.gate_payload(key, {**updated, 'candidate_revision': attempt}, gate['actions'])
        connection.execute('''UPDATE novel_steps SET status='STALE', output_json=?
            WHERE job_id=? AND step_key=? AND attempt=?''',
            (canonical({'superseded_by': latest['token']}), job_id, key, row['attempt']))
        connection.execute('''INSERT INTO novel_steps (job_id,step_key,attempt,status,input_json,output_json)
            VALUES (?,?,?,'STARTED',?,'{}')''', (job_id, key, attempt, canonical(latest)))
        connection.execute('UPDATE novel_jobs SET output_json=? WHERE id=?',
                           (canonical({**outputs, 'gate': latest}), job_id))
        return latest, True
