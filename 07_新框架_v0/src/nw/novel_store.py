
"""SQLite checkpoints for the novel coordinator."""
from dataclasses import asdict, dataclass, field
import json
import sqlite3
from typing import Any, Callable
from uuid import uuid4

from nw.call_budget import _insert_budget, read_budget
from nw.cards import eligible_rule_refs
from nw.materials.binding import resolve_materials
from nw.store import Store, now
from nw.story_delta import _scene_position, story_write_manifest
from nw.story_dependencies import legacy_ref
from nw.story_models import AcceptanceRequest, CardRef, StateHead
from nw.story_state import current_head, revision_state, text
from nw.task_models import Budget, canonical, content_sha256


@dataclass(frozen=True)
class JobRequest:
    mode: str
    branch_id: str = 'main'
    scene_ids: list[str] = field(default_factory=list)
    brief_ref: dict | int | None = None
    budget: Budget | None = None
    design_scope: str = 'chapter'
    parent_id: str | None = None
    scene_scopes: dict[str, dict] = field(default_factory=dict)
    materials: list[dict] = field(default_factory=list)
    material_deferrals: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class JobRef:
    id: str


@dataclass(frozen=True)
class JobResult:
    id: str
    status: str
    step: str | None = None
    outputs: dict = field(default_factory=dict)
    reason: str | None = None


class JobPaused(ValueError):
    def __init__(self, status: str, step: str, reason: str, **outputs: Any) -> None:
        super().__init__(reason)
        self.status, self.step, self.outputs = status, step, outputs


def job_row(store: Store, ident: str) -> sqlite3.Row:
    row = store.connection.execute('SELECT * FROM novel_jobs WHERE id=?', (ident,)).fetchone()
    if row is None:
        raise ValueError('Novel job not found')
    return row


def _next_scene(store: Store, snapshot: dict) -> list[str]:
    active = {(row['card_id'], row['version']) for row in snapshot['settings']}
    cutoff = max((_scene_position(store, ident) for ident in snapshot['slots']), default=(0, 0))
    candidates = []
    for scene in store.list('scene'):
        binding = json.loads(scene.card_json).get('story')
        if not isinstance(binding, dict) or scene.id in snapshot.get('stale_plan_scenes', []):
            continue
        ref = binding.get('scene_ref')
        if not isinstance(ref, dict):
            continue
        position = _scene_position(store, scene.id)
        if (ref.get('card_id'), ref.get('version')) in active and position > cutoff:
            candidates.append((position, scene.id))
    if not candidates:
        raise ValueError('No next approved scene; apply a plan or provide an explicit scene')
    return [min(candidates)[1]]


def start_job(store: Store, request: JobRequest) -> JobRef:
    if (request.mode not in ('design', 'write', 'revise', 'continue') or not text(request.branch_id)
            or not isinstance(request.scene_ids, list) or not all(map(text, request.scene_ids))
            or len(set(request.scene_ids)) != len(request.scene_ids) or not isinstance(request.budget, Budget)):
        raise ValueError('Invalid novel mode, branch, scenes or budget')
    if request.mode == 'design':
        if request.scene_ids or request.scene_scopes or request.design_scope not in ('volume', 'chapter', 'scene', 'replan'):
            raise ValueError('Design requires no scene IDs and a valid detail scope')
        if request.design_scope == 'replan' and not request.parent_id:
            raise ValueError('Replanning requires a parent proposal')
    elif request.parent_id is not None or request.design_scope != 'chapter':
        raise ValueError('Design options are available only in design mode')
    if request.parent_id is not None and not text(request.parent_id):
        raise ValueError('Invalid parent proposal ID')
    if request.mode != 'design' and request.materials != []:
        raise ValueError('MATERIAL_SCOPE: assign materials in design; writing inherits the approved scene')
    if (not isinstance(request.material_deferrals, dict) or
            not all(text(key) and text(reason) for key, reason in request.material_deferrals.items()) or
            request.material_deferrals and request.mode != 'design'):
        raise ValueError('MATERIAL_SCOPE: design deferrals require source IDs and author reasons')
    materials = resolve_materials(store.directory.parent, request.materials)
    ident = uuid4().hex
    with store.connection:
        store.connection.execute('BEGIN IMMEDIATE')
        if not store.managed_story():
            raise ValueError('MANAGED_STORY_REQUIRED: use story adopt before starting a novel job')
        head = current_head(store, request.branch_id)
        snapshot = revision_state(store, head)
        scenes = request.scene_ids
        if request.mode == 'continue' and not scenes:
            scenes = _next_scene(store, snapshot)
        if request.mode != 'design' and not scenes:
            raise ValueError('Choose one or more scenes')
        scenes = sorted(scenes, key=lambda scene: _scene_position(store, scene))
        if (not isinstance(request.scene_scopes, dict) or request.scene_scopes.keys() - set(scenes)
                or any(not isinstance(scope, dict) or set(scope) != {'story_order', 'scene_ref'}
                       or type(scope['story_order']) is not int or not isinstance(scope['scene_ref'], dict)
                       or set(scope['scene_ref']) != {'card_id', 'version'}
                       or not text(scope['scene_ref']['card_id']) or type(scope['scene_ref']['version']) is not int
                       or scope['scene_ref']['version'] < 1 for scope in request.scene_scopes.values())):
            raise ValueError('Scene scopes must pin story_order and scene_ref for a scene in this job')
        originals = {}
        if request.mode == 'revise':
            for scene in scenes:
                slot = snapshot['slots'].get(scene)
                draft = store.get('draft', slot['draft_id']) if slot else None
                if draft is None:
                    for candidate in reversed(store.drafts(scene)):
                        frozen = story_write_manifest(store, candidate)
                        if (candidate.status != 'complete' or frozen is None
                                or frozen['branch_id'] != head.branch_id
                                or frozen['settings']['prompt_version'] == 'story-ab-v1'):
                            continue
                        owner = frozen.get('novel_job_id')
                        if owner and job_row(store, owner)['status'] != 'BLOCKED':
                            continue
                        selected_deltas = {slot['delta_id'] for slot in snapshot['slots'].values()}
                        if any(ident not in selected_deltas for ident, _ in frozen['candidate_delta_refs']):
                            continue
                        draft = candidate
                        break
                if draft is None:
                    raise ValueError('Revision mode requires a complete source draft for each scene')
                originals[scene] = draft.id
        briefs = store.briefs()
        pin = asdict(legacy_ref('brief', store.project().id, briefs[-1])) if briefs else None
        if (request.brief_ref is not None and (pin is None or isinstance(request.brief_ref, bool)
                or request.brief_ref not in (pin, pin['version'])) or request.mode == 'design' and pin is None):
            raise ValueError('Novel job requires the current Brief version')
        if request.mode == 'revise' and request.budget.max_revisions == 0:
            raise ValueError('Revision mode requires at least one revision in the budget')
        frozen = {**asdict(request), 'scene_ids': scenes, 'brief_ref': pin,
                  'head': asdict(head), 'original_drafts': originals, 'materials': materials}
        _insert_budget(store, ident, request.budget)
        store.connection.execute("""INSERT INTO novel_jobs
            (id,branch_id,request_json,budget_id,status,output_json) VALUES (?,?,?,?,'READY','{}')""",
                                 (ident, head.branch_id, canonical(frozen), ident))
    return JobRef(ident)


def show_job(store: Store, ident: str) -> JobResult:
    job = job_row(store, ident)
    steps = store.connection.execute(
        'SELECT step_key,attempt,status,output_json FROM novel_steps WHERE job_id=? ORDER BY rowid', (ident,))
    outputs = json.loads(job['output_json'])
    request = json.loads(job['request_json'])
    outputs['scope'] = {key: request[key] for key in ('mode', 'head', 'scene_ids', 'brief_ref')}
    if request.get('materials'):
        outputs['scope']['materials'] = [row['request'] for row in request['materials']]
    outputs['steps'] = [{'step_key': row[0], 'attempt': row[1], 'status': row[2], 'output': json.loads(row[3])}
                        for row in steps]
    outputs['budget'] = asdict(read_budget(store, job['budget_id']))
    return JobResult(ident, job['status'], job['step_key'], outputs, job['reason'])


def cancel_job(store: Store, ident: str) -> JobResult:
    with store.connection:
        store.connection.execute('BEGIN IMMEDIATE')
        job_row(store, ident)
        store.connection.execute("""UPDATE novel_jobs SET status='CANCELLED',reason='CANCELLED'
            WHERE id=? AND status NOT IN ('DONE','REJECTED','STALE','CANCELLED')""", (ident,))
    return show_job(store, ident)


class Journal:
    def __init__(self, store: Store, ident: str) -> None:
        self.store, self.id = store, ident
        self.request = json.loads(job_row(store, ident)['request_json'])
        self.head = StateHead(**self.request['head'])
        self.current_step: str | None = None

    def check_active(self, key: str, *, check_head: bool = True) -> None:
        self.current_step = key
        if job_row(self.store, self.id)['status'] == 'CANCELLED':
            raise JobPaused('CANCELLED', key, 'CANCELLED')
        if check_head:
            actual = current_head(self.store, self.head.branch_id)
            if actual != self.head:
                raise JobPaused('STALE', key, 'STALE_HEAD', expected=asdict(self.head), actual=asdict(actual))
        briefs = self.store.briefs()
        version = self.request['brief_ref']['version'] if self.request['brief_ref'] else None
        if (briefs[-1].version if briefs else None) != version:
            raise JobPaused('STALE', key, 'STALE_BRIEF', expected_version=version)

    def latest(self, key: str) -> dict | None:
        self.current_step = key
        row = self.store.connection.execute("""SELECT * FROM novel_steps
            WHERE job_id=? AND step_key=? ORDER BY attempt DESC LIMIT 1""", (self.id, key)).fetchone()
        return (dict(row) | {'input': json.loads(row['input_json']), 'output': json.loads(row['output_json'])}
                if row else None)

    def reserve(self, key: str, input_data: dict, *, attempt: int = 1, check_head: bool = True) -> dict:
        with self.store.connection:
            self.store.connection.execute('BEGIN IMMEDIATE')
            self.check_active(key, check_head=check_head)
            self.store.connection.execute("""INSERT INTO novel_steps
                (job_id,step_key,attempt,status,input_json,output_json) VALUES (?,?,?,'STARTED',?,'{}')""",
                                          (self.id, key, attempt, canonical(input_data)))
        return self.latest(key)

    def result(self, key: str, status: str, output: dict) -> None:
        row = self.latest(key)
        with self.store.connection:
            self.store.connection.execute("""UPDATE novel_steps SET status=?,output_json=?
                WHERE job_id=? AND step_key=? AND attempt=?""",
                                          (status, canonical(output), self.id, key, row['attempt']))

    def move(self, status: str, key: str | None, reason: str | None = None, **outputs: Any) -> JobResult:
        with self.store.connection:
            self.store.connection.execute("""UPDATE novel_jobs SET status=?,step_key=?,reason=?,output_json=?
                WHERE id=? AND status<>'CANCELLED'""", (status, key, reason, canonical(outputs), self.id))
        return show_job(self.store, self.id)

    def gate(self, key: str, target: dict, decide: Callable, actions: dict[str, str],
             validate: Callable[[dict], None] | None = None) -> dict:
        row = self.latest(key)
        token = content_sha256({'job': self.id, 'step': key, 'target': target})
        gate = {'token': token, **target, 'actions': list(actions)}
        if row is None:
            row = self.reserve(key, gate)
        if canonical(row['input']) != canonical(gate):
            raise JobPaused('STALE', key, 'STALE_DECISION_TARGET')
        if row['status'] == 'DONE':
            return row['output']['choice']
        choice = decide(key, gate)
        if choice is None:
            raise JobPaused('WAITING', key, 'AUTHOR_DECISION_REQUIRED', gate=gate)
        if (not isinstance(choice, dict) or not text(choice.get('action')) or choice['action'] not in actions
                or not text(choice.get('reason'))):
            raise ValueError('Decision requires a supported action and a reason')
        if validate:
            validate(choice)
        with self.store.connection:
            self.store.connection.execute('BEGIN IMMEDIATE')
            self.check_active(key)
            ident = f'{self.id}:{key}'
            payload = {'job_id': self.id, 'step': key, 'token': token, 'target': target, 'choice': choice}
            self.store.connection.execute('INSERT INTO story_decisions VALUES (?,?,?,?,?)',
                                          (ident, actions[choice['action']], canonical(payload), choice['reason'], now()))
            self.store.connection.execute("""UPDATE novel_steps SET status='DONE',output_json=?
                WHERE job_id=? AND step_key=? AND attempt=?""",
                                          (canonical({'choice': choice, 'decision_id': ident}),
                                           self.id, key, row['attempt']))
        return choice


def checkpoint_input(requests: list[AcceptanceRequest], head: StateHead, commit_id: str) -> dict:
    return {'requests': sorted((asdict(req) for req in requests), key=canonical),
            'head': asdict(head), 'commit_id': commit_id}


def acceptance_checkpoint(store: Store, checkpoint: tuple[str, str, int], expected: dict,
                          result: StateHead | None, *, existing: bool = False) -> None:
    job_id, key, attempt = checkpoint
    row = store.connection.execute("""SELECT n.status,n.input_json,n.output_json,j.status,j.branch_id
        FROM novel_steps n JOIN novel_jobs j ON n.job_id=j.id
        WHERE n.job_id=? AND n.step_key=? AND n.attempt=?""", checkpoint).fetchone()
    required = 'DONE' if existing else 'STARTED'
    if (key != 'batch:accept' or type(attempt) is not int or row is None or row[0] != required or row[1] != canonical(expected)
            or row[3] != ('DONE' if existing else 'RUNNING') or row[4] != expected['head']['branch_id']
            or expected['commit_id'] != f'novel:{job_id}'):
        raise ValueError('Workflow checkpoint does not match the exact batch, job and attempt')
    if existing:
        if json.loads(row[2]).get('head') != asdict(result):
            raise ValueError('Workflow checkpoint does not match the committed head')
    elif result is None:
        eligible = set(eligible_rule_refs(store))
        for item in expected['requests']:
            draft = store.get('draft', item['draft_id'])
            manifest = story_write_manifest(store, draft)
            if manifest is None:
                raise ValueError('Workflow acceptance requires a frozen story draft')
            selected = {CardRef(**ref) for ref in (manifest.get('selection') or {}).get('selected_refs', [])}
            if not selected <= eligible:
                raise ValueError(f"STALE_METHOD_VERSION: {item['scene_id']}")
    else:
        output = canonical({'head': asdict(result), 'accepted': expected['requests']})
        store.connection.execute("""UPDATE novel_steps SET status='DONE',output_json=?
            WHERE job_id=? AND step_key=? AND attempt=?""", (output, job_id, key, attempt))
        store.connection.execute("""UPDATE novel_jobs SET status='DONE',step_key=?,reason=NULL,output_json=?
            WHERE id=?""", (key, output, job_id))
