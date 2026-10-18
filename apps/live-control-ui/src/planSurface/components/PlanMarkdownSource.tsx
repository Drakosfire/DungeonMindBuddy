import "./PlanMarkdownSource.css";

export function PlanMarkdownSource({ value, onChange, disabled }: {
  value: string;
  onChange: (value: string) => void;
  disabled: boolean;
}) {
  return <section className="plan-markdown-source" aria-label="Markdown authoring">
    <details className="plan-markdown-source__help">
      <summary>Markdown help</summary>
      <div>
        <h2>Write with Markdown</h2>
        <dl>
          <dt><code># Heading 1</code></dt><dd>Main heading</dd>
          <dt><code>## Heading 2</code></dt><dd>Section heading</dd>
          <dt><code>**Bold** and *italic*</code></dt><dd>Emphasis</dd>
          <dt><code>- List item</code></dt><dd>Bulleted list</dd>
          <dt><code>[Label](https://example.com)</code></dt><dd>Source link</dd>
        </dl>
        <h3>Read Aloud block</h3>
        <pre>{"> [!READ-ALOUD]\n> The road gives way to a maintained boardwalk.\n> Dark water gathers beneath it."}</pre>
        <p>Document metadata is retained automatically. Keep the existing scene markers with their headings when moving cards. Document view marks those card boundaries with horizontal lines.</p>
      </div>
    </details>
    <label htmlFor="world-plan-markdown-source">Plan Markdown</label>
    <textarea id="world-plan-markdown-source" value={value} disabled={disabled}
      onChange={event => onChange(event.target.value)} spellCheck={false} />
  </section>;
}
