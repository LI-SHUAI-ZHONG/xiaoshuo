/* Browser-only driver for the isolated HTTP editor test. */
(async()=>{
  const frame=document.querySelector('#studio');
  const doc=()=>frame.contentDocument;
  const el=selector=>doc()?.querySelector(selector);
  const wait=async(test,label)=>{
    const deadline=Date.now()+10000;
    do{
      const result=test();
      if(result)return result;
      await new Promise(resolve=>setTimeout(resolve,45));
    }while(Date.now()<deadline);
    throw Error(label+' · '+doc()?.body?.innerText.slice(-1200));
  };
  const require=(ok,label)=>{if(!ok)throw Error(label);};
  const form=()=>el('#modalBackdrop[open] #corpusRecordForm');
  const field=name=>form().querySelector('[name="'+name+'"]');
  const value=key=>form().querySelector('[data-key="'+key+'"]');
  const select=(input,choice)=>{
    input.value=choice;
    require(input.value===choice,'缺少选项 '+choice);
    input.dispatchEvent(new frame.contentWindow.Event('change',{bubbles:true}));
  };
  const card=id=>Array.from(doc().querySelectorAll('.corpus-record'))
    .find(item=>item.querySelector('small')?.textContent.trim().split(' · ')[0]===id);
  const open=async(id)=>{
    const item=await wait(()=>card(id),'寻找 '+id);
    item.querySelector('[data-corpus-edit]').click();
    await wait(form,'打开编辑器 '+id);
  };
  const save=async(version)=>{
    form().requestSubmit();
    await wait(()=>!form()&&el('#corpusVersion')?.value===String(version),'保存版本 '+version);
  };
  const tab=name=>el('[data-corpus-tab="'+name+'"]').click();
  const submit=report=>fetch('/_editor_result',{method:'POST',body:JSON.stringify(report)});
  try{
    await wait(()=>card('Q_title'),'原作证据目录');
    tab('threads');
    await open(fixture.thread);
    select(form().querySelector('[data-kind]'),'sensory_evidence');
    select(value('event_id'),fixture.event);
    require(!value('evidence_id').querySelector('[value="Q_title"]'),'原文标题遗漏手工用途时仍可证明故事');
    el('#modalBackdrop').close();
    tab('evidence');
    await open('Q_title');
    require(field('text_role').selectedOptions[0].text==='故事正文','旧版无用途引文显示不正确');
    select(field('text_role'),'heading');
    await save(3);
    await open('Q_title');
    require(field('text_role').selectedOptions[0].text==='章名与标题','引文用途没有保存');
    el('#modalBackdrop').close();
    tab('threads');
    await open(fixture.thread);
    const kind=form().querySelector('[data-kind]');
    require(kind.querySelector('[value="sensory_evidence"]').parentElement.label==='一处原句可举证','单项分组错误');
    require(kind.querySelector('[value="event_start"]').parentElement.label==='需要前后原句共同举证','前后落点分组错误');
    for(const judgment of ['qualified_claim','interpreted_motive']){
      select(kind,judgment);
      require(value('claim_status').value==='unknown'&&!value('claim_status').querySelector('[value="stated"]'),'估计被默认确认为事实');
      require(field('detail_claim_status').querySelector('[value="stated"]').disabled&&field('detail_claim_status').value!=='stated','整项观察仍认定事实');
      require(value('story_change').type==='hidden'&&value('story_change').value==='', '推测不应填写故事变化');
      select(value('claim_status'),'attributed');
    }
    select(kind,'event_start');
    require(!field('detail_claim_status').querySelector('[value="stated"]').disabled,'切回实际行动后无法选明确事实');
    require([...form().querySelectorAll('[data-key="role"]')].map(s=>s.value).join(',')==='signal,response','启动与响应角色错误');
    select(kind,'sensory_evidence');
    require(form().querySelectorAll('[data-beat]').length===1&&value('role').value==='detail','感官细节应只有一个必需角色');
    value('condition').value='在场人物能听见门环响动';
    value('boundary').value='关门以后远处的人无法听见';
    select(value('event_id'),fixture.event);
    require(!value('evidence_id').querySelector('[value="Q_title"],[value="Q_title_alias"]'),'题外标题或重复位置仍可当作现场证据');
    select(value('evidence_id'),fixture.quote);
    value('bridge').value='先听到门环相撞，才知门口有动静';
    value('reader_change').value='响声让读者留意门口';
    await save(4);
    tab('events');
    await open(fixture.event);
    for(const option of field('evidence_ids').options){
      if(['Q_title','Q_title_alias'].includes(option.value))option.selected=false;
    }
    await save(5);
    const previous=doc();
    frame.src='/#/staging/'+fixture.book+'?tab=threads';
    frame.contentWindow.location.reload();
    await wait(()=>doc()!==previous&&el('[data-corpus-tab="threads"]'),'重新加载已保存版本');
    tab('threads');
    await open(fixture.thread);
    require(form().querySelector('[data-kind]').value==='sensory_evidence','重开后方法丢失');
    require(value('reader_change').value==='响声让读者留意门口'&&value('role').value==='detail','重开后效果或角色丢失');
    require(value('event_id').value===fixture.event&&value('evidence_id').value===fixture.quote,'重开后对应证据丢失');
    el('#modalBackdrop').close();
    tab('evidence');
    card('Q_title').querySelector('[data-corpus-detail]').click();
    require(doc().body.innerText.includes('章名与标题'),'详情未显示引文用途');
    await submit({status:'reopened'});
  }catch(error){
    await submit({error:String(error.stack||error)});
  }
})();
