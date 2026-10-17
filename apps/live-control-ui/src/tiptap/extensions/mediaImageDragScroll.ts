/** Scroll the nearest eligible editor ancestor while a media drag rests at its edge. */
export function mediaDragScroll(editor: HTMLElement) {
  let frame = 0;
  let point: {x: number; y: number} | null = null;
  let dragging = false;
  const stop = () => { dragging = false; point = null; cancelAnimationFrame(frame); frame = 0; };
  const tick = () => {
    frame = 0;
    if (!point || !dragging || !editor.isConnected) return;
    for (let element = editor.parentElement; element; element = element.parentElement) {
      const style = getComputedStyle(element);
      if (!/(auto|scroll)/.test(style.overflowY) || element.scrollHeight <= element.clientHeight) continue;
      const rect = element.getBoundingClientRect();
      const top = Math.max(0, rect.top), bottom = Math.min(window.innerHeight, rect.bottom);
      if (point.x < rect.left || point.x > rect.right || point.y < top - 24 || point.y > bottom + 24) continue;
      const delta = dragScrollDelta(point.y, top, bottom);
      const before = element.scrollTop;
      element.scrollTop += delta;
      if (element.scrollTop !== before) break;
    }
    frame = requestAnimationFrame(tick);
  };
  const start = (event: DragEvent) => {
    dragging = event.target instanceof Element && !!event.target.closest('.document-media-image');
  };
  const over = (event: DragEvent) => {
    const savedImage = Array.from(event.dataTransfer?.types ?? []).includes('application/x-dmb-media');
    if (!dragging && !savedImage) return;
    dragging = true;
    point = {x: event.clientX, y: event.clientY};
    if (!frame) frame = requestAnimationFrame(tick);
  };
  const leave = (event: DragEvent) => { if (!event.relatedTarget && (event.clientX <= 0 || event.clientY <= 0 || event.clientX >= window.innerWidth || event.clientY >= window.innerHeight)) stop(); };
  document.addEventListener('dragstart', start, true);
  document.addEventListener('dragover', over, true);
  document.addEventListener('drop', stop, true);
  document.addEventListener('dragend', stop, true);
  document.addEventListener('dragleave', leave, true);
  window.addEventListener('blur', stop);
  return () => {
    stop();
    document.removeEventListener('dragstart', start, true);
    document.removeEventListener('dragover', over, true);
    document.removeEventListener('drop', stop, true);
    document.removeEventListener('dragend', stop, true);
    document.removeEventListener('dragleave', leave, true);
    window.removeEventListener('blur', stop);
  };
}
export function dragScrollDelta(y: number, top: number, bottom: number): number {
  const edge = Math.min(64, (bottom - top) / 3);
  if (edge <= 0) return 0;
  if (y < top + edge) return -Math.ceil(18 * Math.min(1, (top + edge - y) / edge));
  if (y > bottom - edge) return Math.ceil(18 * Math.min(1, (y - bottom + edge) / edge));
  return 0;
}
