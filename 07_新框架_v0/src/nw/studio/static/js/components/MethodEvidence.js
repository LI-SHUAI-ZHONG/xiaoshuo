import {esc} from '../ui.js';

export function matchLabel(match) {
  if (!match) return '';
  const labels = {subgenre: '子类型匹配', main: '主类型通用', cross_type: '跨类型通用'};
  return `${labels[match.level]}${match.type_names.length ? ` · ${match.type_names.join('、')}` : ''}`;
}

export function methodEvidence(method) {
  return method.evidence.map((evidence, index) => {
    const location = method.evidence_locations[index];
    return `<div>
      <p class="muted">${esc(location?.book_title || '参考作品')} ${esc(location?.chapters?.join('、') || '')} · 字符 ${evidence.start}–${evidence.end}</p>
      <blockquote class="evidence">${esc(evidence.quote)}</blockquote>
      <p>${esc(evidence.explanation)}</p>
    </div>`;
  }).join('');
}
