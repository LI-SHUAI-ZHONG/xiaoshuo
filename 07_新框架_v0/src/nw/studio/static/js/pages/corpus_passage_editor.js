import {esc} from '../ui.js';

const options=(pairs,selected)=>Object.entries(pairs).map(([key,label])=>
  `<option value="${esc(key)}" ${selected===key?'selected':''}>${esc(label)}</option>`).join('');
const field=(title,inner)=>`<label class="field"><span>${esc(title)}</span>${inner}</label>`;
const textField=(key,title,val)=>field(title,`<textarea data-key="${key}" rows="2">${esc(val||'')}</textarea>`);
const judgmentKind=kind=>['qualified_claim','interpreted_motive'].includes(kind);

function chapterBodyStarts(units,source){
  const starts=new Map();
  if(!source)return starts;
  const chapters=units.filter(u=>u.level==='chapter'&&u.boundary_basis==='source_heading').sort((a,b)=>a.start-b.start);
  let offset=0,index=0;
  // Corpus offsets count Unicode code points. The browser indexes a string in UTF-16.
  function advance(){
    const code=source.codePointAt(index);
    index+=code>0xffff?2:1;
    offset++;
    return code;
  }
  for(const chapter of chapters){
    while(index<source.length&&offset<chapter.start)advance();
    while(index<source.length&&offset<chapter.end){if(advance()===10)break;}
    starts.set(chapter.id,offset);
  }
  return starts;
}

export function passageEditor(host,catalog,doc,initial,source){
  const kinds=catalog.passage_sequences;
  const group=(single,label)=>{
    const names=Object.fromEntries(Object.entries(kinds).filter(([,v])=>(v.required_roles.length===1)===single).map(([k,v])=>[k,v.label]));
    return Object.keys(names).length?`<optgroup label="${esc(label)}">${options(names,initial?.kind)}</optgroup>`:'';
  };
  const events=Object.fromEntries(doc.events.filter(e=>e.granularity==='detail').map(e=>[e.id,e.summary]));
  const units=new Map(doc.units.map(u=>[u.id,u]));
  const bodyStarts=chapterBodyStarts(doc.units,source);
  const nonstory=doc.evidence.filter(e=>['heading','reader_address'].includes(e.text_role)).sort((a,b)=>a.start-b.start);
  const evidence=new Map();
  let index=0;
  for(const e of [...doc.evidence].sort((a,b)=>a.start-b.start)){
    while(index<nonstory.length&&nonstory[index].end<=e.start)index++;
    if(index===nonstory.length||e.end<=nonstory[index].start)evidence.set(e.id,e);
  }
  host.insertAdjacentHTML('beforeend',`<fieldset class="method-section"><legend>段落写法与原作证据</legend>
    ${field('选取原文实际使用的一种写法',`<select data-kind>${options({'':'普通叙述观察'},initial?.kind||'')}${group(true,'一处原句可举证')}${group(false,'需要前后原句共同举证')}</select>`)}
    <div data-passage-body></div></fieldset>`);
  const kind=host.querySelector('[data-kind]'), body=host.querySelector('[data-passage-body]');
  function addBeat(container,beat){
    const row=document.createElement('fieldset');
    row.className='method-section';row.dataset.beat='';
    const judgment=judgmentKind(kind.value);
    const claims=Object.fromEntries(Object.entries(catalog.narration_claims).filter(([key])=>!judgment||key!=='stated'));
    const claim=Object.hasOwn(claims,beat.claim_status)?beat.claim_status:judgment?'unknown':'stated';
    row.innerHTML=`<legend>原文落点</legend>
      ${field('这一拍的作用',`<select data-key="role">${options(kinds[kind.value].roles,beat.role)}</select>`)}
      ${field('实际事件',`<select data-key="event_id" required>${options({'':'请选择本章细拆事件',...events},beat.event_id)}</select>`)}
      ${field('此处故事正文原句','<select data-key="evidence_id" required></select>')}
      ${textField('bridge','开场依据或上一拍如何引出本拍',beat.bridge)}
      ${field('所述命题的依据',`<select data-key="claim_status">${options(claims,claim)}</select>`)}
      ${judgment?`<input type="hidden" data-key="story_change" value="">
        ${beat.story_change?`<p>原记录将此句登记为已经发生的变化，请核对并改写到读者所得中。<br>${esc(beat.story_change)}</p>`:''}`:textField('story_change','原文明示已经发生的变化',beat.story_change)}
      ${textField('reader_change','读者此刻得知、推测或仍想知道什么',beat.reader_change)}
      <button type="button" class="secondary" data-add>在此后插入一拍</button>
      <button type="button" class="ghost" data-remove>移除本拍</button>`;
    const event=row.querySelector('[data-key="event_id"]'), quotes=row.querySelector('[data-key="evidence_id"]');
    function showQuotes(selected){
      const observed=doc.events.find(e=>e.id===event.value),unit=units.get(observed?.unit_id);
      const bodyStart=bodyStarts.get(unit?.level==='scene'?unit.parent_id:unit?.id);
      const rows=(observed?.evidence_ids||[]).map(id=>evidence.get(id)).filter(e=>e&&
        (bodyStart==null||e.start>=bodyStart||e.end>bodyStart&&Array.from(e.quote).slice(bodyStart-e.start).join('').trim()));
      const labels=Object.fromEntries(rows.map(e=>[e.id,e.quote]));
      const hint=event.value&&!Object.keys(labels).length?'本事件缺少可用的故事正文引文':'请选择本事件的故事正文';
      quotes.innerHTML=options({'':hint,...labels},selected);
    }
    showQuotes(beat.evidence_id);event.onchange=()=>showQuotes('');
    row.querySelector('[data-add]').onclick=()=>row.after(addBeat(container,{role:row.querySelector('[data-key="role"]').value}));
    row.querySelector('[data-remove]').onclick=()=>row.remove();
    container.append(row);
    return row;
  }
  function show(sequence){
    body.innerHTML='';
    const judgment=judgmentKind(kind.value);
    const outer=host.querySelector('[name="detail_claim_status"]');
    if(outer){
      const stated=outer.querySelector('[value="stated"]');
      if(stated)stated.disabled=judgment;
      if(judgment&&outer.value==='stated')outer.value='unknown';
    }
    if(!kind.value)return;
    body.innerHTML=(judgment?'<p>请将判断者的说法、推测或未知写入读者所得。后文确证的事另引原文。</p>':'')+
      (kinds[kind.value].role_order_flexible?'<p>按原文先后选择作用，陈设和活动都可以先写。</p>':'')+
      textField('condition','适用条件',sequence?.condition)+textField('boundary','不适用边界',sequence?.boundary)+
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
