import {esc} from '../ui.js';

const options=(pairs,selected)=>Object.entries(pairs).map(([key,label])=>
  `<option value="${esc(key)}" ${selected===key?'selected':''}>${esc(label)}</option>`).join('');
const field=(title,inner)=>`<label class="field"><span>${esc(title)}</span>${inner}</label>`;
const textField=(key,title,val)=>field(title,`<textarea data-key="${key}" rows="2">${esc(val||'')}</textarea>`);

export function passageEditor(host,catalog,doc,initial){
  const kinds=catalog.passage_sequences, names=Object.fromEntries(Object.entries(kinds).map(([k,v])=>[k,v.label]));
  const events=Object.fromEntries(doc.events.filter(e=>e.granularity==='detail').map(e=>[e.id,e.summary]));
  const evidence=new Map(doc.evidence.map(e=>[e.id,e]));
  host.insertAdjacentHTML('beforeend',`<fieldset class="method-section"><legend>连续段落手法</legend>
    ${field('有连续原文依据时选用',`<select data-kind>${options({'':'普通叙述观察',...names},initial?.kind||'')}</select>`)}
    <div data-passage-body></div></fieldset>`);
  const kind=host.querySelector('[data-kind]'), body=host.querySelector('[data-passage-body]');
  function addBeat(container,beat){
    const row=document.createElement('fieldset');
    row.className='method-section';row.dataset.beat='';
    row.innerHTML=`<legend>原文落点</legend>
      ${field('这一拍的作用',`<select data-key="role">${options(kinds[kind.value].roles,beat.role)}</select>`)}
      ${field('实际事件',`<select data-key="event_id">${options({'':'请选择本章细拆事件',...events},beat.event_id)}</select>`)}
      ${field('此处原句','<select data-key="evidence_id"></select>')}
      ${textField('bridge','开场依据或上一拍如何引出本拍',beat.bridge)}
      ${field('所述命题的依据',`<select data-key="claim_status">${options(catalog.narration_claims,beat.claim_status||'stated')}</select>`)}
      ${textField('story_change','原文明示已经发生的变化',beat.story_change)}
      ${textField('reader_change','读者此刻得知、推测或仍想知道什么',beat.reader_change)}
      <button type="button" class="secondary" data-add>在此后插入一拍</button>
      <button type="button" class="ghost" data-remove>移除本拍</button>`;
    const event=row.querySelector('[data-key="event_id"]'), quotes=row.querySelector('[data-key="evidence_id"]');
    function showQuotes(selected){
      const ids=doc.events.find(e=>e.id===event.value)?.evidence_ids||[];
      const labels=Object.fromEntries(ids.filter(id=>evidence.has(id)).map(id=>[id,evidence.get(id).quote]));
      quotes.innerHTML=options({'':'请选择本事件的原文',...labels},selected);
    }
    showQuotes(beat.evidence_id);event.onchange=()=>showQuotes('');
    row.querySelector('[data-add]').onclick=()=>row.after(addBeat(container,{role:row.querySelector('[data-key="role"]').value}));
    row.querySelector('[data-remove]').onclick=()=>row.remove();
    container.append(row);
    return row;
  }
  function show(sequence){
    body.innerHTML='';
    if(!kind.value)return;
    body.innerHTML=textField('condition','适用条件',sequence?.condition)+textField('boundary','不适用边界',sequence?.boundary)+
      '<div data-beats class="stack"></div><button type="button" class="secondary" data-last>在末尾添加落点</button>';
    const container=body.querySelector('[data-beats]');
    for(const beat of sequence?.beats||kinds[kind.value].required_roles.map(role=>({role})))addBeat(container,beat);
    body.querySelector('[data-last]').onclick=()=>addBeat(container,{});
  }
  show(initial);
  kind.onchange=()=>show(kind.value===initial?.kind?initial:null);
  return ()=>{
    if(!kind.value)return null;
    const read=(node,key)=>node.querySelector(`[data-key="${key}"]`).value;
    return {kind:kind.value,condition:read(body,'condition'),boundary:read(body,'boundary'),
      beats:Array.from(body.querySelectorAll('[data-beat]'),row=>
        Object.fromEntries([...row.querySelectorAll('[data-key]')].map(input=>[input.dataset.key,input.value])))};
  };
}
