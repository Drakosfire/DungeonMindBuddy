import './embeddedContentFrame.css';

/** Editor-only chrome. Content nodes and their serialization stay owned by the caller. */
export function embeddedContentFrame(label: string, initialCollapsed = false, onToggle?: (collapsed: boolean) => void) {
  const dom = document.createElement('div');
  dom.className = 'embedded-content-frame';
  const header = dom.appendChild(document.createElement('div'));
  header.className = 'embedded-content-frame__header';
  header.contentEditable = 'false';
  const title = header.appendChild(document.createElement('strong'));
  title.textContent = label;
  const summary = header.appendChild(document.createElement('span'));
  const toggle = header.appendChild(document.createElement('button'));
  toggle.type = 'button';
  const content = dom.appendChild(document.createElement('div'));
  content.className = 'embedded-content-frame__body';
  let collapsed = initialCollapsed;
  function paint() {
    content.hidden = collapsed;
    toggle.textContent = collapsed ? 'Expand' : 'Collapse';
    toggle.setAttribute('aria-label', `${collapsed ? 'Expand' : 'Collapse'} ${label.toLowerCase()}`);
    toggle.setAttribute('aria-expanded', String(!collapsed));
  }
  const click = () => { collapsed = !collapsed; onToggle?.(collapsed); paint(); };
  const retainCaret = (event: MouseEvent) => event.preventDefault();
  header.addEventListener('mousedown', retainCaret);
  toggle.addEventListener('click', click);
  paint();
  return { dom, header, content, isCollapsed: () => collapsed, setSummary: (value: string) => { summary.textContent = value; },
    destroy: () => { toggle.removeEventListener('click', click); header.removeEventListener('mousedown', retainCaret); } };
}
