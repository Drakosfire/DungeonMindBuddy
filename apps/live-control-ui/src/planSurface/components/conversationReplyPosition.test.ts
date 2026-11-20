import {describe,expect,it,vi} from "vitest";
import {positionLatestAssistantReply} from "./conversationReplyPosition";
describe("reply reading position",()=>{
 it("aligns the latest answer's beginning without scrolling an outer reader",()=>{
  const outer=document.createElement("div"),viewport=document.createElement("div");
  outer.scrollTop=71;outer.append(viewport);viewport.scrollTop=40;
  viewport.innerHTML='<div class="world-plan-agent-conversation__message--assistant">old</div><div class="world-plan-agent-conversation__message--assistant">new long answer</div>';
  vi.spyOn(viewport,"getBoundingClientRect").mockReturnValue({top:90} as DOMRect);
  vi.spyOn(viewport.lastElementChild!,"getBoundingClientRect").mockReturnValue({top:260} as DOMRect);
  expect(positionLatestAssistantReply(viewport)).toBe(true);expect(viewport.scrollTop).toBe(210);expect(outer.scrollTop).toBe(71);
 });
 it("does not scroll an empty or pending transcript",()=>{const viewport=document.createElement("div");viewport.scrollTop=35;expect(positionLatestAssistantReply(viewport)).toBe(false);expect(viewport.scrollTop).toBe(35);});
});
