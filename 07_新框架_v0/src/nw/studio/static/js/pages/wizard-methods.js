import {esc} from '../ui.js';
import {matchLabel, methodEvidence} from '../components/MethodEvidence.js';

export function methodChoices(selected, currentVersions) {
  if (!selected.size) return '';
  return `<section class="method-section" aria-label="已选制作方法">
    <h3>已选制作方法</h3>
    ${Array.from(selected.values(), method => {
      const latest = currentVersions[method.id];
      const stale = latest !== method.version;
      return `<div class="row wrap">
        <span>${esc(method.title)} · v${method.version}</span>
        ${stale ? `<span class="error">${latest ? `已有 v${latest}，请重新选择` : '当前类型或来源已不适用'}</span>` : ''}
        <button type="button" class="ghost" data-remove-wizard-method="${esc(method.id)}">移除</button>
      </div>`;
    }).join('')}
  </section>`;
}

export function methodRecommendations(methods, selected, currentVersions) {
  return `<section class="method-section" aria-label="类型资料库推荐">
    <div class="row spread wrap"><h3>类型资料库推荐</h3>
      <button type="button" class="secondary" data-refresh-wizard-methods>刷新方法推荐</button>
    </div>
    ${methods.length ? `<div class="rec-grid">${methods.map(method => {
      const active = selected.get(method.id)?.version === method.version;
      return `<article class="rec-card ${active ? 'selected' : ''}">
        <span class="muted">${esc(matchLabel(method.type_match))}</span>
        <h4>${esc(method.title)} · v${method.version}</h4>
        <p>${method.applicability.map(esc).join('。')}</p>
        <button type="button" class="secondary" data-wizard-method="${esc(method.id)}" aria-pressed="${active}">${active ? '取消选择' : '选为制作偏好'}</button>
        <details class="details"><summary>使用步骤、所需前置与原作证据</summary>
          <ul>${method.uses.map(use => `<li>${esc(use.scope_name)} · ${esc(use.stage_name)} · ${use.tasks.map(esc).join('、')}</li>`).join('')}</ul>
          ${method.prerequisites.map(input => `<p>${esc(input.artifact)} · ${esc(input.requirement)}</p>`).join('')}
          <p>不适用情况 · ${method.non_applicability.map(esc).join('。')}</p>
          ${methodEvidence(method)}
        </details>
      </article>`;
    }).join('')}</div>` : '<p class="muted">这个板块暂无匹配的已批准拆解方法。</p>'}
    ${methodChoices(selected, currentVersions)}
  </section>`;
}
