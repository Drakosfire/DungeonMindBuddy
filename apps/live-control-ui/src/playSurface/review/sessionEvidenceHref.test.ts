import {it,expect} from 'vitest';
import {admittedSessionEvidenceHref} from './sessionEvidenceHref';
const base='/play?world=park+%2F+%26&run=11111111-1111-4111-8111-111111111111&evidence_revision=54';
const fragment='#source-0-'+['a','b','c','d'].map(x=>x.repeat(64)).join('-');
it('admits whole immutable reviews and exact generated source syntax without interpreting evidence',()=>{
 expect(admittedSessionEvidenceHref(base)).toBe(true);expect(admittedSessionEvidenceHref(base+fragment)).toBe(true);
});
it.each([
 base+'&world=other',base+'&run=other',base+'&unknown=1',base.replace('evidence_revision=54','review=1'),
 base.replace('54','054'),base.replace('54','0'),base.replace('54','9007199254740992'),
 base.replace('park+%2F+%26',''),base.replace('park+%2F+%26','%20park'),base.replace('park+%2F+%26','park%00'),
 base.replace('11111111-1111-4111-8111-111111111111','not-run'),base.replace('/play?','//evil/play?'),
 base.replace('/play?','/other?'),base.replace('/play?','/a/../play?'),base+'#arbitrary',base+'#source-0-a',
 base+fragment.replace('source-0','source-01'),base+fragment+'x','../session',
])('refuses unsupported or conflicting session href %s',href=>expect(admittedSessionEvidenceHref(href)).toBe(false));
