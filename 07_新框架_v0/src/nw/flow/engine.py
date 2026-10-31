"""Six-node flow with durable checkpoints and at most two revisions."""
from dataclasses import asdict
from typing import Callable
from uuid import NAMESPACE_URL, uuid5

from nw.context.registry import build_context, get_provider
from nw.flow.nodes import NODE_IDS, NodeStore
from nw.generation import call_model, encode
from nw.llm.base import LLMProvider
from nw.models import StateNote
from nw.store import Store

Decision = Callable[[str, dict], str]


class FlowEngine:
    def __init__(self, store: Store, provider: LLMProvider, model: str, params: dict, context_name: str = 'minimal') -> None:
        get_provider(context_name)
        self.context_name = context_name
        self.store, self.provider, self.model, self.params = store, provider, model, params

    def nodes(self, scene_id: str) -> list[dict]:
        state = NodeStore(self.store, scene_id)
        return [state.get(n) for n in NODE_IDS]

    def run(self, scene_id: str, decide: Decision, *, notes: list[dict] | None = None,
            resume: bool = False, retry_failed: bool = False,
            after_node: Callable[[str], None] | None = None) -> dict:
        if self.provider.name == 'fake' and not self.store.test_mode:
            raise ValueError('fake is allowed only in isolated test stores')
        state = NodeStore(self.store, scene_id)
        settings = {'provider': self.provider.name, 'model': self.model, 'params': self.params,
                    'base_url': getattr(self.provider, 'base_url', None),
                    'timeout': getattr(self.provider, 'timeout', None), 'context': self.context_name}
        if resume:
            state.check_settings(settings)
        else:
            state.create(settings, notes or [])
        for node in NODE_IDS:
            record = state.get(node)
            if record['status'] == 'DONE':
                continue
            inputs = state.author_input(node) if node in ('N1', 'N2', 'N3') else record['input']
            state.save(node, 'IN_PROGRESS', record['output'], inputs)
            if state.get(node)['status'] == 'DONE':
                continue  # Another local resume completed this node after our read.
            if node in ('N1', 'N2', 'N3'):
                if decide(node, inputs) != 'confirm':
                    return self.block(state, node, record['output'], 'Author confirmation required')
                state.save(node, 'DONE', inputs)
            elif node == 'N4':
                context = {**state.get('N1')['output'], **state.get('N2')['output'], **state.get('N3')['output']}
                context = build_context(self.store, scene_id, self.context_name, context)
                state.save(node, 'DONE', context, context)
            elif node == 'N5':
                blocked = self.write_review_revise(state, decide, retry_failed)
                if blocked:
                    return blocked
            else:
                self.accept(state)
            if after_node:
                after_node(node)
        return {'scene_id': scene_id, 'status': 'DONE', 'nodes': self.nodes(scene_id)}

    def block(self, state: NodeStore, node: str, output: dict, reason: str) -> dict:
        output['reason'] = reason
        state.save(node, 'BLOCKED', output)
        return {'scene_id': state.scene_id, 'status': 'BLOCKED', 'node': node, 'reason': reason}

    def call_id(self, state: NodeStore, kind: str, output: dict, retry_failed: bool) -> str:
        key = f'{kind}:{output["round"]}'
        attempts = output.setdefault('attempts', {})
        attempt = attempts.get(key, 0)
        prefix = f'nw-flow:{state.scene_id}:{key}'
        run_id = uuid5(NAMESPACE_URL, prefix + (f':retry:{attempt}' if attempt else '')).hex
        row = self.store.connection.execute('SELECT ended_at,finish_reason FROM runs WHERE id=?', (run_id,)).fetchone()
        if retry_failed and row and (not row[0] or row[1] != 'complete'):
            attempts[key] = attempt + 1
            state.save('N5', 'IN_PROGRESS', output)
            run_id = uuid5(NAMESPACE_URL, prefix + f':retry:{attempt + 1}').hex
        return run_id

    def write_review_revise(self, state: NodeStore, decide: Decision, retry_failed: bool) -> dict | None:
        context = state.get('N4')['output']
        output = state.get('N5')['output']
        output.setdefault('round', 0)
        output.setdefault('rejected', [])
        state.save('N5', 'IN_PROGRESS', output, context)
        while True:
            round_no = output['round']
            kind = 'write' if round_no == 0 else 'revise'
            content = {'context': context}
            if round_no:
                content.update(previous_draft=asdict(self.store.get('draft', output['previous_draft'])),
                               review=asdict(self.store.get('run', output['previous_review'])))
            prompt = '根据上下文创作场景正文，只输出正文。' if kind == 'write' else '根据上下文、旧稿和审稿意见修订场景，只输出完整修订正文。'
            messages = [{'role': 'system', 'content': prompt}, {'role': 'user', 'content': encode(content)}]
            run_id = self.call_id(state, kind, output, retry_failed)
            run, draft = call_model(self.store, state.scene_id, self.provider, self.model, self.params,
                                    kind, messages, context, run_id)
            if not run.ended_at or run.finish_reason != 'complete' or draft is None:
                output['run_id'] = run.id
                return self.block(state, 'N5', output, 'Writing call incomplete/failed; retained without automatic retry')
            review_id = self.call_id(state, 'review', output, retry_failed)
            review_messages = [{'role': 'system', 'content': '审查场景与作者需求、设定、视角和场景目标的一致性，列出具体修订意见；不要输出替代正文。'},
                               {'role': 'user', 'content': encode({'context': context, 'draft': asdict(draft)})}]
            review, _ = call_model(self.store, state.scene_id, self.provider, self.model, self.params,
                                   'review', review_messages, context, review_id)
            output.update(draft_id=draft.id, review_id=review.id)
            state.save('N5', 'IN_PROGRESS', output, context)
            if not review.ended_at or review.finish_reason != 'complete':
                return self.block(state, 'N5', output, 'Review incomplete/failed; retained without automatic retry')
            decision = decide('N5', {'draft': asdict(draft), 'review': asdict(review),
                                     'revisions': round_no, 'remaining_revisions': 2 - round_no})
            if decision == 'accept':
                output['decision'] = 'accept'
                state.save('N5', 'DONE', output)
                return None
            if decision != 'revise':
                return self.block(state, 'N5', output, 'Awaiting author decision')
            if draft.id not in output['rejected']:
                output['rejected'].append(draft.id)
            if round_no == 2:
                return self.block(state, 'N5', output, 'Two revisions reached; manual decision required')
            output.update(round=round_no + 1, previous_draft=draft.id, previous_review=review.id)
            state.save('N5', 'IN_PROGRESS', output)

    def accept(self, state: NodeStore) -> None:
        draft_id = state.get('N5')['output']['draft_id']
        current = self.store.accepted(state.scene_id)
        if current is None or current.draft_id != draft_id:
            self.store.accept(draft_id)
        else:
            with self.store.connection:
                self.store.connection.execute('BEGIN IMMEDIATE')
                self.store._export(self.store.get('draft', draft_id))
        # Notes and DONE checkpoint commit together, so resume never duplicates notes.
        with self.store.connection:
            self.store.connection.execute('BEGIN IMMEDIATE')
            if state.get('N6')['status'] == 'DONE':
                return
            notes = state.get('N6')['input']['notes']
            for note in notes:
                self.store._insert('note', StateNote(state.scene_id, note['kind'], note['text']))
            state.save_in_transaction('N6', 'DONE', {'draft_id': draft_id, 'notes': notes},
                                      {'draft_id': draft_id, 'notes': notes})
