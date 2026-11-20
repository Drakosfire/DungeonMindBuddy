import { Mark } from '@tiptap/core';
import { Plugin } from '@tiptap/pm/state';
import { nativePassageTarget, webSourceHref, validWebSourceTitle } from '../markdown/webSourceHref';

async function openNativePassage(target: NonNullable<ReturnType<typeof nativePassageTarget>>) {
  const dialog = document.createElement('dialog');
  const title = document.createElement('h2');
  title.textContent = 'Source passage';
  dialog.setAttribute('aria-label', title.textContent);
  const close = document.createElement('button');
  close.type = 'button';
  close.textContent = 'Close';
  close.addEventListener('click', () => dialog.close());
  const passage = document.createElement('p');
  passage.style.whiteSpace = 'pre-wrap';
  passage.textContent = 'Opening source passage…';
  dialog.append(title, close, passage);
  dialog.addEventListener('close', () => dialog.remove(), {once: true});
  document.body.append(dialog);
  dialog.showModal();
  try {
    const {getAgentNativeBodyExcerpt} = await import('../../api/liveApi');
    const result = await getAgentNativeBodyExcerpt(target.worldId, target.turnId, target.index);
    if (result.world_id !== target.worldId || result.turn_id !== target.turnId
        || result.citation_index !== target.index || typeof result.content !== 'string') {
      throw new Error('The returned passage does not match this link.');
    }
    title.textContent = result.display_label || 'Source passage';
    passage.textContent = result.content;
  } catch {
    passage.textContent = 'The exact source passage could not be reopened.';
  }
}

function activateSourceLink(root: HTMLElement, event: MouseEvent | KeyboardEvent): boolean {
  if (event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return false;
  if (event instanceof MouseEvent && event.button !== 0) return false;
  if (event instanceof KeyboardEvent && event.key !== 'Enter') return false;
  const target = event.target;
  const anchor = target instanceof Element ? target.closest('a[data-web-source-link]') : null;
  if (!(anchor instanceof HTMLAnchorElement) || !root.contains(anchor)) return false;
  // Admission is checked again: a mutable DOM href is not trusted authority.
  const native = nativePassageTarget(anchor.getAttribute('data-native-passage'));
  const href = webSourceHref(anchor.getAttribute('href'));
  event.preventDefault();
  if (native) void openNativePassage(native);
  else if (href && !nativePassageTarget(href)) window.open(href, '_blank', 'noopener,noreferrer');
  return true;
}

/** Explicit web links; no autolink or authority-producing behavior. */
export const WebSourceLink = Mark.create({
  name: 'link',
  inclusive: false,
  addAttributes() { return { href: { default: null }, title: { default: null } }; },
  parseHTML() {
    return [{ tag: 'a[href]', getAttrs: element => {
      const locator = element.getAttribute('data-native-passage');
      const href = webSourceHref(nativePassageTarget(locator) ? locator : element.getAttribute('href'));
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
    if (href && nativePassageTarget(href) && validWebSourceTitle(HTMLAttributes.title)) {
      return ['a', {href: '#', 'data-native-passage': href, 'data-web-source-link': '', tabindex: '0'}, 0];
    }
    return href && validWebSourceTitle(HTMLAttributes.title) ? ['a', { href, ...(HTMLAttributes.title == null ? {} : {title: HTMLAttributes.title}), target: '_blank', rel: 'noopener noreferrer', 'data-web-source-link': '', tabindex: '0' }, 0] : ['span', {}, 0];
  },
});
