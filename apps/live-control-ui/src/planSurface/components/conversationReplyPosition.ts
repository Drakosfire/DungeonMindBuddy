/** Scroll only the transcript, never the document or outer workspace. */
export function positionLatestAssistantReply(viewport: HTMLElement): boolean {
  const replies = viewport.querySelectorAll<HTMLElement>(".world-plan-agent-conversation__message--assistant");
  const reply = replies.item(replies.length - 1);
  if (!reply) return false;
  viewport.scrollTop = Math.max(0, viewport.scrollTop + reply.getBoundingClientRect().top - viewport.getBoundingClientRect().top);
  return true;
}
