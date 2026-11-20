/** Edge scrolling exists only for an owned suggestion drag. */
export function startProposalDragScroll(editor: HTMLElement): () => void {
  const parents: HTMLElement[] = [];
  for (let parent = editor.parentElement; parent; parent = parent.parentElement) {
    if (/auto|scroll/.test(getComputedStyle(parent).overflowY)) parents.push(parent);
  }
  const root = document.scrollingElement;
  if (root instanceof HTMLElement && !parents.includes(root)) parents.push(root);
  let pointer: number | null = null;
  let frame = 0;
  let active = true;
  const tick = () => {
    if (!active) return;
    if (pointer !== null) {
      for (const parent of parents) {
        const rect = parent === root ? {top: 0, bottom: window.innerHeight} : parent.getBoundingClientRect();
        const direction = pointer < rect.top + 48 ? -1 : pointer > rect.bottom - 48 ? 1 : 0;
        const available = direction < 0 ? parent.scrollTop > 0
          : direction > 0 && parent.scrollTop < parent.scrollHeight - parent.clientHeight;
        if (available) { parent.scrollTop += direction * 12; break; }
      }
    }
    frame = requestAnimationFrame(tick);
  };
  const update = (event: DragEvent) => { pointer = event.clientY; };
  const stop = () => {
    active = false; cancelAnimationFrame(frame);
    document.removeEventListener('dragover', update, true);
    document.removeEventListener('dragend', stop, true);
    document.removeEventListener('drop', stop, true);
  };
  document.addEventListener('dragover', update, true);
  document.addEventListener('dragend', stop, true);
  document.addEventListener('drop', stop, true);
  frame = requestAnimationFrame(tick);
  return stop;
}
