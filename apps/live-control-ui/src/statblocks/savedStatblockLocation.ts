export interface SavedStatblockTarget {worldId:string;draftId:string;revisionId:string;sourceReviewId?:string}

/** Explicit navigation identity only. The existing server reader owns admission. */
export function savedStatblockHref(target:SavedStatblockTarget):string {
 return '/statblock?'+new URLSearchParams({world:target.worldId,draft:target.draftId,revision:target.revisionId,...(target.sourceReviewId?{sourceReview:target.sourceReviewId}:{})});
}
export function readSavedStatblockTarget(snapshot:string):SavedStatblockTarget|null {
 const params=new URL(snapshot,'http://localhost').searchParams;
 const values=['world','draft','revision'].map(key=>params.getAll(key));
 if(values.some(items=>items.length!==1||!items[0]!.trim()))return null;
 const source = params.getAll('sourceReview');
 if(source.length>1||(source.length===1&&!source[0]?.trim()))return null;
 return {worldId:values[0]![0]!,draftId:values[1]![0]!,revisionId:values[2]![0]!,
  ...(source[0]?{sourceReviewId:source[0]}:{})};
}

export function buildSavedStatblockHref(target: SavedStatblockTarget): string {
 return "/build?" + new URLSearchParams({world: target.worldId, draft: target.draftId, revision: target.revisionId, ...(target.sourceReviewId ? {sourceReview: target.sourceReviewId} : {})});
}
