import {expect,it} from 'vitest';
import wire from '../test/nativePlayReceipt.json';
import {isSurfaceGraphInput} from './surfaceGraphInput';
const check=(input:unknown)=>isSurfaceGraphInput(input as typeof wire,'world-one','dmb_play_world_graph_packet_v1',['play','session','graph','history','instructions','tools','message']);
it('retains the actual historical APP Graph input shape',()=>expect(check(structuredClone(wire))).toBe(true));
it('accepts the provider-owned window value on the existing shared Graph shape',()=>{
  const c=structuredClone(wire);
  Object.assign(c.assembled_input,{context_window_limit:null,output_token_reserve:0});
  expect(check(c)).toBe(true);
});
it.each([0,-1,'128000',false,undefined,Number.NaN])('refuses malformed shared Graph capacity %s',window=>{
  const c=structuredClone(wire);Object.assign(c.assembled_input,{context_window_limit:window});
  expect(check(c)).toBe(false);
});
it('keeps the actual finite historical capacity comparison',()=>{
  const c=structuredClone(wire);c.assembled_input.context_window_limit=1;expect(check(c)).toBe(false);
});
it.each(['count','reserve','hash','world'])('null window retains shared Graph %s checks',change=>{
  const c=structuredClone(wire);Object.assign(c.assembled_input,{context_window_limit:null,output_token_reserve:0});
  if(change==='count')c.assembled_input.provider_envelope_input_tokens=-1;
  if(change==='reserve')c.assembled_input.output_token_reserve=-1;
  if(change==='hash')c.assembled_input.assembled_input_sha256='not-a-hash';
  if(change==='world')c.graph_authority.managed_world_id='foreign';
  expect(check(c)).toBe(false);
});
