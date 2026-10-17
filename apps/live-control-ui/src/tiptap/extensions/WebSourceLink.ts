import { Mark } from '@tiptap/core';
import { webSourceHref } from '../markdown/webSourceHref';

/** Explicit web links; no autolink or authority-producing behavior. */
export const WebSourceLink = Mark.create({
  name: 'link',
  inclusive: false,
  addAttributes() { return { href: { default: null } }; },
  parseHTML() {
    return [{ tag: 'a[href]', getAttrs: element => {
      const href = webSourceHref(element.getAttribute('href'));
      return href && !element.hasAttribute('title') ? { href } : false;
    } }];
  },
  renderHTML({ HTMLAttributes }) {
    const href = webSourceHref(HTMLAttributes.href);
    return href ? ['a', { href, target: '_blank', rel: 'noopener noreferrer' }, 0] : ['span', {}, 0];
  },
});
