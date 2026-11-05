import {beforeEach,afterEach,it,expect,vi} from 'vitest';
import {webcrypto} from 'node:crypto';
import {buildRecapSupportRequest,validateRecapSupportRequest,extendRecapSupport} from './recapMergeSupportApi';
import {projection,context} from '../ingestion/nativeMergeFixtures';
import * as transport from './liveApi';
beforeEach(()=>vi.stubGlobal('crypto',webcrypto));
afterEach(()=>{vi.restoreAllMocks();vi.unstubAllGlobals();transport.setNativeGraphAccessToken(null);});
it('registers deduplicated exact UTF8 paragraphs rather than using whole-source context',async()=>{
 const p=structuredClone(projection);p.sourceMarkdown='Préface.\r\n\r\nMara keeps the gate.\r\n';p.nodes.forEach(n=>n.evidence.forEach(w=>{w.startLine=3;w.endLine=3;w.paragraphText='Mara keeps the gate.';}));p.edges.forEach(n=>n.evidence.forEach(w=>{w.startLine=3;w.endLine=3;w.paragraphText='Mara keeps the gate.';}));
 const r=context();r.native_context.source_evidence=[];const command=await buildRecapSupportRequest(p,r);expect(command?.spans).toHaveLength(1);expect(command?.spans[0]).toMatchObject({evidence_role:'support',start_byte:new TextEncoder().encode('Préface.\r\n\r\n').length,end_byte:new TextEncoder().encode('Préface.\r\n\r\nMara keeps the gate.').length});
 const expected=Buffer.from(await webcrypto.subtle.digest('SHA-256',new TextEncoder().encode('Mara keeps the gate.'))).toString('hex');expect(command?.spans[0].expected_slice_sha256).toBe(expected);
 expect(command?.source_artifact_id).toBe('native-source');expect(command?.original_admission_id).toBe('native-admission');
 const again=await buildRecapSupportRequest(p,r);expect(again?.extension_id).toBe(command?.extension_id);
});
it('does not create another extension when verified support already covers the witnesses',async()=>{expect(await buildRecapSupportRequest(projection,context())).toBeNull();});
it('refuses an unwitnessed claim instead of converting context into support',async()=>{const p=structuredClone(projection);p.nodes[0].evidence=[];await expect(buildRecapSupportRequest(p,context())).rejects.toThrow('no verified source witness');});
it('sends the exact request authenticated and never automatically retries a write',async()=>{
 transport.setNativeGraphAccessToken('synthetic-token');const r=context();r.native_context.source_evidence=[];const command=(await buildRecapSupportRequest(projection,r))!;
 const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue(Response.json({detail:{message:'temporary refusal'}},{status:401}));await expect(extendRecapSupport(projection,command)).rejects.toMatchObject({status:401});expect(fetch).toHaveBeenCalledOnce();expect(fetch.mock.calls[0][0]).toBe('/api/live/source-statements/extend-evidence');expect(new Headers(fetch.mock.calls[0][1]?.headers).get('Authorization')).toBe('Bearer synthetic-token');expect(JSON.parse(String(fetch.mock.calls[0][1]?.body))).toEqual(command);
});
it('requires the matching original admission and support bindings in the receipt',async()=>{
 const r=context();r.native_context.source_evidence=[];const command=(await buildRecapSupportRequest(projection,r))!;
 vi.spyOn(transport,'authenticatedApiFetch').mockResolvedValue({response:Response.json({status:'committed',receipt:{space_id:'n',extension_id:command.extension_id,original_admission_id:'another-source',source_artifact_id:'native-source',source_revision_id:'native-rev',publication_receipt:{published_revision_id:'child'},bindings:[]}})} as never);
 await expect(extendRecapSupport(projection,command)).rejects.toThrow('unverified');
});

it.each(['\r','\u2028','\u2029','\v','\f','\u0085','\u001c'])('matches owning splitlines semantics for %j',async separator=>{
 const p=structuredClone(projection);p.sourceMarkdown='Préface'+separator+'Mara keeps the gate.\nOther text\n';for(const record of [...p.nodes,...p.edges])record.evidence.forEach(w=>{w.startLine=2;w.endLine=2;w.paragraphText='Mara keeps the gate.';});const r=context();r.native_context.source_evidence=[];const request=(await buildRecapSupportRequest(p,r))!;expect(request.spans[0].start_byte).toBe(new TextEncoder().encode('Préface'+separator).length);await expect(validateRecapSupportRequest(p,r,request)).resolves.toEqual(request);
});
it('refuses a paragraph-text mismatch before support registration',async()=>{const p=structuredClone(projection);p.nodes[0].evidence[0].paragraphText='Different text';await expect(buildRecapSupportRequest(p,context())).rejects.toThrow('no longer matches');});
it.each(['whole-source','digest','identity','duplicate','timestamp'])('rejects corrupted retained support packet: %s',async change=>{
 const r=context();r.native_context.source_evidence=[];const request=(await buildRecapSupportRequest(projection,r))!;
 if(change==='whole-source')request.spans[0].end_byte=new TextEncoder().encode(projection.sourceMarkdown).length;
 if(change==='digest')request.spans[0].expected_slice_sha256='0'.repeat(64);
 if(change==='identity')request.extension_id='other';
 if(change==='duplicate')request.spans.push(request.spans[0]);
 if(change==='timestamp')request.created_at='not-a-time';
 await expect(validateRecapSupportRequest(projection,r,request)).rejects.toThrow();
});

it.each(['\r\n','\u2028'])('preserves internal %j bytes in a multiline paragraph',async separator=>{
 const p=structuredClone(projection);p.sourceMarkdown='Mara waits.'+separator+'Nero follows.\n';for(const record of [...p.nodes,...p.edges])record.evidence.forEach(w=>{w.startLine=1;w.endLine=2;w.paragraphText='Mara waits.'+separator+'Nero follows.';});const r=context();r.native_context.source_evidence=[];const request=(await buildRecapSupportRequest(p,r))!;await expect(validateRecapSupportRequest(p,r,request)).resolves.toEqual(request);expect(request.spans[0].end_byte).toBe(new TextEncoder().encode(p.sourceMarkdown.trimEnd()).length);
});
it('does not treat visual highlightability as native evidence authority',async()=>{
 const p=structuredClone(projection);for(const record of [...p.nodes,...p.edges])record.evidence.forEach(w=>{w.canHighlight=false;});const r=context();r.native_context.source_evidence=[];const request=await buildRecapSupportRequest(p,r);expect(request?.spans).toHaveLength(1);await expect(validateRecapSupportRequest(p,r,request)).resolves.toEqual(request);
});
