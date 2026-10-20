/** Inert source presentation shared by direct lookup and accepted historical citations. */
export function RulesPassageView({ section, title, page, text, attribution, sourceUri, corpus, textSha256, onClose, excerpt = false }: {
  section: string; title: string; page: string; text: string; attribution: string;
  sourceUri: string; corpus: string; textSha256: string; onClose: () => void; excerpt?: boolean;
}) {
  return <section aria-label="Cited rules passage"><h3>{section}</h3>
    <p>{title} · {page}</p>
    {excerpt && <p>Exact cited excerpt saved with this answer.</p>}
    <p style={{ whiteSpace: 'pre-wrap' }}>{text}</p><p>{attribution}</p>
    <details><summary>Source identity</summary><p>Source: {sourceUri}</p><p>Corpus: {corpus}</p><p>Passage SHA-256: {textSha256}</p></details>
    <button type="button" onClick={onClose}>Close cited passage</button>
  </section>;
}
