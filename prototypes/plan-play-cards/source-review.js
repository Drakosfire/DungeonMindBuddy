export function validateSourceCorrections(board){const errors=[];if(board.sourceCorrections!==undefined&&(!board.sourceCorrections||typeof board.sourceCorrections!=='object'||Array.isArray(board.sourceCorrections)))return ['Invalid reviewed source corrections'];const units=new Map(board.units.map(u=>[u.id,u]));for(const [id,c] of Object.entries(board.sourceCorrections??{})){const u=units.get(id);if(!u||!c||typeof c!=='object'||Array.isArray(c)||c.originalText!==u.text||typeof c.text!=='string'||!c.text.trim()||c.text===u.text||typeof c.reviewer!=='string'||!c.reviewer.trim()||!/^([a-f0-9]{64})$/.test(c.packageHash??'')||typeof c.packageId!=='string'||!c.packageId||typeof c.packageRevision!=='string'||!c.packageRevision||c.sourcePdfHash!==board.pdfHash)errors.push('Invalid reviewed source correction')}return errors}
export function correctedItem(item,board){if(item.status!=='source_supported'||item.refs?.length!==1)return item;const c=board.sourceCorrections?.[item.refs[0]];if(!c||item.text!==c.originalText)return item;return {...item,text:c.text,status:'reviewed_inference',sourceReview:c}}

// Offsets are Unicode code points, matching the reviewed source package.
export function validateSourceAnnotations(board){
 const errors=[],units=new Map(board.units.map(u=>[u.id,u])),cards=new Set(board.cards?.map(c=>c.id)??[]);
 if(board.sourceAnnotations===undefined)return errors;
 if(!Array.isArray(board.sourceAnnotations))return ['Invalid source annotations'];
 const used=new Map();
 for(const a of board.sourceAnnotations){
  const u=units.get(a?.unitId),points=Array.from(u?.text??'');
  if(!u||!Number.isInteger(a.start)||!Number.isInteger(a.end)||a.start<0||a.end<=a.start||a.end>points.length||points.slice(a.start,a.end).join('')!==a.expectedText||!['excerpt','list_item','conditional','warning'].includes(a.kind)||!cards.has(a.targetCard)||a.audience!=='GM'||!/^([a-f0-9]{64})$/.test(a.packageHash??'')){errors.push('Invalid source annotation basis or range');continue}
  const key=a.unitId+'|'+a.targetCard+'|'+a.kind;const prior=used.get(key)??[];
  if(prior.some(b=>a.start<b.end&&b.start<a.end))errors.push('Overlapping source annotation');
  prior.push(a);used.set(key,prior);
 }
 for(const card of board.cards??[])for(const [lens,items] of Object.entries(card.lenses??{}))for(const item of items){
  if(!item.sourceExcerpt)continue;const x=item.sourceExcerpt;
  if(lens!=='GM only'||item.status!=='reviewed_inference'||item.refs?.length!==1||!board.sourceAnnotations.some(a=>a.kind==='excerpt'&&a.targetCard===card.id&&a.unitId===item.refs[0]&&a.start===x.start&&a.end===x.end&&a.expectedText===item.text))errors.push('Unreviewed source excerpt');
 }
 for(const w of board.sourceWarnings??[])if(!units.has(w?.unitId)||!cards.has(w.targetCard)||typeof w.text!=='string'||!w.text.trim()||!/^([a-f0-9]{64})$/.test(w.packageHash??''))errors.push('Invalid source warning');
 return errors;
}

const sourceEscape=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export function renderSourceFormatting(item,board,cardId){
 if(item.refs?.length!==1)return null;
 const unit=board.units.find(u=>u.id===item.refs[0]);if(!unit)return null;
 const marks=(board.sourceAnnotations??[]).filter(a=>a.unitId===unit.id&&a.kind==='conditional'&&a.targetCard===cardId);
 if(item.text!==unit.text||!marks.length)return null;
 let position=0,html='';const points=Array.from(unit.text);
 for(const mark of [...marks].sort((a,b)=>a.start-b.start)){html+=sourceEscape(points.slice(position,mark.start).join(''))+'<strong>'+sourceEscape(points.slice(mark.start,mark.end).join(''))+'</strong>';position=mark.end}
 return '<p>'+html+sourceEscape(points.slice(position).join(''))+'</p>';
}
export function isSourceListItem(item,board,cardId){return item.refs?.length===1&&(board.sourceAnnotations??[]).some(a=>a.unitId===item.refs[0]&&a.kind==='list_item'&&a.targetCard===cardId&&item.text===a.expectedText)}

export const derivativeRendererFiles=['boards.html','boards.js','boards.css','style.css','themes.css','theme-model.js','theme-ui.js','board-model.js','source-review.js','presentation-model.js','composer-ui.js','backup-model.js','backup-ui.js'];
// The reader resolves scoped roots; this verifier never writes or starts a runtime.
export async function verifyDerivativeReceipt(receipt,read,hash){
 const fail=()=>{throw Error('Invalid Sheep derivative receipt or file basis')},digest=/^[a-f0-9]{64}$/;
 if(receipt?.schema!=='sheep_source_fidelity_derivative_receipt_v1'||receipt.acceptanceStatus!=='candidate_not_accepted'||!/^([a-f0-9]{40})$/.test(receipt.rendererExactGitRevision??''))fail();
 const verify=async(scope,name,expected)=>{if(!digest.test(expected??''))fail();const bytes=await read(scope,name);if(await hash(bytes)!==expected)fail();return bytes};
 const parentBytes=await verify('parent','receipt.json',receipt.parent?.receiptSha256);const parent=JSON.parse(new TextDecoder().decode(parentBytes));
 const required=['source/board.json','source/reference-manifest.json','source/source.pdf','play.json',...derivativeRendererFiles.map(n=>'renderer/'+n)];
 for(const n of required)if(!parent.files?.[n])fail();
 for(const [name,sha] of Object.entries(parent.files)){if(name.startsWith('/')||name.split('/').includes('..'))fail();await verify('parent',name,sha)}
 const parentBoard=JSON.parse(new TextDecoder().decode(await read('parent','source/board.json')));
 for(const asset of parentBoard.assets??[]){const name='source/'+asset.url.split('/').at(-1);if(parent.files[name]!==asset.hash)fail()}
 const files=receipt.outputSha256ByFilename;if(!files||Object.keys(files).sort().join('|')!=='board.json|reference-manifest.json')fail();
 const board=JSON.parse(new TextDecoder().decode(await verify('derivative','board.json',files['board.json'])));
 const manifest=JSON.parse(new TextDecoder().decode(await verify('derivative','reference-manifest.json',files['reference-manifest.json'])));
 if(JSON.stringify(board.units)!==JSON.stringify(parentBoard.units)||JSON.stringify(manifest.units)!==JSON.stringify(parentBoard.units)||board.pdfHash!==parentBoard.pdfHash||JSON.stringify(board.assets)!==JSON.stringify(parentBoard.assets)||board.pin!==receipt.newDatasetPin)fail();
 if(validateSourceCorrections(board).length||validateSourceAnnotations(board).length)fail();
 const packageBytes=await verify('package','correction.json',receipt.reviewedCorrectionPackageSha256);await verify('evidence','evidence.json',receipt.independentEvidenceSha256);
 const pack=JSON.parse(new TextDecoder().decode(packageBytes));
 if(pack.sourceBasis?.receiptSha256!==receipt.parent.receiptSha256||pack.sourceBasis?.pdfSha256!==board.pdfHash||pack.independentEvidence?.sha256!==receipt.independentEvidenceSha256)fail();
 for(const a of board.sourceAnnotations??[])if(a.packageHash!==receipt.reviewedCorrectionPackageSha256||!pack.findings.some(f=>(f.proposed.ranges??[]).some(r=>r.unitId===a.unitId&&r.start===a.start&&r.end===a.end&&r.expectedText===a.expectedText)))fail();
 for(const [id,c] of Object.entries(board.sourceCorrections??{}))if(c.packageHash!==receipt.reviewedCorrectionPackageSha256||!pack.findings.some(f=>f.units?.[0]?.id===id&&f.units[0].originalText===c.originalText&&(f.proposed.replacementText??f.proposed.sourceFaithfulReplacement)===c.text))fail();
 const expected=expectedSheepTransformation(parentBoard,pack,receipt.reviewedCorrectionPackageSha256);
 for(const key of ['cards','sourceAnnotations','sourceCorrections','sourceWarnings'])if(canonical(board[key])!==canonical(expected[key]))fail();
 if(manifest.datasetPin!==board.pin||canonical(manifest.cards)!==canonical(board.cards)||manifest.sourceFidelityDerivative?.packageHash!==receipt.reviewedCorrectionPackageSha256||manifest.sourceFidelityDerivative?.parentDatasetPin!==pack.sourceBasis.datasetPin||manifest.sourceFidelityDerivative?.independentEvidenceHash!==receipt.independentEvidenceSha256)fail();
 const renderer=receipt.rendererSha256ByFilename;if(!renderer||Object.keys(renderer).sort().join('|')!==[...derivativeRendererFiles].sort().join('|'))fail();
 for(const name of derivativeRendererFiles)await verify('renderer',name,renderer[name]);
 const aggregate=JSON.stringify(Object.fromEntries(Object.entries(renderer).sort(([a],[b])=>a.localeCompare(b))));
 if(await hash(new TextEncoder().encode(aggregate))!==receipt.rendererAggregateSha256)fail();
 return {status:'candidate_not_accepted',board,manifest};
}

const canonical=value=>JSON.stringify(value,(_,v)=>v&&typeof v==='object'&&!Array.isArray(v)?Object.fromEntries(Object.entries(v).sort(([a],[b])=>a.localeCompare(b))):v);
// Reconstruct the complete approved transformation, rather than trusting entries supplied by a derivative.
export function expectedSheepTransformation(parent,pack,packageHash){
 const board=structuredClone(parent),cards=new Map(board.cards.map(c=>[c.id,c]));
 board.sourceAnnotations=[];board.sourceCorrections={};board.sourceWarnings=[];
 const expectedIds=['dagger-assignment','noke-ability-cells','biography-exterior','seven-bullets','conditional-leadins','cover-association','save-label-source-typo','guz-charisma-modifier'];
 if(canonical(pack.findings.map(f=>f.id))!==canonical(expectedIds))throw Error('Incomplete reviewed Sheep package');
 for(const f of pack.findings){const p=f.proposed;
  if(f.id==='dagger-assignment'){
   const source=cards.get(p.fromCard),target=cards.get(p.toCard),items=source.lenses['GM only'].filter(i=>i.refs.includes(p.moveUnit));
   if(items.length!==1)throw Error('Invalid dagger source basis');
   for(const [lens,list] of Object.entries(source.lenses)){for(const i of list)if(i.refs.includes(p.moveUnit)&&i.refs.length>1)i.refs=i.refs.filter(r=>r!==p.moveUnit);source.lenses[lens]=list.filter(i=>!(i.refs.length===1&&i.refs[0]===p.moveUnit))}
   target.lenses['GM only'].push(...items);
  }
  if(['noke-ability-cells','save-label-source-typo'].includes(f.id)){
   const u=f.units[0];board.sourceCorrections[u.id]={originalText:u.originalText,text:p.replacementText??p.sourceFaithfulReplacement,reviewer:'PRIME independent navigation_shell_review',packageHash,packageId:'sheep-source-fidelity-v2',packageRevision:packageHash,sourcePdfHash:board.pdfHash};
  }
  if(f.id==='biography-exterior'){
   const ref=f.units[0].id,source=cards.get('sheep:card:5'),old=source.lenses['GM only'].find(i=>i.refs.length===1&&i.refs[0]===ref);
   if(!old)throw Error('Invalid excerpt source basis');source.lenses['GM only']=source.lenses['GM only'].filter(i=>i!==old);
   for(const range of p.ranges){board.sourceAnnotations.push({...range,kind:'excerpt',packageHash,audience:'GM'});cards.get(range.targetCard).lenses['GM only'].push({...old,text:range.expectedText,status:'reviewed_inference',sourceExcerpt:{start:range.start,end:range.end},audience:'GM reviewed excerpt'})}
  }
  if(['seven-bullets','conditional-leadins'].includes(f.id))for(const range of p.ranges)board.sourceAnnotations.push({...range,kind:f.id==='seven-bullets'?'list_item':'conditional',targetCard:f.cards[0].id,packageHash,audience:'GM'});
  if(f.id==='cover-association')cards.get(p.targetCard).assetIds=['cover-art'];
  if(f.id==='guz-charisma-modifier')board.sourceWarnings.push({unitId:f.units[0].id,targetCard:f.cards[0].id,text:p.annotation,packageHash});
 }
 return board;
}
