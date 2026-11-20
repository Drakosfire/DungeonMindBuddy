import {expect,it} from 'vitest';
import {readSavedStatblockTarget,savedStatblockHref} from './savedStatblockLocation';
it('round trips an exact saved target without losing opaque revision bytes',()=>{
 const target={worldId:'elderwyld',draftId:'draft-a',revisionId:'rev:one + two'};
 expect(readSavedStatblockTarget(savedStatblockHref(target))).toEqual(target);
});
it.each(['/statblock','/statblock?world=w&draft=d','/statblock?world=w&world=x&draft=d&revision=r','/statblock?world=w&draft=d&revision=r&revision=s','/statblock?world=w&draft=&revision=r'])(
 'rejects missing or ambiguous target %s',url=>expect(readSavedStatblockTarget(url)).toBeNull());
