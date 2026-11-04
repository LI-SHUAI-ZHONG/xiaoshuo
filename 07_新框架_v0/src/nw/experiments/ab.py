"""Durable blind comparison; choices never automatically accept a draft."""
import hashlib
import json
import random
from uuid import uuid4

from nw.call_budget import BudgetExceeded, _cost, _insert_budget, _money, prepare_call
from nw.call_control import check_test_provider, execution_lock, model_settings
from nw.cards import eligible_rule_refs, read_card
from nw.context.registry import build_context
from nw.context.story import WRITE_PROMPT, StoryScope, build_story_context, scene_scope
from nw.generation import call_model, encode, recover_run
from nw.llm.base import LLMProvider
from nw.store import Store, now
from nw.story_models import CardRef, SourceRef
from nw.task_models import Budget, InputManifest, canonical, content_sha256
from nw.tasks import _insert_manifest, read_input_manifest


def seal(mapping: dict) -> str:
    canonical = json.dumps(mapping, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:8]


class Experiment:
    def __init__(self, store: Store) -> None:
        self.store = store

    def start(self, scene_id: str, provider: LLMProvider, model: str, params: dict,
              *, a: str = 'minimal', b: str = 'rules_pack', seed: int | None = None) -> dict:
        if provider.name == 'fake' and not self.store.test_mode:
            raise ValueError('fake is allowed only in isolated test stores')
        # Validate both contexts before making any model call.
        packages = [build_context(self.store, scene_id, name) for name in (a, b)]
        arms = [{'provider': name, 'run_id': uuid4().hex} for name in (a, b)]
        order = [0, 1]
        random.Random(seed).shuffle(order)
        mapping = {str(i + 1): arms[arm] for i, arm in enumerate(order)}
        experiment_id = uuid4().hex
        with self.store.connection:
            self.store.connection.execute('INSERT INTO ab_experiments VALUES (?,?,?,?,?,NULL,0,?)',
                (experiment_id, scene_id, encode(mapping), seal(mapping), 'IN_PROGRESS', now()))
        complete = True
        for arm, context in zip(arms, packages):
            messages = [{'role': 'system', 'content': '根据作者需求、设定和场景卡创作本场景正文。只输出正文，不输出资料标签或解释。'},
                        {'role': 'user', 'content': encode(context)}]
            run, draft = call_model(self.store, scene_id, provider, model, params,
                                    'write', messages, context, arm['run_id'])
            complete = complete and run.finish_reason == 'complete' and draft is not None
        self._finish(experiment_id, complete)
        return self.view(experiment_id)

    def start_story(self, scene_id: str, provider: LLMProvider, model: str, params: dict, *,
                    budget: Budget, scope: StoryScope | None = None, branch: str = 'main',
                    seed: int | None = None) -> dict:
        check_test_provider(self.store, provider)
        if not self.store.managed_story():
            raise ValueError('Story A/B requires story adoption')
        if type(budget.max_calls) is not int or budget.max_calls < 2:
            raise ValueError('Story A/B requires a budget for two calls')
        scope = scope or scene_scope(self.store, scene_id, branch)
        work = build_story_context(self.store, scene_id, scope, budget.context_char_limit)
        methods = work.selection['selected_refs']
        if not methods:
            raise ValueError('Story A/B needs at least one eligible method in the work package')

        experiment = uuid4().hex
        budget_id = f'ab:{experiment}'
        arms = [{'provider': name, 'run_id': uuid4().hex} for name in ('no_methods', 'selected_methods')]
        random.Random(seed).shuffle(arms)
        mapping = {str(i): arm for i, arm in enumerate(arms, start=1)}
        full = {'items': work.package['items']}
        base = {'items': [item for item in full['items'] if not item['source'].startswith('rule:')]}
        comparison = {'base_sha256': content_sha256(base), 'method_refs': methods, 'budget_id': budget_id,
                      'branch_id': scope.branch_id, 'state_revision': scope.revision}
        sealed = {'mapping': mapping, 'comparison': comparison}
        record = {'version': 2, **sealed, 'choice_reason': None}
        selected = {CardRef(**raw) for raw in methods}
        base_cards = tuple(raw for raw in work.card_refs if CardRef(**raw) not in selected)
        base_sources = {SourceRef(**source): source for raw in base_cards
                        for source in read_card(self.store, CardRef(**raw))['source_refs']}
        with execution_lock(self.store, f'ab:{experiment}') as acquired:
            if not acquired:
                raise ValueError('Experiment is already being started')
            requests = []
            with self.store.connection:
                self.store.connection.execute('BEGIN IMMEDIATE')
                _insert_budget(self.store, budget_id, budget)
                for arm in arms:
                    include = arm['provider'] == 'selected_methods'
                    context = full if include else base
                    messages = [{'role': 'system', 'content': WRITE_PROMPT},
                                {'role': 'user', 'content': canonical(context)}]
                    effective, estimate = prepare_call(self.store, budget_id, provider.name, params, messages)
                    ident = f"ab:{arm['run_id']}"
                    manifest = InputManifest(
                        ident, 'write', model_settings(provider, model, effective, 'story-ab-v1'), content_sha256(context),
                        brief_ref=work.brief_ref, card_refs=work.card_refs if include else base_cards,
                        source_refs=work.source_refs if include else tuple(base_sources.values()),
                        branch_id=scope.branch_id, state_revision=scope.revision, story_order=scope.story_order,
                        disclosure_order=work.disclosure, predecessor_drafts=work.predecessor_drafts,
                        dependency_refs=tuple(ref for ref in work.dependency_refs if include or ref.kind != 'card'
                                              or CardRef(ref.id, ref.version) not in selected),
                        selection={**work.selection, 'manifest_id': ident} if include else None)
                    _insert_manifest(self.store, manifest, context)
                    requests.append((arm['run_id'], context, messages, manifest, estimate))
                if budget.max_cost is not None:
                    cost = sum(_cost(budget.price_snapshot, estimate['input_tokens'], estimate['output_tokens'])
                               for _, _, _, _, estimate in requests)
                    if cost > _money(budget.max_cost):
                        raise BudgetExceeded('COST_LIMIT: Story A/B needs enough budget for both calls')
                self.store.connection.execute('INSERT INTO ab_experiments VALUES (?,?,?,?,?,NULL,0,?)',
                    (experiment, scene_id, encode(record), seal(sealed), 'IN_PROGRESS', now()))

            def current() -> None:
                if not selected <= set(eligible_rule_refs(self.store)):
                    raise ValueError('STALE_METHOD_VERSION: comparison inputs changed before the call')

            complete = True
            for run_id, context, messages, manifest, _ in requests:
                try:
                    run, draft = call_model(self.store, scene_id, provider, model, params, 'write', messages,
                                            context, run_id, budget_id=budget_id, story_manifest=manifest,
                                            before_reserve=current)
                except ValueError as exc:
                    self._finish(experiment, False)
                    return {**self.view(experiment), 'reason': str(exc)}
                complete = complete and run.ended_at and run.finish_reason == 'complete' and draft is not None
            self._finish(experiment, bool(complete))
            return self.view(experiment)

    def _finish(self, experiment_id: str, complete: bool) -> None:
        with self.store.connection:
            self.store.connection.execute('UPDATE ab_experiments SET status=? WHERE id=?',
                                          ('READY' if complete else 'BLOCKED', experiment_id))

    def record(self, experiment_id: str | None = None) -> dict:
        if experiment_id is None:
            row = self.store.connection.execute('SELECT * FROM ab_experiments ORDER BY rowid DESC LIMIT 1').fetchone()
        else:
            row = self.store.connection.execute('SELECT * FROM ab_experiments WHERE id=?', (experiment_id,)).fetchone()
        if row is None:
            raise ValueError('Experiment not found')
        result = dict(row)
        data = json.loads(result['mapping_json'])
        mapping = data
        if isinstance(data, dict) and data.get('version') == 2:
            if set(data) != {'version', 'mapping', 'comparison', 'choice_reason'}:
                raise ValueError('Invalid story comparison record')
            mapping = data['mapping']
            result['comparison'] = data['comparison']
            result['choice_reason'] = data['choice_reason']
        sealed = {'mapping': mapping, 'comparison': result['comparison']} if 'comparison' in result else mapping
        if seal(sealed) != result['seal']:
            raise ValueError('Experiment seal mismatch: mapping was modified')
        if (not isinstance(mapping, dict) or set(mapping) != {'1', '2'} or any(not isinstance(x, dict)
                or set(x) != {'provider', 'run_id'} for x in mapping.values())):
            raise ValueError('Invalid sealed mapping')
        result['mapping'] = mapping
        return result

    def _recover_story_pair(self, row: dict) -> dict:
        if row['status'] != 'IN_PROGRESS' or 'comparison' not in row:
            return row
        with execution_lock(self.store, f"ab:{row['id']}") as acquired:
            row = self.record(row['id'])
            if not acquired or row['status'] != 'IN_PROGRESS':
                return row
            draft_runs = {draft.run_id for draft in self.store.drafts(row['scene_id'])}
            complete = True
            for arm in row['mapping'].values():
                ident = arm['run_id']
                if not self.store.connection.execute('SELECT 1 FROM runs WHERE id=?', (ident,)).fetchone():
                    complete = False
                    continue
                run = recover_run(self.store, ident)
                if run is None:
                    return row
                complete = complete and run.finish_reason == 'complete' and bool(run.ended_at) and ident in draft_runs
            self._finish(row['id'], complete)
            return self.record(row['id'])

    def view(self, experiment_id: str | None = None) -> dict:
        row = self._recover_story_pair(self.record(experiment_id))
        result = {'experiment_id': row['id'], 'status': row['status'], 'seal': row['seal']}
        if row['status'] == 'READY':
            for number, label in [('1', '一'), ('2', '二')]:
                result[label] = self.store.get('run', row['mapping'][number]['run_id']).output_text
        return result

    def choose(self, choice: int, experiment_id: str | None = None, *, reason: str | None = None) -> dict:
        if choice not in (1, 2):
            raise ValueError('Choice must be 1 or 2')
        experiment_id = self._recover_story_pair(self.record(experiment_id))['id']
        with self.store.connection:
            self.store.connection.execute('BEGIN IMMEDIATE')
            row = self.record(experiment_id)
            if row['status'] != 'READY':
                raise ValueError('Both generations must be complete before choose')
            if row['revealed'] or row['choice'] is not None:
                raise ValueError('Choice already recorded or experiment revealed')
            if 'comparison' in row:
                if not isinstance(reason, str) or not reason.strip():
                    raise ValueError('Story A/B requires a reason for the blind choice')
                self._verify_story_pair(row)
                data = json.loads(row['mapping_json'])
                data['choice_reason'] = reason
                self.store.connection.execute('UPDATE ab_experiments SET choice=?,mapping_json=? WHERE id=?',
                                              (choice, encode(data), row['id']))
            else:
                if reason is not None:
                    raise ValueError('Choice reasons are available for story A/B')
                self.store.connection.execute('UPDATE ab_experiments SET choice=? WHERE id=?', (choice, row['id']))
        return {'experiment_id': row['id'], 'choice': choice, 'seal': row['seal']}

    def reveal(self, experiment_id: str | None = None) -> dict:
        with self.store.connection:
            self.store.connection.execute('BEGIN IMMEDIATE')
            row = self.record(experiment_id)
            if row['status'] != 'READY' or row['choice'] is None:
                raise ValueError('Use ab choose before reveal')
            if 'comparison' in row:
                self._verify_story_pair(row)
            self.store.connection.execute('UPDATE ab_experiments SET revealed=1 WHERE id=?', (row['id'],))
        result = {'experiment_id': row['id'], 'choice': row['choice'], 'seal': row['seal'],
                  'verified': True, 'providers': {k: v['provider'] for k, v in row['mapping'].items()},
                  'mapping': row['mapping']}
        if 'comparison' in row:
            result.update(comparison=row['comparison'], choice_reason=row['choice_reason'])
        return result

    def _verify_story_pair(self, row: dict) -> None:
        by_arm = {}
        for arm in row['mapping'].values():
            run = self.store.get('run', arm['run_id'])
            snapshot = json.loads(run.input_snapshot_json)
            manifest, package = read_input_manifest(self.store, snapshot['manifest_id'])
            if (run.scene_id != row['scene_id'] or run.finish_reason != 'complete'
                    or any(snapshot.get(key) != value for key, value in manifest['settings'].items())
                    or json.loads(run.params_json) != manifest['settings']['params']
                    or snapshot['messages'][1]['content'] != canonical(package)
                    or json.loads(run.context_package_json) != package):
                raise ValueError('Story A/B run does not match the frozen input')
            by_arm[arm['provider']] = (snapshot, manifest, package)
        if set(by_arm) != {'no_methods', 'selected_methods'}:
            raise ValueError('Invalid story A/B arms')
        a, base, plain = by_arm['no_methods']
        b, selected, full = by_arm['selected_methods']
        comparison = row['comparison']
        fields = ('brief_ref', 'branch_id', 'state_revision', 'story_order', 'disclosure_order',
                  'predecessor_drafts', 'settings')
        methods = comparison['method_refs']
        if (any(base[key] != selected[key] for key in fields) or a['messages'][0] != b['messages'][0]
                or comparison['branch_id'] != base['branch_id'] or comparison['state_revision'] != base['state_revision']
                or base['card_refs'] != [ref for ref in selected['card_refs'] if ref not in methods]
                or plain != {'items': [item for item in full['items'] if not item['source'].startswith('rule:')]}
                or content_sha256(plain) != comparison['base_sha256']
                or not methods or (selected.get('selection') or {}).get('selected_refs') != methods):
            raise ValueError('Story A/B inputs differ outside the method cards')
