import assert from 'node:assert/strict';import {validateSourceCorrections,correctedItem} from './source-review.js';
const correction={originalText:'Synthetic OCR typo',text:'Synthetic reviewed text',reviewer:'Source reviewer',packageHash:'a'.repeat(64),packageId:'synthetic',packageRevision:'revision',sourcePdfHash:'pdf'};
const board={pdfHash:'pdf',units:[{id:'unit',text:correction.originalText}],sourceCorrections:{unit:correction}};
assert.deepEqual(validateSourceCorrections(board),[]);const original={text:correction.originalText,refs:['unit'],status:'source_supported'};const revised=correctedItem(original,board);assert.equal(revised.text,correction.text);assert.equal(revised.status,'reviewed_inference');assert.equal(original.text,correction.originalText);assert.equal(board.units[0].text,correction.originalText);assert.equal(revised.sourceReview.packageHash,correction.packageHash);
for(const item of [{...original,status:'proposed_connective'},{...original,text:'Authored adaptation'},{...original,refs:['unit','other']}])assert.equal(correctedItem(item,board),item);
for(const patch of [{originalText:'wrong basis'},{sourcePdfHash:'wrong source'},{packageHash:'unknown'},{reviewer:''}])assert.equal(validateSourceCorrections({...board,sourceCorrections:{unit:{...correction,...patch}}}).length,1);

for(const sourceCorrections of [null,[],false,{unit:null},{unit:4}])assert.equal(validateSourceCorrections({...board,sourceCorrections}).length,1);

const {validateSourceAnnotations}=await import('./source-review.js');
const annotation={unitId:'unit',start:0,end:9,expectedText:'Synthetic',kind:'excerpt',targetCard:'card',audience:'GM',packageHash:'b'.repeat(64)};
const annotated={...board,cards:[{id:'card'}],sourceAnnotations:[annotation]};
assert.deepEqual(validateSourceAnnotations(annotated),[]);
for(const patch of [{start:-1},{end:999},{expectedText:'changed'},{audience:'player'},{kind:'html'},{targetCard:'stale'},{packageHash:'unreviewed'}])assert.ok(validateSourceAnnotations({...annotated,sourceAnnotations:[{...annotation,...patch}]}).length);
assert.ok(validateSourceAnnotations({...annotated,sourceAnnotations:[annotation,annotation]}).length);
assert.deepEqual(validateSourceAnnotations({...annotated,units:[{id:'unit',text:'😀abc'}],sourceAnnotations:[{...annotation,start:1,end:4,expectedText:'abc'}]}),[]);

const {renderSourceFormatting,isSourceListItem}=await import('./source-review.js');
const formatted={...annotated,sourceAnnotations:[{...annotation,kind:'conditional'}]};
assert.equal(renderSourceFormatting(original,formatted,'card'),'<p><strong>Synthetic</strong> OCR typo</p>');
assert.equal(renderSourceFormatting({...original,text:'authored'},formatted,'card'),null);
assert.equal(isSourceListItem(original,{...annotated,sourceAnnotations:[{...annotation,kind:'list_item',expectedText:original.text}]},'card'),true);

const {verifyDerivativeReceipt,derivativeRendererFiles}=await import('./source-review.js');
const {createHash}=await import('node:crypto');const hash=bytes=>createHash('sha256').update(bytes).digest('hex');const encode=x=>new TextEncoder().encode(JSON.stringify(x));
const fileMap=new Map();const put=(scope,name,bytes)=>{fileMap.set(scope+':'+name,bytes);return hash(bytes)};
const parentBoard={id:'synthetic',pin:'old',pdfHash:'pdf',units:[{id:'u',text:'original'}],cards:[{id:'c'}],assets:[]};
const parentFiles={};for(const name of ['source/board.json','source/reference-manifest.json','source/source.pdf','play.json',...derivativeRendererFiles.map(n=>'renderer/'+n)])parentFiles[name]=put('parent',name,encode(name==='source/board.json'?parentBoard:{}));
const parentReceipt=put('parent','receipt.json',encode({files:parentFiles}));
const successor={...parentBoard,pin:'new'};const outputs={'board.json':put('derivative','board.json',encode(successor)),'reference-manifest.json':put('derivative','reference-manifest.json',encode({units:parentBoard.units}))};
const renderer=Object.fromEntries(derivativeRendererFiles.map(n=>[n,put('renderer',n,encode(n))]));
const receipt={schema:'sheep_source_fidelity_derivative_receipt_v1',acceptanceStatus:'candidate_not_accepted',rendererExactGitRevision:'a'.repeat(40),parent:{receiptSha256:parentReceipt},outputSha256ByFilename:outputs,newDatasetPin:'new',reviewedCorrectionPackageSha256:put('package','correction.json',encode({sourceBasis:{receiptSha256:parentReceipt,pdfSha256:'pdf'},independentEvidence:{sha256:hash(encode({}))},findings:[]})),independentEvidenceSha256:put('evidence','evidence.json',encode({})),rendererSha256ByFilename:renderer,rendererAggregateSha256:hash(encode(Object.fromEntries(Object.entries(renderer).sort(([a],[b])=>a.localeCompare(b)))))};
const read=async(scope,name)=>{const bytes=fileMap.get(scope+':'+name);if(!bytes)throw Error('Missing scoped file');return bytes};
await assert.rejects(()=>verifyDerivativeReceipt(receipt,read,hash),'incomplete package rejects even when every supplied digest agrees');
for(const patch of [{newDatasetPin:'wrong'},{rendererExactGitRevision:'unknown'},{outputSha256ByFilename:{'board.json':outputs['board.json']}},{rendererAggregateSha256:'0'.repeat(64)},{reviewedCorrectionPackageSha256:'0'.repeat(64)},{acceptanceStatus:'accepted'}])await assert.rejects(()=>verifyDerivativeReceipt({...receipt,...patch},read,hash));
const originalFile=fileMap.get('parent:play.json');fileMap.set('parent:play.json',encode({changed:true}));await assert.rejects(()=>verifyDerivativeReceipt(receipt,read,hash));fileMap.set('parent:play.json',originalFile);
const wrongManifest=put('derivative','reference-manifest.json',encode({units:[{id:'u',text:'changed original'}]}));await assert.rejects(()=>verifyDerivativeReceipt({...receipt,outputSha256ByFilename:{...outputs,'reference-manifest.json':wrongManifest}},read,hash));
console.log('PASS: derivative parent/output/renderer/package verification rejects missing, stale and altered evidence');
assert.equal(renderSourceFormatting(original,formatted,'wrong-card'),null,'marks remain scoped to their reviewed card');
// Private fixture runs prove completeness against the independently reviewed real package without committing corpus.
if(process.env.SHEEP_FIDELITY_ROOT){
 const {readFile}=await import('node:fs/promises'),root=process.env.SHEEP_FIDELITY_ROOT;
 const json=async p=>JSON.parse(await readFile(p,'utf8'));
 const actualReceipt=await json(root+'/.private/sheep-successor-v1/receipt.json');
 const actualBoard=await json(root+'/.private/sheep-successor-v1/board.json'),actualManifest=await json(root+'/.private/sheep-successor-v1/reference-manifest.json');
 const actualParent=await json(actualReceipt.parent.root+'/source/board.json');
 const packageData=await json(root+'/.private/sheep-correction-package-v2.json');
 const {expectedSheepTransformation}=await import('./source-review.js');
 const rebuilt=expectedSheepTransformation(actualParent,packageData,actualReceipt.reviewedCorrectionPackageSha256);
 for(const key of ['cards','sourceAnnotations','sourceCorrections','sourceWarnings'])assert.deepEqual(actualBoard[key],rebuilt[key]);
 async function trial(mutate){
  const b=structuredClone(actualBoard),m=structuredClone(actualManifest),r=structuredClone(actualReceipt);mutate(b,m,r);
  const output={'board.json':encode(b),'reference-manifest.json':encode(m)};r.outputSha256ByFilename=Object.fromEntries(Object.entries(output).map(([n,v])=>[n,hash(v)]));
  r.rendererSha256ByFilename=Object.fromEntries(await Promise.all(derivativeRendererFiles.map(async n=>[n,hash(await readFile(root+'/'+n))])));
  r.rendererAggregateSha256=hash(encode(Object.fromEntries(Object.entries(r.rendererSha256ByFilename).sort(([a],[b])=>a.localeCompare(b)))));
  const reader=(scope,name)=>scope==='derivative'?output[name]:readFile(scope==='parent'?r.parent.root+'/'+name:scope==='renderer'?root+'/'+name:scope==='package'?root+'/.private/sheep-correction-package-v2.json':'/tmp/prime-sheep-source-review/evidence.json');
  return verifyDerivativeReceipt(r,reader,hash);
 }
 assert.equal((await trial(()=>{})).status,'candidate_not_accepted');
 const mutations=[
 b=>{const index=b.sourceAnnotations.findIndex(a=>a.kind==='conditional');b.sourceAnnotations.splice(index,1)},
 b=>{delete b.sourceCorrections[Object.keys(b.sourceCorrections)[0]]},
 b=>{b.sourceAnnotations.find(a=>a.kind==='conditional').targetCard='sheep:card:1'},
 b=>{b.cards=structuredClone(actualParent.cards)},
 b=>{b.sourceWarnings[0].text='Unreviewed replacement'},
 (_,m)=>{m.datasetPin='wrong';m.cards=structuredClone(actualParent.cards)},
 b=>{const card=b.cards.find(c=>c.id==='sheep:card:2');card.lenses['GM only'].reverse()},
 b=>{b.sourceAnnotations[0].audience='player'},
 b=>{b.sourceAnnotations.find(a=>a.kind==='conditional').kind='list_item'}
 ];
 for(const mutate of mutations)await assert.rejects(()=>trial(mutate));
 console.log('PASS: actual reviewed transformation rejects nine independently rehashed invalid derivatives');
}

if(process.env.CONKS_FIDELITY_ROOT){
 const {readFile}=await import('node:fs/promises'),root=process.env.CONKS_FIDELITY_ROOT;
 const json=async p=>JSON.parse(await readFile(p,'utf8'));
 const {verifyConksDerivativeReceipt,renderConksStatblock}=await import('./source-review.js');
 const actual=await json(root+'/.private/conks-successor-v1/receipt.json'),actualBoard=await json(root+'/.private/conks-successor-v1/board.json'),actualManifest=await json(root+'/.private/conks-successor-v1/reference-manifest.json');
 async function trial(mutate){
  const b=structuredClone(actualBoard),m=structuredClone(actualManifest),r=structuredClone(actual);mutate(b,m,r);
  const output={'board.json':encode(b),'reference-manifest.json':encode(m)};r.outputSha256ByFilename=Object.fromEntries(Object.entries(output).map(([n,v])=>[n,hash(v)]));
  r.rendererSha256ByFilename=Object.fromEntries(await Promise.all(derivativeRendererFiles.map(async n=>[n,hash(await readFile(root+'/'+n))])));
  r.rendererAggregateSha256=hash(encode(Object.fromEntries(Object.entries(r.rendererSha256ByFilename).sort(([a],[b])=>a.localeCompare(b)))));
  const reader=(scope,name)=>scope==='derivative'?output[name]:readFile(scope==='parent'?r.parent.root+'/'+name:scope==='renderer'?root+'/'+name:scope==='package'?root+'/.private/conks-correction-package-v2.json':scope==='evidence'?'/tmp/prime-conks-source-review/evidence.json':'/tmp/prime-conks-source-review/v2-span-review.json');
  return verifyConksDerivativeReceipt(r,reader,hash);
 }
 assert.equal((await trial(()=>{})).status,'candidate_not_accepted');
 for(const mutate of [
  b=>b.sourceAnnotations.pop(),b=>b.sourceAnnotations.reverse(),b=>{b.sourceAnnotations[0].targetCard='conks:card:1'},
  b=>{b.sourceAnnotations[0].audience='player'},b=>{b.sourceAnnotations.at(-1).role='html'},
  b=>{b.sourceSemantics.boldMonsterNames='Force combat'},b=>{b.cards.find(c=>c.id==='conks:card:18').lenses['GM only'].reverse()},
  b=>{b.units[0].text='changed'},(_,m)=>{m.datasetPin='wrong'},(_,m)=>{m.audit.knownGaps[2]='blindsight60'},
  b=>{b.sourceAnnotations.find(a=>a.role==='ability_value').column=5},(_,m,r)=>{r.independentPackageReviewSha256='0'.repeat(64)}
 ])await assert.rejects(()=>trial(mutate));
 const card=actualBoard.cards.find(c=>c.id==='conks:card:1');
 const abilities=card.lenses['GM only'].find(i=>i.refs.includes(actualBoard.sourceAnnotations.find(a=>a.role==='ability_label').unitId));
 const table=renderConksStatblock(abilities,actualBoard,card.id);assert.equal((table.match(/<th scope=/g)??[]).length,6);assert.equal((table.match(/<td>/g)??[]).length,6);
 const senses=card.lenses['GM only'].find(i=>i.text.includes('Senses blindness'));
 assert.match(renderConksStatblock(senses,actualBoard,card.id),/blindsight 600 ft/);assert.match(senses.text,/blindness 600 ft/,'original OCR stays intact');
 assert.equal(renderConksStatblock(senses,actualBoard,'conks:card:2'),null);
 assert.equal(renderConksStatblock({...senses,text:'authored adaptation'},actualBoard,card.id),null);
 const wagon=actualBoard.cards.find(c=>c.id==='conks:card:18');assert.equal(wagon.lenses['Read aloud'].length,0);assert.ok(wagon.lenses['GM only'].some(i=>i.audience==='GM biography'));
 console.log('PASS: real Conks complete derivative rejects twelve rehashed mutations; six ability columns, original-offset corrected senses and GM-only split verified');
}
