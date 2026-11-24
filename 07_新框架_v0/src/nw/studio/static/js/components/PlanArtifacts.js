import {esc, readable} from '../ui.js';

const scopes = {book:'全书', volume:'卷纲', chapter:'章纲', scene:'场景', replan:'改案'};
const fields = {
  volume:{goal:'阶段目标', turn:'卷末转折', ending_direction:'卷末交接'},
  chapter:{goal:'本章目标', consequence:'章末变化', reader_promise:'读者期待'},
  scene:{function:'本场职责', goal:'本场目标', location:'地点', story_time:'故事时间',
    entering_state:'进入状态', conflict:'本场冲突', choice:'人物选择', planned_result:'本场结果',
    pov:'视角人物', allowed_disclosure:'可披露的信息'},
};
const eventFields = {goal:'事件目标', setting:'发生处境', obstacle:'阻碍', completion_condition:'完成条件'};

function definitionList(data, labels) {
  const entries = Object.entries(labels).filter(([key]) => data[key]);
  return entries.length ? `<dl class="selection-summary">${entries.map(([key, label]) =>
    `<dt>${label}</dt><dd>${esc(data[key])}</dd>`).join('')}</dl>` : '';
}

export function scopeName(scope) {
  return scopes[scope] || '';
}

export function approvedParent(parent) {
  const scope = scopeName(parent?.scope);
  if (!scope || !parent.title) return '';
  const number = parent.artifact?.ref?.version ?? parent.version ?? parent.root?.version;
  const version = Number.isInteger(number) && number > 0 ? ` · 第 ${number} 版` : '';
  return `<section class="design-card"><h3>上一级已批准方案</h3>
    <p>${scope}${version}</p><strong>${esc(parent.title)}</strong>
    ${parent.artifact?.kind === 'volume' ? definitionList(parent.artifact.body || {}, fields.volume) : ''}</section>`;
}

function scopeArtifact(member) {
  const {kind, body} = member;
  const {title, ...other} = body;
  for (const key of Object.keys(fields[kind])) delete other[key];
  return `<section class="design-card">
    <p class="muted">${scopeName(kind)}</p><h3>${esc(title || scopeName(kind))}</h3>
    ${definitionList(body, fields[kind])}
    ${Object.keys(other).length ? `<details class="details"><summary>更多${scopeName(kind)}字段</summary>${readable(other)}</details>` : ''}
    </section>`;
}

export function approvedChapter(chapter) {
  if (!chapter) return '';
  const body = chapter.body || chapter.chapter?.body;
  if (!body?.title && !chapter.title) return '';
  return `<details class="details" open><summary>本章已批准章纲</summary>
    ${body ? scopeArtifact({kind:'chapter',body}) : `<p>${esc(chapter.title)}</p>`}</details>`;
}

export function chapterOutline(chapter, events = [], direction = {}) {
  if (!chapter?.body) return '';
  const choice = definitionList(direction, {conflict:'本章矛盾', choice:'人物选择', cost:'选择代价'});
  return scopeArtifact({kind:'chapter',body:chapter.body})
    + (choice ? `<section class="design-card"><h3>本章关键选择</h3>${choice}</section>` : '')
    + (events.length ? `<section><h3>本章计划推进的事件</h3>${events.map(event =>
      `<div class="design-card">${definitionList(event, eventFields)}</div>`).join('')}</section>` : '');
}

export function planArtifacts(output) {
  if (!Array.isArray(output?.members)) return readable(output);
  const visible = [], other = [];
  for (const member of output.members) {
    if (fields[member?.kind] && member.body) visible.push(member);
    else other.push(member);
  }
  const {members, ...rest} = output;
  if (other.length) rest.members = other.map(member => member?.body || member);
  return visible.map(scopeArtifact).join('') + (Object.keys(rest).length ? readable(rest) : '');
}
