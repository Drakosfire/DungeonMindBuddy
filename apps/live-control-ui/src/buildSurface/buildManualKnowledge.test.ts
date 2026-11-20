import {expect,it} from 'vitest';
import {readKnowledgeRecovery,selectionForFrozenText,type ManualKnowledgeScope} from './buildManualKnowledge';
const scope:ManualKnowledgeScope={worldId:'world',documentId:'doc',revision:2,hash:'b'.repeat(64),runId:'run',artifactId:'source'};
const catalog:any={spans:[{sourceSpanRefId:'one',paragraphText:'Mara rings the bell.'}]};
it('joins a unique normalized quote to its frozen span without treating editor offsets as evidence',()=>{
 expect(selectionForFrozenText(scope,catalog,'Mara\n rings')).toMatchObject({sourceSpanRefId:'one',normalizedSelectedText:'Mara rings',sourceArtifactId:'source'});
});
it.each(['empty','absent','repeated','two spans'])('refuses %s selection',kind=>{
 const text=kind==='empty'?'':kind==='absent'?'Nell':'Mara';
 const c=kind==='repeated'?{spans:[{sourceSpanRefId:'one',paragraphText:'Mara watches Mara.'}]}:kind==='two spans'?{spans:[...catalog.spans,...catalog.spans]}:catalog;
 expect(()=>selectionForFrozenText(scope,c,text)).toThrow();
});
it('refuses foreign recovery and incomplete prepared data',()=>{
 expect(readKnowledgeRecovery(null,scope)).toBeNull();
 expect(()=>readKnowledgeRecovery(JSON.stringify({schema:'dmb_build_manual_knowledge_v1',scope:{...scope,worldId:'foreign'}}),scope)).toThrow();
 expect(()=>readKnowledgeRecovery(JSON.stringify({schema:'dmb_build_manual_knowledge_v1',scope,request:{worldId:'world',campaignId:'world',sourceRunId:'run',proposals:[{}]},submitted:false,prepared:{confirm_token:'token',expressibility:'EXPRESSIBLE'},receipt:null}),scope)).toThrow();
});
