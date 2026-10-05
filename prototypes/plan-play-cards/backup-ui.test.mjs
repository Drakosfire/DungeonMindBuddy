import assert from 'node:assert/strict';
import {openBackup} from './backup-ui.js';
import {newPlayState} from './board-model.js';
import {makeBackup} from './backup-model.js';
const board={id:'synthetic',pin:'pin',cards:[{id:'scene'}]};
const nodes=Object.fromEntries(['inspector','restoreText','backupFile','reviewBackup','applyRestore','backupStatus','downloadBackup','copyBackup'].map(id=>['#'+id,{value:'',disabled:false,open:true,isConnected:true}]));
globalThis.document={querySelector:s=>nodes[s]};
openBackup({board,play:newPlayState(),show:()=>{},onRestored:()=>{}});
const input=nodes['#restoreText'],review=nodes['#reviewBackup'],apply=nodes['#applyRestore'],file=nodes['#backupFile'];
input.value=JSON.stringify(makeBackup(board,newPlayState()));review.onclick();assert.equal(apply.disabled,false);
let finish;
const pending=file.onchange({target:{files:[{size:20,text:()=>new Promise(resolve=>{finish=resolve})}]}});
assert.equal(apply.disabled,true,'new file immediately invalidates the previous review');assert.equal(review.disabled,true);
input.value='new typed text';input.oninput();finish('late file text');await pending;
assert.equal(input.value,'new typed text','late file result cannot overwrite newer writing');assert.equal(review.disabled,false);assert.equal(apply.disabled,true);
let finishClosed;const closed=file.onchange({target:{files:[{size:20,text:()=>new Promise(resolve=>{finishClosed=resolve})}]}});
input.isConnected=false;finishClosed('old dialog text');await closed;assert.equal(input.value,'new typed text','closed dialog rejects a late file result');
input.isConnected=true;await file.onchange({target:{files:[{size:20,text:async()=>JSON.stringify(makeBackup(board,newPlayState()))}]}});assert.equal(review.disabled,false);review.onclick();assert.equal(apply.disabled,false);

// Exercise the actual UI restore storage routing, not only state helpers.
const stored=new Map(),writes=[];globalThis.localStorage={getItem:k=>stored.get(k)??null,setItem:(k,v)=>{writes.push(k);stored.set(k,v)}};
const currentKey='dmb-private-board-v1:synthetic:new',oldKey='dmb-private-board-v1:synthetic:old';
stored.set(currentKey,JSON.stringify({...newPlayState(),notes:'Current writing survives'}));stored.set(oldKey,'old pre-restore writing');
let replaced=false;const newerBoard={...board,pin:'new',previousPins:['old']};
openBackup({board:newerBoard,play:newPlayState(),show:()=>{},onRestored:()=>{replaced=true}});
const oldPlay={...newPlayState(),notes:'Recovered old notes',sceneNotes:{orphan:'Retain orphan'},selected:{scene:['choice']},completed:{scene:true},other:{scene:'Something else'}};
input.value=JSON.stringify(makeBackup({...board,pin:'old'},oldPlay));review.onclick();apply.onclick();
assert.deepEqual(JSON.parse(stored.get(oldKey)),oldPlay);assert.equal(JSON.parse(stored.get(currentKey)).notes,'Current writing survives');assert.equal(writes.includes(currentKey),false);assert.equal(replaced,false);assert.ok(writes.some(k=>k.startsWith(oldKey+':before-restore:')));
console.log('PASS: UI previous-pin restore uses original storage key and preserves current writing');
