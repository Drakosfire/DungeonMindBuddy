import {parse,validate,editCard,recordOutcome,sceneBlocks,rooms,roomBlocks,createScene,directionEffects} from './model.js?v=direction-log-1';
const fixtures=await (await fetch('./content.json')).json();
const verifiedRefs=[...new Map(fixtures.flatMap(f=>[...f.markdown.matchAll(/\[([^\]]+)\]\(dmb-node:([^)]+)\)/g)].map(m=>[m[2],{id:m[2],label:m[1]}]))).values()];
const storage='dmb-plan-play-cards-v1';
const $=s=>document.querySelector(s);
const esc=s=>s.replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let state;try{state=JSON.parse(localStorage.getItem(storage))}catch{}
state??={drafts:fixtures.map(x=>x.markdown),outcomes:[],doc:0,scene:'scene:warehouse-tail',mode:'plan',view:'cards',block:0,room:null};
state.actions??={};state.noteDrafts??={};state.otherNotes??={};state.panels??={outline:true,notes:false};
if(state.selectionVersion!==2){for(const outcome of state.outcomes){const key=outcome.document+':'+outcome.scene;state.actions[key]=[...outcome.choices]}state.selectionVersion=2;save()}
let choices=new Set();
function inline(s){return esc(s).replace(/\[([^\]]+)\]\(dmb-node:([^)]+)\)/g,'<button class="node" data-node="$2">$1</button>').replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>').replace(/`([^`]+)`/g,'<code>$1</code>');}
function md(text){
 let html='',list=false,quote=false;
 for(const line of text.replace(/<!--.*?-->/gs,'').split('\n')){
  if(!line.startsWith('- ')&&list){html+='</ul>';list=false}
  if(!line.startsWith('>')&&quote){html+='</blockquote>';quote=false}
  if(!line.trim())continue;
  if(/^#{1,4} /.test(line)){const n=line.match(/^#+/)[0].length;html+=`<h${Math.max(2,n)}>${inline(line.slice(n+1))}</h${Math.max(2,n)}>`}
  else if(line.startsWith('- ')){if(!list){html+='<ul>';list=true}html+='<li>'+inline(line.slice(2))+'</li>'}
  else if(line.startsWith('>')){if(!quote){html+='<blockquote>';quote=true}html+='<p>'+inline(line.replace(/^> ?/,''))+'</p>'}
  else if(/^---+$/.test(line)){html+='<hr>'}
  else if(line.startsWith('|')){if(!/^\|[-| :]+\|$/.test(line))html+='<div class="table-row">'+line.split('|').slice(1,-1).map(cell=>'<span>'+inline(cell.trim())+'</span>').join('')+'</div>'}
  else{html+='<p>'+inline(line)+'</p>'}
 }
 return html+(list?'</ul>':'')+(quote?'</blockquote>':'');
}
function download(name,content,type){const url=URL.createObjectURL(new Blob([content],{type}));const a=document.createElement('a');a.href=url;a.download=name;a.click();URL.revokeObjectURL(url)}
function save(){localStorage.setItem(storage,JSON.stringify(state))}
function go(id,doc=state.doc){state.doc=doc;state.scene=id;state.block=0;state.room=null;state.detail=0;choices.clear();save();render();window.scrollTo({top:0,behavior:'smooth'})}
function render(){
 const text=state.drafts[state.doc],parsed=parse(text),s=parsed.scenes.find(x=>x.id===state.scene)??parsed.scenes[0];state.scene=s.id;const draftKey=state.doc+':'+s.id;choices=new Set(state.actions[draftKey]??state.outcomes.filter(o=>o.document===state.doc&&o.scene===s.id).at(-1)?.choices??[]);
 $('#document').innerHTML=fixtures.map((x,i)=>`<option value="${i}" ${i===state.doc?'selected':''}>${x.name}</option>`).join('');
 for(const key of ['plan','play','cards','long'])$('#'+key).classList.toggle('active',state.mode===key||state.view===key);
 $('#create').hidden=state.mode!=='plan';$('#indexTitle').textContent='Outline';$('.workspace').classList.toggle('outline-hidden',!state.panels.outline);$('.workspace').classList.toggle('notes-hidden',!state.panels.notes);
 const effects=directionEffects(text,state.outcomes,state.doc);
 let beat='';
 $('#index').innerHTML=parsed.scenes.map(x=>{let heading='';if(x.beat!==beat){beat=x.beat;const e=parsed.elements.find(y=>y.id===beat);heading=`<div class="beat">${esc(text.slice(e?.bodyStart??0,e?.end??0).match(/^## (.+)/m)?.[1]??'Scenes')}</div>`}return heading+`<button data-scene="${x.id}" class="${x.id===s.id?'active':''} ${effects.find(e=>e.scene===x.id)?.effect.status==='not-planned'?'not-planned':''}">${esc(x.title)}${effects.find(e=>e.scene===x.id)?.effect.status==='not-planned'?'<small>Not planned · prior direction</small>':''}</button>`}).join('')+'<div class="beat">Reference</div><button id="overview">Intent / source context</button>'+(state.doc===0?'<div class="beat">Connected place</div><button id="house">Ironveil House →</button>':'<button id="session">← Session 29 aftermath</button>');
 $('#context').innerHTML=`<button id="toggleOutline" aria-controls="index" aria-expanded="${state.panels.outline}">Outline</button><h2 title="${esc(s.id)}">${esc(s.title)}</h2><span id="blockContext"></span><span class="badge">${state.mode==='plan'?'Prep · local copy':'Play · local session'}</span>${state.mode==='plan'?'<button id="edit">Edit this card</button>':''}<button id="toggleNotes" aria-controls="journal" aria-expanded="${state.panels.notes}">Decision log${state.outcomes.filter(o=>o.document===state.doc).length?' · '+state.outcomes.filter(o=>o.document===state.doc).length:''}</button>`;
 if(state.view==='long'){
  $('#content').innerHTML=md(text);$('#context').innerHTML+='<button id="returnCard">Return to focused card</button>';
 }else{
  const nested=parsed.elements.filter(e=>e.start>s.start&&e.start<s.end),firstChoice=nested.find(e=>e.kind==='choice');
  const body=text.slice(s.bodyStart,firstChoice?.start??s.end),blocks=sceneBlocks(body);
  let items=blocks;
  if(state.doc===1&&s.id==='scene:ironveil-house-map'){
   items=[{title:'House overview',text:body.slice(0,body.indexOf('#### Ground floor'))},...rooms(text)];
  }
  const isHouseMap=state.doc===1&&s.id==='scene:ironveil-house-map';
  const slot=Math.min(state.block??0,items.length-1);
  const selected=items[slot];
  const roomParts=state.doc===1&&s.id==='scene:ironveil-house-map'&&slot>0?roomBlocks(selected.text):null;
  const detailSlot=Math.min(state.detail??0,(roomParts?.length??1)-1);
  const focusText=roomParts?.[detailSlot].text??selected.text;
  $('#blockContext').textContent=selected.title+' · '+(slot+1)+' / '+items.length;
  let displayText=focusText.replace(/^### [^\n]+\n?/, '');
  const leadingLabel=displayText.match(/^\*\*([^*]+)\*\*\s*\n/);
  if(leadingLabel&&leadingLabel[1]===selected.title)displayText=displayText.slice(leadingLabel[0].length);
  $('#content').innerHTML=`<div class="block-tabs">${isHouseMap?`<button data-block="0">Room map</button><select id="roomSelect" aria-label="House space">${items.map((b,i)=>`<option value="${i}" ${i===slot?'selected':''}>${esc(b.title)}</option>`).join('')}</select>`:items.map((b,i)=>`<button data-block="${i}" class="${i===slot?'active':''}">${esc(b.title)}</button>`).join('')}</div>${roomParts&&roomParts.length>1?`<div class="room-tabs">${roomParts.map((b,i)=>`<button data-detail="${i}" class="${i===detailSlot?'active':''}">${esc(b.title)}</button>`).join('')}</div>`:''}<section class="focused-block">${md(displayText)}</section>`;
  if(isHouseMap&&slot===0)$('#content').insertAdjacentHTML('beforeend',`<section class="room-map"><h3>Ground floor</h3><div>${items.slice(1,6).map((b,i)=>`<button data-block="${i+1}">${esc(b.title)}</button>`).join('')}</div><h3>Upper floor</h3><div>${items.slice(6).map((b,i)=>`<button data-block="${i+6}">${esc(b.title)}</button>`).join('')}</div><p class="map-note">Source-described spaces by floor. Positions imply no physical adjacency. Residence remains unresolved.</p></section>`);
  if(state.doc===1&&s.id==='scene:ironveil-house-map'&&[2,9].includes(slot))$('#content').insertAdjacentHTML('beforeend',`<button data-scene="${slot===2?'scene:ironveil-kitchen':'scene:lysandra-alone-at-home'}">Related interaction: ${slot===2?'Kitchen Table':'Lysandra alone'} →</button>`);
  const location=body.match(/^Location:\s*(.+)$/m)?.[1];
  if(location)$('#content').insertAdjacentHTML('afterbegin',`<div class="scene-location">${inline(location)}</div>`);
  const effect=effects.find(e=>e.scene===s.id)?.effect;
  if(effect?.status==='not-planned')$('#content').insertAdjacentHTML('afterbegin','<p class="direction-flag">Not planned after a recorded player direction. Still available to run.</p>');
  if(firstChoice&&(!isHouseMap||slot===9))renderChoices(text,nested,s);
  const i=parsed.scenes.indexOf(s);
  $('#content').insertAdjacentHTML('beforeend',`<div class="next"><button id="previous" ${i===0?'disabled':''}>← Previous scene</button><button id="next" ${i===parsed.scenes.length-1?'disabled':''}>Next scene →</button></div>`);
  $('#previous').onclick=()=>go(parsed.scenes[i-1].id);$('#next').onclick=()=>go(parsed.scenes[i+1].id);
 }
 $('#outcomes').innerHTML=state.outcomes.filter(o=>o.document===state.doc).map(o=>`<div class="outcome"><span class="badge">${o.kind==='player-direction'?'PLAYER DIRECTION':'PLAY NOTE'} · LOCAL</span><strong>${esc(parsed.scenes.find(s=>s.id===o.scene)?.title??o.scene)}</strong><p>${esc(o.note)}</p><details><summary>Advanced</summary><small>${esc(o.at??'')} · ${esc(o.choices.join(', '))}</small></details>${followups(o)}</div>`).join('')+(state.mode==='play'?'<label>What happened? Include unexpected actions.<textarea id="outcomeNote" placeholder="Record what players actually did…"></textarea></label><button id="record">Record local outcome</button>':'<p>Optional details can be added in Play.</p>');
 $('#toggleOutline').onclick=()=>{state.panels.outline=!state.panels.outline;save();render()};
 $('#toggleNotes').onclick=()=>{state.panels.notes=!state.panels.notes;save();render()};
 document.querySelectorAll('[data-follow]').forEach(b=>b.onclick=()=>go(b.dataset.follow,+b.dataset.followdoc));
 document.querySelectorAll('[data-scene]').forEach(b=>b.onclick=()=>go(b.dataset.scene));
 document.querySelectorAll('[data-block]').forEach(b=>b.onclick=()=>{state.block=+b.dataset.block;state.detail=0;save();render()});
 if($('#roomSelect'))$('#roomSelect').onchange=e=>{state.block=+e.target.value;state.detail=0;save();render()};
 document.querySelectorAll('[data-detail]').forEach(b=>b.onclick=()=>{state.detail=+b.dataset.detail;save();render()});
 document.querySelectorAll('[data-option]').forEach(b=>b.onchange=()=>{b.checked?choices.add(b.dataset.option):choices.delete(b.dataset.option);state.actions[draftKey]=[...choices];save()});
 document.querySelectorAll('[data-other-note]').forEach(field=>field.oninput=()=>{const id=field.dataset.otherNote;state.otherNotes[draftKey+':'+id]=field.value;if(field.value.trim())choices.add(id);else choices.delete(id);state.actions[draftKey]=[...choices];const checkbox=document.querySelector(`[data-option="${id}"]`);if(checkbox)checkbox.checked=choices.has(id);save()});
 document.querySelectorAll('.log-direction').forEach(button=>button.onclick=()=>{
  const status=button.nextElementSibling;
  if(!choices.size){status.textContent='Check the actions the players took first.';return}
  const last=state.outcomes.filter(o=>o.document===state.doc&&o.scene===s.id).at(-1);
  if(last&&last.choices.length===choices.size&&last.choices.every(id=>choices.has(id))&&(last.otherNote??'')===([...choices].map(id=>state.otherNotes[draftKey+':'+id]?.trim()).filter(Boolean).join('; ')||state.otherNotes[draftKey]?.trim()||'')){status.textContent='These decisions are already logged.';return}
  const labels=[...choices].map(id=>{const option=parsed.elements.find(e=>e.id===id);if(!option)return 'Something else.';return text.slice(option.bodyStart,option.end).match(/- \*\*([^*]+)\*\*/)?.[1]??id});
  const extra=[...choices].map(id=>state.otherNotes[draftKey+':'+id]?.trim()).filter(Boolean).join('; ')||state.otherNotes[draftKey]?.trim()||'';
  state=recordOutcome(state,state.doc,s.id,[...choices],labels.join('; ')+(extra?' — '+extra:''));
  state.outcomes.at(-1).otherNote=extra;state.outcomes.at(-1).kind='player-direction';state.outcomes.at(-1).choiceLabels=labels;
  state.actions[draftKey]=[...choices];save();render();
 });
 document.querySelectorAll('[data-node]').forEach(b=>b.onclick=()=>showReference(b.dataset.node,b.textContent));
 if($('#outcomeNote')){$('#outcomeNote').value=state.noteDrafts[draftKey]??'';$('#outcomeNote').oninput=()=>{state.noteDrafts[draftKey]=$('#outcomeNote').value;save()}};
 if($('#record'))$('#record').onclick=()=>{try{state=recordOutcome(state,state.doc,s.id,[...choices],$('#outcomeNote').value);state.actions[draftKey]=[...choices];delete state.noteDrafts[draftKey];save();render()}catch(e){$('#outcomeNote').setCustomValidity(e.message);$('#outcomeNote').reportValidity()}};
 if($('#edit'))$('#edit').onclick=()=>openEdit(s,text);
 $('#exportPrep').onclick=()=>download(fixtures[state.doc].name+' - local prep.md',state.drafts[state.doc],'text/markdown');
 $('#exportOutcomes').onclick=()=>download('prototype-outcomes.json',JSON.stringify(state.outcomes,null,2),'application/json');
 if($('#returnCard'))$('#returnCard').onclick=()=>{state.view='cards';save();render()};
 $('#overview').onclick=()=>{state.view='long';save();render();window.scrollTo({top:0,behavior:'smooth'})};
 if($('#house'))$('#house').onclick=()=>go('scene:ironveil-arrival',1);
 if($('#session'))$('#session').onclick=()=>go('scene:town-breathes',0);
}
function followups(outcome){
 const docText=state.drafts[outcome.document],p=parse(docText),targets=new Set(),suppressed=new Set();
 for(const id of outcome.choices){const option=p.elements.find(x=>x.id===id);for(const target of (option?.activates??'').split(',').filter(Boolean))targets.add(target);for(const target of (option?.suppresses??'').split(',').filter(Boolean))suppressed.add(target)}
 const available=[...targets].map(id=>p.scenes.find(x=>x.id===id||x.beat===id)).filter(Boolean);
 return available.length?`<p>Source-linked follow-ups (optional)</p>${available.map(x=>`<button data-followdoc="${outcome.document}" data-follow="${x.id}">${esc(x.title)} →</button>`).join('')}${suppressed.size?`<p>Source relevance suppressed: ${esc([...suppressed].join(', '))}. Navigation stays open.</p>`:''}`:'';
}
function renderChoices(text,nested,s){
 for(const c of nested.filter(e=>e.kind==='choice')){
  const opts=nested.filter(e=>e.kind==='option'&&e.start>c.start&&e.start<(nested.find(x=>x.kind==='choice'&&x.start>c.start)?.start??s.end));
  const other=opts.find(o=>/something (else|unexpected)|another objective/i.test(text.slice(o.bodyStart,o.end)));
  if(!other)opts.push({id:c.id+':unexpected',bodyStart:0,end:0,unexpected:true});
  $('#content').insertAdjacentHTML('beforeend',`<details class="choice"><summary><span class="choice-callout">Choices <span class="choice-hint">Click to expand</span></span></summary><p class="choice-prompt">${esc(text.slice(c.bodyStart,c.end).match(/^### (.+)/m)?.[1]??'What do they do?')}</p>${md(text.slice(c.bodyStart,c.end).replace(/^\s*### [^\n]+\n?/,''))}${opts.map(o=>{const raw=text.slice(o.bodyStart,Math.min(o.end,s.end)),title=o.unexpected?'Something else.':raw.match(/- \*\*([^*]+)\*\*/)?.[1]??o.id,consequence=raw.replace(/^\s*- \*\*[^*]+\*\*[^\n]*(?:\n|$)/,'');return `<div class="option"><label><input style="width:auto" type="checkbox" aria-label="${esc(title)}" data-option="${o.id}" ${choices.has(o.id)?'checked':''}> ${esc(title)}</label>${/something (else|unexpected)|another objective/i.test(title)?`<label class="other-action">What did they do?<textarea data-other-note="${o.id}" placeholder="Describe the unexpected action…">${esc(state.otherNotes[state.doc+':'+s.id+':'+o.id]??state.otherNotes[state.doc+':'+s.id]??'')}</textarea></label>`:''}<details><summary>Consequences / later relevance</summary>${md(consequence)}</details></div>`}).join('')}<button type="button" class="log-direction">Log player direction</button><span class="direction-status" role="status">${state.outcomes.some(o=>o.document===state.doc&&o.scene===s.id)?'Saved in Decision log · browser only':'Saved here in your browser; export from Files'}</span></details>`);
 }
}
function showReference(id,label){
 const mentions=state.drafts.flatMap((text,doc)=>parse(text).scenes.flatMap(scene=>{
  const body=text.slice(scene.bodyStart,scene.end);
  const paragraphs=body.replace(/<!--.*?-->/gs,'').split(/\n\s*\n/).filter(p=>p.includes('(dmb-node:'+id+')')).map(p=>p.replace(/\[([^\]]+)\]\(dmb-node:[^)]+\)/g,'$1').replace(/^#{1,4} /gm,'').trim());
  const situation=sceneBlocks(body).find(b=>b.title==='Situation')?.text.replace(/^\s*\*\*Situation\*\*\s*/, '').trim();
  if(paragraphs.length&&situation&&!paragraphs.includes(situation))paragraphs.push(situation.replace(/\[([^\]]+)\]\(dmb-node:[^)]+\)/g,'$1'));
  return paragraphs.length?[{doc,scene,paragraphs}]:[];
 }));
 $('#editorTitle').textContent=label;$('#editorHelp').textContent='In your preparation · '+mentions.length+' connected scenes';
 $('#fields').innerHTML=mentions.length?mentions.map(m=>`<section class="reference-context"><button type="button" data-reference-scene="${esc(m.scene.id)}" data-reference-doc="${m.doc}">${esc(fixtures[m.doc].name)} · ${esc(m.scene.title)} →</button>${m.paragraphs.slice(0,2).map(p=>`<p>${inline(p)}</p>`).join('')}</section>`).join(''):'<p>No scene context is linked to this reference yet.</p>';
 $('#fields').insertAdjacentHTML('beforeend',`<details><summary>Advanced</summary><p>${esc(id)}</p><p>Context comes from local preparation, not a live Graph query.</p></details>`);
 document.querySelectorAll('[data-reference-scene]').forEach(b=>b.onclick=()=>{$('#editor').close();state.view='cards';go(b.dataset.referenceScene,+b.dataset.referenceDoc)});
 $('#apply').hidden=true;$('#errors').textContent='';$('#editor').showModal();
}
function openEdit(s,text){
 $('#apply').hidden=false;$('#apply').textContent='Apply preparation';$('#editorTitle').textContent='Edit · '+s.title;$('#editorHelp').textContent='Edit one scene in the local preparation copy. Existing stable markers must remain intact.';
 $('#fields').innerHTML='<label>Card preparation Markdown<textarea id="cardBody" style="min-height:350px"></textarea></label>';$('#cardBody').value=text.slice(s.bodyStart,s.end).trim();$('#fields').insertAdjacentHTML('beforeend',`<label>Verified node reference<select id="referenceSelect" aria-label="Verified node reference">${verifiedRefs.map(r=>`<option value="${r.id}">${esc(r.label)}</option>`).join('')}</select></label><button type="button" id="insertReference">Insert reference at selection</button>`);$('#insertReference').onclick=()=>{const field=$('#cardBody'),r=verifiedRefs.find(x=>x.id===$('#referenceSelect').value);const from=field.selectionStart,to=field.selectionEnd;field.setRangeText(`[${to>from?field.value.slice(from,to):r.label}](dmb-node:${r.id})`,from,to,'end');field.focus()};$('#errors').textContent='';
 $('#apply').onclick=()=>{const changed=editCard(text,s.id,$('#cardBody').value),errors=validate(changed,fixtures[state.doc].markdown,verifiedRefs.map(x=>x.id));if(errors.length){$('#errors').textContent=errors.join(' ');return}state.drafts[state.doc]=changed;save();$('#editor').close();render()};$('#editor').showModal();
}
$('#document').onchange=e=>go('',+e.target.value);
for(const mode of ['plan','play'])$('#'+mode).onclick=()=>{state.mode=mode;save();render()};
$('#cards').onclick=()=>{state.view='cards';save();render()};$('#long').onclick=()=>{state.view='long';save();render()};
$('#create').onclick=()=>{
 const fields=['Scene name','Situation','Perception / read aloud','Immediate prompt','Choices and consequences','Linked people / places / threats'];
 let step=0;const values=Array(6).fill('');
 $('#apply').hidden=false;$('#editorTitle').textContent='Create a focused scene';
 function show(){
  $('#editorHelp').textContent=`Step ${step+1} of 6 · ${step===4?'One action | consequence per line. Optional. Unexpected actions remain possible.':step===5?'Names / reference notes only. Unverified identities remain unlinked.':'Local preparation, never played canon.'}`;
  $('#fields').innerHTML=`<label>${fields[step]}<textarea id="guidedField"></textarea></label>${step>0?'<button type="button" id="backStep">← Back</button>':''}`;
  $('#guidedField').value=values[step];$('#apply').textContent=step===5?'Create local scene':'Next →';$('#errors').textContent='';
  if($('#backStep'))$('#backStep').onclick=()=>{values[step]=$('#guidedField').value;step--;show()};
  $('#apply').onclick=()=>{values[step]=$('#guidedField').value.trim();if(step<4&&!values[step]){$('#errors').textContent='This block is required.';return}if(step<5){step++;show();return}
   try{const id='scene:local-'+crypto.randomUUID(),addition=createScene(values,id);const next=state.drafts[state.doc]+addition,problems=validate(next,fixtures[state.doc].markdown,verifiedRefs.map(x=>x.id));if(problems.length)throw Error(problems.join(' '));state.drafts[state.doc]=next;state.scene=id;state.block=0;state.detail=0;save();$('#editor').close();render()}catch(e){$('#errors').textContent=e.message}
  };
 }
 show();$('#editor').showModal();
};render();
state.playPad??={text:'',open:false};
function showPlayPad(open){state.playPad.open=open;$('#playPad').hidden=!open;$('#togglePlayPad').setAttribute('aria-expanded',String(open));save();if(open)$('#playPadText').focus()}
$('#playPadText').value=state.playPad.text;
$('#playPadText').oninput=()=>{state.playPad.text=$('#playPadText').value;save();$('#playPadStatus').textContent='Saved in this browser'};
$('#togglePlayPad').onclick=()=>showPlayPad(!state.playPad.open);
$('#closePlayPad').onclick=()=>showPlayPad(false);
$('#exportPlayPad').onclick=()=>download('play-notes.md',state.playPad.text,'text/markdown');
showPlayPad(state.playPad.open);
