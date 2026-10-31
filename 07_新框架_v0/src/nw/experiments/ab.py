"""Durable blind comparison; choices never automatically accept a draft."""
import hashlib
import json
import random
from uuid import uuid4

from nw.context.registry import build_context
from nw.generation import call_model, encode
from nw.llm.base import LLMProvider
from nw.store import Store, now


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
        with self.store.connection:
            self.store.connection.execute('UPDATE ab_experiments SET status=? WHERE id=?',
                                          ('READY' if complete else 'BLOCKED', experiment_id))
        return self.view(experiment_id)

    def record(self, experiment_id: str | None = None) -> dict:
        if experiment_id is None:
            row = self.store.connection.execute('SELECT * FROM ab_experiments ORDER BY rowid DESC LIMIT 1').fetchone()
        else:
            row = self.store.connection.execute('SELECT * FROM ab_experiments WHERE id=?', (experiment_id,)).fetchone()
        if row is None:
            raise ValueError('Experiment not found')
        result = dict(row)
        mapping = json.loads(result['mapping_json'])
        if seal(mapping) != result['seal']:
            raise ValueError('Experiment seal mismatch: mapping was modified')
        if (set(mapping) != {'1', '2'} or any(not isinstance(x, dict)
                or set(x) != {'provider', 'run_id'} for x in mapping.values())):
            raise ValueError('Invalid sealed mapping')
        result['mapping'] = mapping
        return result

    def view(self, experiment_id: str | None = None) -> dict:
        row = self.record(experiment_id)
        result = {'experiment_id': row['id'], 'status': row['status'], 'seal': row['seal']}
        if row['status'] == 'READY':
            for number, label in [('1', '一'), ('2', '二')]:
                result[label] = self.store.get('run', row['mapping'][number]['run_id']).output_text
        return result

    def choose(self, choice: int, experiment_id: str | None = None) -> dict:
        if choice not in (1, 2):
            raise ValueError('Choice must be 1 or 2')
        with self.store.connection:
            self.store.connection.execute('BEGIN IMMEDIATE')
            row = self.record(experiment_id)
            if row['status'] != 'READY':
                raise ValueError('Both generations must be complete before choose')
            if row['revealed'] or row['choice'] is not None:
                raise ValueError('Choice already recorded or experiment revealed')
            self.store.connection.execute('UPDATE ab_experiments SET choice=? WHERE id=?', (choice, row['id']))
        return {'experiment_id': row['id'], 'choice': choice, 'seal': row['seal']}

    def reveal(self, experiment_id: str | None = None) -> dict:
        with self.store.connection:
            self.store.connection.execute('BEGIN IMMEDIATE')
            row = self.record(experiment_id)
            if row['status'] != 'READY' or row['choice'] is None:
                raise ValueError('Use ab choose before reveal')
            self.store.connection.execute('UPDATE ab_experiments SET revealed=1 WHERE id=?', (row['id'],))
        return {'experiment_id': row['id'], 'choice': row['choice'], 'seal': row['seal'],
                'verified': True, 'providers': {k: v['provider'] for k, v in row['mapping'].items()},
                'mapping': row['mapping']}
