import assert from 'node:assert/strict';
import {validateBoard,newPlayState,logDecision,recoverPreviousState} from './board-model.js';
const board={id:'synthetic',pin:'sha256:test',units:[{id:'u1'}],cards:[{id:'c1',lenses:{Situation:[{text:'A test premise',status:'source_supported',refs:['u1']}]},links:[]}]};
assert.deepEqual(validateBoard(board),[]);assert.match(validateBoard({...board,cards:[{...board.cards[0],lenses:{Situation:[{status:'source_supported',refs:['missing']}]}}]}).join(),/Stale/);
assert.match(validateBoard({...board,cards:[{...board.cards[0],links:[{target:'lost'}]}]}).join(),/Missing navigation/);
assert.match(validateBoard({...board,pdfUrl:'javascript:evil'}).join(),/Unsafe/);assert.match(validateBoard({...board,entities:[{refs:['missing']}]}).join(),/Stale/);
const state=newPlayState(),result=logDecision(state,'c1',['a','b'],'Unexpected approach','time');assert.equal(state.decisions.length,0);assert.deepEqual(result.decisions[0].choices,['a','b']);assert.equal(result.decisions[0].status,'operator_recorded');assert.equal(newPlayState().notes,'');
console.log('PASS: source readback, authority, link validation and prep/play separation');

const previous={...newPlayState(),current:"removed",notes:"keep writing",edits:{"removed:Situation":"old preparation"},sceneNotes:{removed:"context"},decisions:[{card:"removed",note:"played"}]};const recovered=recoverPreviousState(previous,board);assert.equal(recovered.current,"c1");assert.equal(recovered.notes,"keep writing");assert.deepEqual(recovered.edits,previous.edits);assert.deepEqual(recovered.decisions,previous.decisions);recovered.sceneNotes.removed="new";assert.equal(previous.sceneNotes.removed,"context");console.log("PASS: explicit revision recovery retains orphaned writing and isolates old snapshot");
