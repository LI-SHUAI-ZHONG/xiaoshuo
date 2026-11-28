"""Fit the frozen story package through drafting, independent review and revision."""
from __future__ import annotations

import json

from nw.call_budget import BudgetExceeded, check_window, message_size, output_cap, read_budget
from nw.length_plan import frozen_scene_budget, scene_length_feedback
from nw.materials.evidence import review_contract, scene_materials
from nw.studio.craft_materials import design_genre_ids
from nw.materials.steps.review import MATERIAL as REVIEW_MATERIAL
from nw.materials.steps.writing import MATERIAL as WRITING_MATERIAL
from nw.models import Draft
from nw.novel_calls import JobCalls
from nw.scene_messages import draft_messages
from nw.store import now
from nw.task_models import canonical


class SceneCapacity:
    def __init__(self, calls: JobCalls, scene: str, chain: tuple[tuple[str, str], ...]) -> None:
        journal = calls.journal
        self.budget = read_budget(journal.store, journal.id)
        prior_id = journal.request['original_drafts'].get(scene)
        self.prior = journal.store.get('draft', prior_id) if prior_id else None
        stages = ['write', 'review']
        if self.budget.max_revisions or self.prior:
            stages.append('revise')
        self.runtimes = {stage: calls.for_stage(stage) for stage in stages}
        self.caps = {stage: output_cap(runtime.provider.name, runtime.config.params, self.budget.output_limit)[1]
                     for stage, runtime in self.runtimes.items()}
        # Size the real envelope (including private checks, character cards and
        # comparison passages). The empty draft is never stored or sent.
        version = journal.store.connection.execute('SELECT coalesce(max(version),0)+1 FROM drafts WHERE scene_id=?',
                                                   (scene,)).fetchone()[0]
        self.draft_shape = Draft('0' * 32, scene, version, '', 'complete', '0' * 32, now())
        head = journal.head
        manifest = {
            'branch_id': head.branch_id, 'state_revision': head.revision, 'candidate_delta_refs': chain,
        }
        self.contract, _ = review_contract(journal.store, self.draft_shape, manifest)
        self.genre_ids = design_genre_ids(scene_materials(journal.store, scene))
        self.feedback_shape = scene_length_feedback(journal.store, scene, manifest, '')
        self.omitted_for: set[str] = set()

    def check(self, prompt: str, package: dict, keys: set[str]) -> dict:
        planned = frozen_scene_budget(package)
        # Without an approved upper bound reserve one prose character per output
        # token as a CJK planning estimate; actual messages are checked again.
        prose_chars = planned['max_words'] if planned else max(self.caps[k] for k in ('write', 'revise') if k in self.caps)
        basis = 'approved_scene_max_words' if planned else 'one_cjk_character_per_output_token'
        for item in package['items']:
            if item['source'] == 'chapter:length':
                progress = json.loads(item['text'])
                upper = progress['feasible_max_words']
                if progress.get('length_mode') == 'tiered' or planned and upper < prose_chars:
                    prose_chars, basis = upper, 'feasible_chapter_scene_max_words'
                break
        try:
            return self._check_stages(prompt, package, keys, prose_chars, basis)
        except BudgetExceeded as exc:
            sizes: dict[str, int] = {}
            for item in package['items']:
                sizes[item['reason']] = sizes.get(item['reason'], 0) + len(item['text'])
            largest = sorted(sizes.items(), key=lambda item: item[1], reverse=True)[:3]
            breakdown = '、'.join(f'{label} {size} 字符' for label, size in largest)
            raise BudgetExceeded(f'{exc} 本场稿件预估 {prose_chars} 字符，主要资料：{breakdown}。') from exc

    def _check_stages(self, prompt: str, package: dict, keys: set[str], prose_chars: int,
                      basis: str) -> dict:
        from nw.context.briefing_compiler import compile_writer_briefing, should_use_natural_briefing
        write_rt = self.runtimes['write']
        user_body = (
            compile_writer_briefing(package)
            if should_use_natural_briefing(write_rt.provider.name, write_rt.config, store=write_rt.journal.store)
            else canonical(package)
        )
        writing_messages = [{'role': 'system', 'content': prompt}, {'role': 'user', 'content': user_body}]
        report = {'write': self._fit('write', writing_messages, 0, 0)}
        review, _ = draft_messages(package, 'review', self.draft_shape, None, self.contract, REVIEW_MATERIAL, keys,
                                   self.feedback_shape, genre_ids=self.genre_ids)
        report['review'] = self._fit('review', review, prose_chars, 3 * prose_chars)
        if 'revise' in self.runtimes:
            revise, _ = draft_messages(package, 'revise', self.draft_shape, {}, None, WRITING_MATERIAL, keys,
                                       self.feedback_shape, genre_ids=self.genre_ids)
            review_chars = self.caps['review']
            report['revise'] = self._fit('revise', revise, prose_chars + review_chars, 3 * (prose_chars + review_chars))
            if self.prior:
                # A manual revision can start with an actual, much longer old draft.
                actual, _ = draft_messages(package, 'revise', self.prior, {}, None, WRITING_MATERIAL, keys,
                                           genre_ids=self.genre_ids)
                report['initial_revision'] = self._fit('revise', actual, 0, 0)
        return {'stages': report, 'reserved_draft_chars': prose_chars,
                'draft_estimate_basis': basis,
                'input_estimate_basis': 'utf8_bytes_plus_chat_framing',
                'optional_context_limited_by': sorted(self.omitted_for)}

    def _fit(self, stage: str, messages: list[dict], extra_chars: int, extra_bytes: int) -> dict:
        runtime = self.runtimes[stage]
        window = getattr(runtime.config, 'context_window_tokens', None)
        cap = self.caps[stage]
        chars, estimated = message_size(messages)
        chars += extra_chars
        estimated += extra_bytes
        label = {'write': '写作', 'review': '审稿', 'revise': '修订'}[stage]
        try:
            if chars > self.budget.context_char_limit:
                raise BudgetExceeded(f'CONTEXT_TOO_LARGE: 预计输入 {chars} 字符，任务上限 {self.budget.context_char_limit}')
            check_window(estimated, cap, window)
        except BudgetExceeded as exc:
            self.omitted_for.add(stage)
            raise BudgetExceeded(f'{exc}。{label}模型 {runtime.config.model} 无法容纳本场必需输入及预留空间，'
                                 '请拆分场景，或核对模型窗口后调整制作预算。') from exc
        return {'model': runtime.config.model, 'input_chars': chars, 'estimated_input_tokens': estimated,
                'reserved_output_tokens': cap, 'model_window_tokens': window,
                'window_check': 'estimated' if window is not None else 'unknown'}
