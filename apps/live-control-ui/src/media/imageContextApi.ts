import { authenticatedApiFetch, getNativeGraphAccessGeneration } from '../api/liveApi';
import { MEDIA_ASSET_ID } from './mediaReferences';
export type ImageEditMode='image_to_image'|'new';
export type ImageContext={asset_id:string;content_sha256:string};
export type ImageCandidate={asset_id:string;parent_asset_id:string;state:string;model:string};
async function read(path:string, generation:number, init:RequestInit) {
 const {response,requestEpoch}=await authenticatedApiFetch(`/api/live/media/images/${path}`,init);
 const body=await response.json();
 if(requestEpoch!==generation||generation!==getNativeGraphAccessGeneration())throw new Error('Access changed. Reopen the image edit menu.');
 if(!response.ok)throw new Error(typeof body.detail==='string'?body.detail:body.detail?.message??'The image request could not be confirmed. Check your library before trying again.');
 return body;
}
export async function imageEditContext(assetId:string,generation:number,signal:AbortSignal):Promise<ImageContext> {
 if(!MEDIA_ASSET_ID.test(assetId))throw new Error('Image unavailable.');
 const body=await read(`${assetId}/metadata`,generation,{signal,cache:'no-store'});
 if(body.asset_id!==assetId||!['staged','ready'].includes(body.state)||typeof body.content_sha256!=='string'||!/^[a-f0-9]{64}$/.test(body.content_sha256))throw new Error('The image is not ready for editing.');
 return {asset_id:assetId,content_sha256:body.content_sha256};
}
export async function regenerateImage(context:ImageContext,mode:ImageEditMode,instructions:string,generation:number,signal:AbortSignal):Promise<ImageCandidate> {
 const body=await read(`${context.asset_id}/regenerate`,generation,{method:'POST',signal,body:JSON.stringify({mode,instructions,expected_content_sha256:context.content_sha256})});
 if(!MEDIA_ASSET_ID.test(body.asset_id)||body.asset_id===context.asset_id||body.parent_asset_id!==context.asset_id||body.state!=='staged'||typeof body.model!=='string')throw new Error('The generated candidate could not be verified. Check your library.');
 return body;
}
