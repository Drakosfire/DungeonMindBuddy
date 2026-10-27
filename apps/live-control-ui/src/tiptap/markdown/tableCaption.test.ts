import {expect,it} from 'vitest';
import {isPlainTableCaption,isTableCaptionAt} from './tableCaption';

const caption={type:'heading',attrs:{level:2,playableElementId:null},content:[{type:'text',text:'Tactics'}]};
it('recognizes only the shared plain-caption and adjacent-table pair',()=>{
 expect(isPlainTableCaption(caption)).toBe(true);
 expect(isTableCaptionAt([caption,{type:'table'}],0)).toBe(true);
 expect(isTableCaptionAt([caption,{type:'paragraph'},{type:'table'}],0)).toBe(false);
 expect(isTableCaptionAt([caption],0)).toBe(false);
});
it.each([
 {...caption,attrs:{level:1}},
 {...caption,attrs:{level:2,playableElementId:'beat:owned'}},
 {...caption,content:[{type:'text',text:'Marked',marks:[{type:'bold'}]}]},
 {...caption,content:[{type:'graphNodeReference',attrs:{nodeId:'node:one'}}]},
 {...caption,content:[{type:'text',text:'   '}]},
])('does not adopt a structural, marked, reference or empty heading as table chrome',node=>{
 expect(isPlainTableCaption(node)).toBe(false);
});
