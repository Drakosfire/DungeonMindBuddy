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
assert.equal(renderSourceFormatting(original,formatted),'<p><strong>Synthetic</strong> OCR typo</p>');
assert.equal(renderSourceFormatting({...original,text:'authored'},formatted),null);
assert.equal(isSourceListItem(original,{...annotated,sourceAnnotations:[{...annotation,kind:'list_item',expectedText:original.text}]}),true);

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
assert.equal((await verifyDerivativeReceipt(receipt,read,hash)).status,'candidate_not_accepted');
for(const patch of [{newDatasetPin:'wrong'},{rendererExactGitRevision:'unknown'},{outputSha256ByFilename:{'board.json':outputs['board.json']}},{rendererAggregateSha256:'0'.repeat(64)},{reviewedCorrectionPackageSha256:'0'.repeat(64)},{acceptanceStatus:'accepted'}])await assert.rejects(()=>verifyDerivativeReceipt({...receipt,...patch},read,hash));
const originalFile=fileMap.get('parent:play.json');fileMap.set('parent:play.json',encode({changed:true}));await assert.rejects(()=>verifyDerivativeReceipt(receipt,read,hash));fileMap.set('parent:play.json',originalFile);
const wrongManifest=put('derivative','reference-manifest.json',encode({units:[{id:'u',text:'changed original'}]}));await assert.rejects(()=>verifyDerivativeReceipt({...receipt,outputSha256ByFilename:{...outputs,'reference-manifest.json':wrongManifest}},read,hash));
console.log('PASS: derivative parent/output/renderer/package verification rejects missing, stale and altered evidence');
