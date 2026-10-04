import {validateSourceCorrections} from './source-review.js';
export const lenses=['Situation','Read aloud','Do now','GM only','Relevant','Missing reference'];
export function validateBoard(board){
 const errors=[];if(!board?.id||!board.pin||!Array.isArray(board.cards)||!Array.isArray(board.units))return ['Missing board identity, pin, cards or units'];
 const units=new Map(board.units.map(u=>[u.id,u])),ids=new Set();if(units.size!==board.units.length)errors.push('Duplicate evidence identity');for(const url of [board.pdfUrl,board.manifestUrl,...(board.assets??[]).map(a=>a.url)])if(url&&!url.startsWith('/private/'))errors.push('Unsafe resource URL');const checkRefs=refs=>{for(const ref of refs??[])if(!units.has(ref))errors.push('Stale evidence reference')};
 for(const card of board.cards){if(ids.has(card.id))errors.push('Duplicate card');ids.add(card.id);for(const item of Object.values(card.lenses).flat()){if(!['source_supported','reviewed_inference','proposed_connective','unresolved'].includes(item.status))errors.push('Invalid authority');if(item.status==='source_supported'&&!item.refs.length)errors.push('Unsupported source claim');for(const ref of item.refs??[])if(!units.has(ref))errors.push('Stale evidence reference');} }
 for(const card of board.cards){for(const link of card.links??[]){if(!ids.has(link.target))errors.push('Missing navigation target');checkRefs(link.refs)}for(const choice of card.choices??[])checkRefs(choice.refs)}for(const entity of board.entities??[])checkRefs(entity.refs);for(const relation of board.relationships??[])checkRefs(relation.refs);
 return [...errors,...validateSourceCorrections(board)];
}
export function newPlayState(){return {notes:'',sceneNotes:{},entityNotes:{},completed:{},decisions:[],selected:{},other:{}}}
export function logDecision(state,card,choices,note,at){return {...state,decisions:[...state.decisions,{card,choices:[...choices],note,at,status:'operator_recorded'}]}}
export function recoverPreviousState(previous,board){const state=structuredClone(previous);if(!board.cards.some(c=>c.id===state.current))state.current=board.startCard??board.cards[0].id;return state}
