import {api,enc} from '../api.js';
import {$,$$,esc,modal,busy,toast} from '../ui.js';
import {passageEditor} from './corpus_passage_editor.js';

const optionList=(rows,value='',multiple=false)=>Object.entries(rows).map(([key,label])=>`<option value="${esc(key)}" ${(multiple?value.includes(key):value===key)?'selected':''}>${esc(label)}</option>`).join('');
const field=(label,control)=>`<label class="field"><span>${esc(label)}</span>${control}</label>`;
const blankId=section=>`${section[0].toUpperCase()}_${Date.now()}`;

export function openCorpusEditor({book,catalog,record,section,row=null,initialDomain='',reload}){
  const document=record.body,existing=row;
  const names=rows=>Object.fromEntries(rows.map(r=>[r.id,`${r.id} · ${r.title||r.name||r.summary||r.quote||''}`.slice(0,140)]));
  const refOptions={evidence_ids:names(document.evidence),characters:names(document.characters),node_ids:names(document.events),
    parent_event_ids:names(document.events.filter(e=>e.granularity==='overview')),unit_id:names(document.units),
    parent_id:{'':'无上级（仅全书）',...names(document.units.filter(u=>u.id!==row?.id))},
    canonical_id:{'':'未归并',...names(document.characters.filter(p=>p.id!==row?.id))},
    thread_id:{'':'独立关系',...names(document.threads)},source:names(document.events),target:names(document.events)};
  const multikeys=['evidence_ids','characters','node_ids','parent_event_ids'];
  const selections={level:catalog.levels,domain:catalog.domains,kind:catalog.link_kinds,certainty:catalog.certainty,
    granularity:catalog.granularity,boundary_basis:{source_file:'原始文件',source_heading:'原文标题',analyst_inference:'分析推断',author_confirmed:'作者核对'},
    status:section==='threads'?catalog.thread_statuses:catalog.domain_statuses};
  let value=structuredClone(row||{});
  if(!row&&catalog.row_fields[section]){
    for(const key of Object.keys(catalog.row_fields[section])){
      value[key]=multikeys.includes(key)?[]:key==='details'?{}:['parent_id','canonical_id','thread_id','story_order'].includes(key)?null:
        ['start','end'].includes(key)?0:key==='id'?blankId(section):refOptions[key]?Object.keys(refOptions[key])[0]||'':selections[key]?Object.keys(selections[key])[0]:'';
    }
    if(section==='events')value.granularity='detail';
    if(section==='evidence'){value.start='';value.end='';}
    if(section==='units')value.boundary_basis='analyst_inference';
    if(section==='links')value.certainty='inferred';
    if(section==='threads')value.status='open';
    if(section==='domains')value.status='uncertain';
    if('domain' in value&&Object.hasOwn(catalog.domains,initialDomain))value.domain=initialDomain;
  }
  function control(key,label,current){
    if(key==='details')return '<div id="corpusDomainDetails" class="stack"></div>';
    if(refOptions[key]||selections[key]){
      const multi=multikeys.includes(key),opts=refOptions[key]||selections[key];
      return field(label,`<select name="${key}" ${multi?'multiple size="5"':''}>${optionList(opts,multi?current||[]:current||'',multi)}</select>`);
    }
    if(['start','end','story_order'].includes(key))return field(label,`<input name="${key}" type="number" min="0" value="${current??''}">`);
    if(key==='id')return field(label,`<input name="id" value="${esc(current||blankId(section))}" ${existing?'readonly':''}>`);
    return field(label,`<textarea name="${key}" rows="${key==='quote'?5:3}">${esc(current||'')}</textarea>`);
  }
  let fields;
  if(section==='overview'){value=row||document.overview;fields=Object.entries(catalog.overview_fields);}
  else if(section==='source_extent'){
    value=row||document.source_extent;selections.status=catalog.source_extents;
    fields=[['status','参考文本完整性'],['note','作者核对依据（不是模型判断）']];
  }else if(section==='uncertainties'){
    value={text:(row||document.uncertainties).join('\n')};fields=[['text','待核实项（每行一条）']];
  }else fields=Object.entries(catalog.row_fields[section]);
  modal(existing?'修改记录 · 新增结构版本':'维护参考作品结构',`<form id="corpusRecordForm" class="stack">
    <p class="notice">保存会新增版本。引用必须来自本作品结构；未知保持待核，不凭字段完整宣称文学效果。</p>
    ${fields.map(([key,label])=>control(key,label,value[key])).join('')}
    ${section==='evidence'?'<button class="secondary" type="button" id="locateCorpusQuote">按原作定位摘录</button>':''}
    <button class="button" type="submit">保存新版本</button></form>`,'',true);
  let readPassage=null;
  function domainFields(){
    const domain=$('#corpusRecordForm [name=domain]')?.value;
    if(!$('#corpusDomainDetails')||!domain)return;
    const form=$('#corpusRecordForm'),roster=domain==='cast_roster';
    for(const key of ['characters','node_ids']){
      const input=$(`[name=${key}]`,form);
      const selected=Array.from(input.selectedOptions,o=>o.value).filter(Boolean);
      input.multiple=!roster;input.size=roster?1:5;
      const choices=key==='node_ids'&&roster?names(document.events.filter(e=>e.granularity==='detail')):refOptions[key];
      input.innerHTML=roster?optionList({'':'请选择一项',...choices},selected[0]||''):optionList(choices,selected,true);
    }
    const citedEvent=$('[name=node_ids]',form),detail=value.details||{};
    $('#corpusDomainDetails').innerHTML=Object.entries(catalog.domain_details[domain]).map(([key,label])=>{
      const choices=key==='claim_status'?catalog.narration_claims:roster?catalog.cast_roster_options[key]:null;
      if(choices)return field(label,`<select name="detail_${key}">${optionList(choices,detail[key]||'unknown')}</select>`);
      if(roster&&['appearance_evidence','standing_evidence'].includes(key)){
        const choices=key==='standing_evidence'?refOptions.evidence_ids:{};
        return field(label,`<select name="detail_${key}">${optionList({'':'待核实',...choices},detail[key]||'')}</select>`);
      }
      return field(label,`<textarea name="detail_${key}" rows="3">${esc(detail[key]||'')}</textarea>`);
    }).join('');
    readPassage=domain==='narration'&&catalog.passage_sequences
      ?passageEditor($('#corpusDomainDetails'),catalog,document,detail.passage_sequence):null;
    citedEvent.onchange=null;
    if(roster){
      const appearance=$('[name=detail_appearance_evidence]',form);
      const lookup=(selected='')=>{
        const ids=document.events.find(e=>e.id===citedEvent.value)?.evidence_ids||[];
        const evidence=names(document.evidence.filter(e=>ids.includes(e.id)));
        appearance.innerHTML=optionList({'':'选择此事件的原作证据',...evidence},selected);
      };
      lookup(detail.appearance_evidence);
      citedEvent.onchange=()=>lookup(appearance.value);
    }
  }
  if($('#corpusDomainDetails')){domainFields();$('#corpusRecordForm [name=domain]').onchange=domainFields;}
  if(section==='evidence')$('#locateCorpusQuote').onclick=e=>busy(e.currentTarget,async()=>{
    const form=$('#corpusRecordForm'),quote=$('[name=quote]',form).value,rawStart=$('[name=start]',form).value;
    const body={book_id:book.id,quote,explanation:$('[name=explanation]',form).value};
    if(rawStart!=='')body.start=Number(rawStart);
    const located=await api.post('/kb/method-evidence',body);
    $('[name=start]',form).value=located.start;$('[name=end]',form).value=located.end;toast('原作字符位置已核对');
  });
  $('#corpusRecordForm').onsubmit=e=>{
    e.preventDefault();busy(e.target.querySelector('[type=submit]'),async()=>{
      const form=e.target,result={};
      for(const [key] of fields){
        if(key==='details'){
          const domain=$('[name=domain]',form).value;
          result.details=Object.fromEntries(Object.keys(catalog.domain_details[domain]).map(k=>[k,$(`[name=detail_${k}]`,form).value]));
          const sequence=readPassage?.();
          if(sequence)result.details.passage_sequence=sequence;
        }else if(multikeys.includes(key))result[key]=Array.from($(`[name=${key}]`,form).selectedOptions).map(o=>o.value);
        else{
          const input=$(`[name=${key}]`,form);let raw=input.value;
          if(['start','end','story_order'].includes(key))raw=raw===''?null:Number(raw);
          else if(['parent_id','canonical_id','thread_id'].includes(key)&&raw==='')raw=null;
          result[key]=raw;
        }
      }
      if(section==='threads'&&result.domain==='cast_roster'){
        result.characters=result.characters.filter(Boolean);result.node_ids=result.node_ids.filter(Boolean);
        const cited=[result.details.appearance_evidence,result.details.standing_evidence].filter(Boolean);
        result.evidence_ids=[...new Set([...result.evidence_ids,...cited])];
      }
      if(result.details?.passage_sequence){
        const beats=result.details.passage_sequence.beats;
        result.node_ids=[...new Set([...result.node_ids,...beats.map(b=>b.event_id)])];
        result.evidence_ids=[...new Set([...result.evidence_ids,...beats.map(b=>b.evidence_id)])];
      }
      const payload=section==='uncertainties'?String(result.text).split('\n').map(s=>s.trim()).filter(Boolean):result;
      await api.post(`/staging/${enc(book.id)}/corpus/record`,{expected_version:record.latest_version,section,row:payload});
      $('#modalBackdrop').close();toast('新结构版本已保存，原版本保留');await reload();
    });
  };
}

export function openCorpusReview({book,record,reload}){
  const chapters=record.body.units.filter(u=>u.level==='chapter');let selected=record.coverage.reviewed_units||[];
  modal('审核参考作品结构',`<form id="corpusReviewForm" class="stack">
    <p class="notice">阅读覆盖只说明原文被处理；请核对主线、人物、因果、信息与兑现是否成立。批准结构不会自动批准方法。</p>
    <fieldset class="method-section"><legend>人工阅读确认（模型已有完整阅读记录时可不选）</legend>
    ${chapters.map(u=>`<label class="check-row"><input name="reviewed" type="checkbox" value="${esc(u.id)}" ${selected.includes(u.id)?'checked':''}> ${esc(u.title)}</label>`).join('')}</fieldset>
    <label class="check-row"><input name="limitations" type="checkbox"> 我确认当前原作完整性声明、分析推断及待核实项，不把摘录当完整作品</label>
    ${field('审核依据 / 退回原因','<textarea name="note" rows="4" required></textarea>')}
    <div class="row wrap"><button type="submit" class="button">批准此结构版本</button><button type="button" class="secondary" id="returnCorpus">退回此版本</button></div></form>`,'',true);
  async function submit(decision,button){await busy(button,async()=>{
    const form=$('#corpusReviewForm'),reviewed=$$('[name=reviewed]:checked',form).map(x=>x.value);
    if(!$('[name=note]',form).value.trim())throw new Error('请先填写审核依据或退回原因');
    let version=record.version;
    if(JSON.stringify([...reviewed].sort())!==JSON.stringify([...selected].sort())){
      const saved=await api.post(`/staging/${enc(book.id)}/corpus/record`,{expected_version:record.latest_version,section:'read_confirmation',row:reviewed});
      version=saved.version;record.latest_version=version;record.version=version;selected=reviewed;
    }
    await api.post(`/staging/${enc(book.id)}/corpus/review`,{version,decision,note:$('[name=note]',form).value,accept_limitations:$('[name=limitations]',form).checked});
    $('#modalBackdrop').close();toast(decision==='approve'?'结构版本已批准；方法仍需独立提炼和审核':'结构版本已退回');await reload();
  });}
  $('#corpusReviewForm').onsubmit=e=>{e.preventDefault();submit('approve',e.target.querySelector('[type=submit]'));};
  $('#returnCorpus').onclick=e=>submit('reject',e.currentTarget);
}
