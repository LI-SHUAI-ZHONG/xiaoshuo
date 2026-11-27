"""Generate and freeze short, comparable directions before designing the book."""
from dataclasses import asdict
from difflib import SequenceMatcher
from itertools import combinations
from unicodedata import normalize

from nw.call_budget import prepare_call
from nw.call_control import model_settings
from nw.novel_calls import JobCalls, call_id
from nw.novel_store import Journal, job_row
from nw.story_dependencies import legacy_ref
from nw.task_models import InputManifest, Ref, TaskRequest, canonical, content_sha256
from nw.tasks import freeze_manifest

KIND = 'book_directions'
CONFIRM_STEP = 'direction:book:confirm'
FIELDS = {
    'title': ('短标题', 50),
    'premise': ('故事前提', 180),
    'world_premise': ('世界前提', 180),
    'protagonist': ('主角的现有处境', 160),
    'goal': ('可追求的主角目标', 160),
    'conflict': ('核心矛盾与对抗力量', 180),
    'long_term_drive': ('长篇推进方式与累积后果', 300),
    'type_fit': ('同一类型组合怎样体现在故事里', 150),
    'author_fit': ('与构想和硬约束的具体对应', 150),
}
DRIVING_FIELDS = ('goal', 'conflict', 'long_term_drive')
PLACEHOLDERS = frozenset({'待定', '未知', '略', '空', '同上', '见前案', '照前案', '沿用上案', '占位', '无', 'tbd', 'placeholder'})

PROMPT = (
    '[BOOK_DIRECTIONS] 你在小说立项后提出供作者比较的全书故事短案。返回两个或三个相互独立的原创候选，'
    '每个自成一体，约 200 到 350 字。每个候选都从同一份立项构想、类型主次和硬约束出发。'
    '普通偏好按候选的实际需要使用。每案让主角的起始处境产生明确目标，说明哪些人或力量阻止他，'
    '首轮行动会引发什么变化，以及这些后果怎样积累成后续长篇推进。让候选在目标、对抗方式或推进路径上有实质差异。'
    '所有世界前提和人物处境都是各自独立的提案。选定一个方向后，制作步骤再核证规则、设计具体卡片和细化剧情。'
    '若 production_methods.method_summaries 给出了作者已选或系统冻结的拆解方法抽象摘要，请让候选方向与这些方法的目标步骤和适用条件相容，但严禁照搬任何参考作品的人名、设定或情节。'
    '已发生的故事事实与作者约束以 Brief 为准。若有 previous_rejection，回应作者退回理由并提出新的方向。'
    '严格返回一个 JSON 对象，唯一字段为 candidates。每个候选的字段和字数上限由 contract 给出，'
    '全部填写短文本。禁止输出正文、世界规则卡、卷章纲或制作步骤的完成结论。'
)


def _comparison_key(value: str) -> str:
    return ''.join(ch for ch in normalize('NFKC', value).casefold() if ch.isalnum())


def validate_direction_options(raw: dict) -> None:
    if (not isinstance(raw, dict) or set(raw) != {'candidates'}
            or not isinstance(raw['candidates'], list) or not 2 <= len(raw['candidates']) <= 3):
        raise ValueError('BOOK_DIRECTION: 请提交两到三个独立方向短案')

    titles = set()
    drives = []
    for index, row in enumerate(raw['candidates'], start=1):
        if not isinstance(row, dict) or row.keys() != FIELDS.keys():
            raise ValueError(f'BOOK_DIRECTION: 第 {index} 个短案须完整使用方向字段')
        for field, (label, limit) in FIELDS.items():
            value = row[field]
            key = _comparison_key(value) if isinstance(value, str) else ''
            if not key or key in PLACEHOLDERS or len(value) > limit:
                raise ValueError(f'BOOK_DIRECTION: 第 {index} 个短案的「{label}」须为 {limit} 字内的具体文本')
        title = _comparison_key(row['title'])
        if title in titles:
            raise ValueError('BOOK_DIRECTION: 请为每个短案提供清晰可区分的标题')
        titles.add(title)
        drives.append('\n'.join(_comparison_key(row[field]) for field in DRIVING_FIELDS))

    for first, second in combinations(drives, 2):
        if SequenceMatcher(None, first, second, autojunk=False).ratio() >= 0.92:
            raise ValueError('BOOK_DIRECTION: 请让候选在主角目标、核心矛盾或长篇推进上有实质差异')


def direction_options(raw: dict) -> list[dict]:
    validate_direction_options(raw)
    return [{'id': 'direction-' + content_sha256(row)[:20], **row} for row in raw['candidates']]


def _creation_input(journal: Journal) -> dict:
    governance = journal.request.get('governance_inputs') or {}
    if isinstance(governance.get('book'), dict):
        governance = governance['book']
    types = governance.get('type_selection', {}).get('creation_plan', {}).get('types', [])
    prefs = {}
    for stage in governance.values():
        for row in stage.get('creation_plan', {}).get('preferences', []):
            prefs.setdefault(row['key'], row)
    result: dict = {'types': types, 'preferences': list(prefs.values())}
    plot_gov = governance.get('plot_design') or {}
    if plot_gov.get('length_policy'):
        result['length_policy'] = plot_gov['length_policy']
    if plot_gov.get('length_recommendation'):
        result['length_recommendation'] = plot_gov['length_recommendation']
    world_gov = governance.get('world_design') or {}
    if world_gov.get('cast_sample_reference'):
        result['cast_sample_reference'] = world_gov['cast_sample_reference']
    if world_gov.get('passage_references'):
        kinds: dict[str, str] = {}
        for ref in world_gov['passage_references']:
            if isinstance(ref, dict) and ref.get('kind'):
                kinds.setdefault(ref['kind'], str(ref.get('condition', ''))[:160])
        if kinds:
            result['passage_technique_kinds'] = [{'kind': k, 'condition': v} for k, v in kinds.items()]
    if method_policy := journal.request.get('production_method_policy'):
        summary = {k: method_policy[k] for k in ('tasks', 'preferred_methods', 'recommended_slots')
                   if method_policy.get(k)}
        method_summaries = _resolve_method_summaries(journal, method_policy)
        if method_summaries:
            summary['method_summaries'] = method_summaries
        if summary:
            result['production_methods'] = summary
    if journal.request.get('planning_hierarchy'):
        result['planning_hierarchy'] = True
    return result


def _resolve_method_summaries(journal: Journal, policy: dict) -> list[dict]:
    """Resolve pinned method IDs into abstract, non-copying summaries for direction planning."""
    pinned: dict[tuple[str, int], list[str]] = {}
    for ident, version in (policy.get('preferred_methods') or {}).items():
        if isinstance(ident, str) and type(version) is int:
            pinned.setdefault((ident, version), []).append('author_preferred')
    for slot, route in (policy.get('recommended_slots') or {}).items():
        if isinstance(route, dict):
            for ident, version in (route.get('versions') or {}).items():
                if isinstance(ident, str) and type(version) is int:
                    pinned.setdefault((ident, version), []).append(
                        f"auto:{slot}@{route.get('scope', '')}.{route.get('stage', '')}"
                    )
    if not pinned:
        return []
    try:
        from nw.production_methods.sources import MethodReader
        reader = MethodReader(journal.store.directory.parent)
        if not reader.db_path.is_file():
            return []
    except Exception:
        return []
    summaries = []
    for (ident, version), roles in pinned.items():
        try:
            row = reader.get_method(ident, version)
        except Exception:
            continue
        body = row.get('body') or {}
        summaries.append({
            'id': ident,
            'version': version,
            'title': body.get('title', ''),
            'roles': roles,
            'tasks': list(body.get('tasks', ())),
            'scopes': list(body.get('scopes', ())),
            'target_stages': sorted({o['stage'] for o in body.get('outputs', ()) if o.get('stage')}),
            'applicability': [str(x)[:160] for x in body.get('applicability', ())[:3]],
            'non_applicability': [str(x)[:160] for x in body.get('non_applicability', ())[:2]],
            'output_targets': [
                f"{o.get('stage', '')}.{o.get('field', '')}:{str(o.get('description', ''))[:100]}"
                for o in body.get('outputs', ())[:4]
            ],
        })
    return summaries


def _previous_rejection(journal: Journal) -> dict | None:
    if not (old_id := journal.request.get('direction_retry_of')):
        return None
    row = job_row(journal.store, old_id)
    previous = Journal(journal.store, old_id)
    record = previous.latest(CONFIRM_STEP)
    if (row['status'] != 'REJECTED' or row['step_key'] != CONFIRM_STEP
            or previous.head.branch_id != journal.head.branch_id
            or previous.request['brief_ref'] != journal.request['brief_ref']
            or not record or record['status'] != 'DONE' or record['output']['choice']['action'] != 'reject'):
        raise ValueError('BOOK_DIRECTION: 重新生成须依据同一分支和立项版本已退回的方向短案')
    reason = record['output']['choice']['reason']
    result = {'job_id': old_id, 'reason': reason[:1600],
              'candidates': [{'title': c['title'], 'premise': c['premise']} for c in record['input']['candidates']]}
    if len(reason) > 1600:
        result['reason_chars_omitted'] = len(reason) - 1600
    return result


def prepare_direction_task(calls: JobCalls, key: str) -> TaskRequest:
    j = calls.journal
    j.check_active(key)
    store = j.store
    brief = store.briefs()[-1]
    project = store.project().id
    pin = Ref(**j.request['brief_ref'])
    if pin != legacy_ref('brief', project, brief):
        raise ValueError('STALE_BRIEF: 方向短案所需的立项版本已经改变')
    package = {'brief': asdict(brief), 'branch_head': asdict(j.head), **_creation_input(j),
               'contract': {field: {'name': label, 'max_chars': limit} for field, (label, limit) in FIELDS.items()}}
    if feedback := _previous_rejection(j):
        package['previous_rejection'] = feedback
    messages = [{'role': 'system', 'content': PROMPT}, {'role': 'user', 'content': canonical(package)}]
    params, _ = prepare_call(store, j.id, calls.provider.name, calls.config.params, messages,
                             context_window_tokens=calls.config.context_window_tokens)
    ident = call_id(j.id, key, 1)
    manifest_id = f'{KIND}:{ident}'
    freeze_manifest(store, InputManifest(
        manifest_id, KIND, model_settings(calls.provider, calls.config.model, params, 'book-direction-shortlist-v1'),
        content_sha256(package), brief_ref=pin, novel_job_id=j.id), package)
    return TaskRequest(ident, project, KIND, manifest_id, {'messages': messages}, j.id)
