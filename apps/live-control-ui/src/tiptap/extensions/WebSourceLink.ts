import { Mark } from '@tiptap/core';
import { Plugin } from '@tiptap/pm/state';
import { webSourceHref, validWebSourceTitle } from '../markdown/webSourceHref';

function activateSourceLink(root: HTMLElement, event: MouseEvent | KeyboardEvent): boolean {
  if (event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return false;
  if (event instanceof MouseEvent && event.button !== 0) return false;
  if (event instanceof KeyboardEvent && event.key !== 'Enter') return false;
  const target = event.target;
  const anchor = target instanceof Element ? target.closest('a[data-web-source-link]') : null;
  if (!(anchor instanceof HTMLAnchorElement) || !root.contains(anchor)) return false;
  // Admission is checked again: a mutable DOM href is not trusted authority.
  const href = webSourceHref(anchor.getAttribute('href'));
  event.preventDefault();
  if (href) window.open(href, '_blank', 'noopener,noreferrer');
  return true;
}

/** Explicit web links; no autolink or authority-producing behavior. */
export const WebSourceLink = Mark.create({
  name: 'link',
  inclusive: false,
  addAttributes() { return { href: { default: null }, title: { default: null } }; },
  parseHTML() {
    return [{ tag: 'a[href]', getAttrs: element => {
      const href = webSourceHref(element.getAttribute('href'));
      const title = element.getAttribute('title');
      return href && validWebSourceTitle(title) ? { href, title } : false;
    } }];
  },
  addProseMirrorPlugins() {
    return [new Plugin({ props: { handleDOMEvents: {
      click: (view, event) => activateSourceLink(view.dom, event),
      keydown: (view, event) => activateSourceLink(view.dom, event),
    } } })];
  },
  renderHTML({ HTMLAttributes }) {
    const href = webSourceHref(HTMLAttributes.href);
    return href && validWebSourceTitle(HTMLAttributes.title) ? ['a', { href, ...(HTMLAttributes.title == null ? {} : {title: HTMLAttributes.title}), target: '_blank', rel: 'noopener noreferrer', 'data-web-source-link': '', tabindex: '0' }, 0] : ['span', {}, 0];
  },
});
