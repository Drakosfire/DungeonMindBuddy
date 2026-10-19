import "./CardSceneNavigation.css";

/** Browse presentation order. The owner supplies Plan selection or Play inspection. */
export function CardSceneNavigation({ scenes, sceneId, onSelect, hidden = false }: {
  scenes: readonly { id: string; title: string }[];
  sceneId: string | null;
  onSelect: (sceneId: string) => void;
  hidden?: boolean;
}) {
  const index = scenes.findIndex(scene => scene.id === sceneId);
  const previous = index > 0 ? scenes[index - 1] : undefined;
  const next = index >= 0 ? scenes[index + 1] : undefined;
  return <nav className="card-scene-navigation" aria-label="Card navigation" hidden={hidden}>
    <button type="button" aria-label="Previous scene" title={previous ? `Previous scene: ${previous.title}` : "First scene"}
      disabled={!previous} onClick={() => { if (previous) onSelect(previous.id); }}>
      <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M15 5l-7 7 7 7" /></svg>
    </button>
    <button type="button" aria-label="Next scene" title={next ? `Next scene: ${next.title}` : "Last scene"}
      disabled={!next} onClick={() => { if (next) onSelect(next.id); }}>
      <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M9 5l7 7-7 7" /></svg>
    </button>
  </nav>;
}
