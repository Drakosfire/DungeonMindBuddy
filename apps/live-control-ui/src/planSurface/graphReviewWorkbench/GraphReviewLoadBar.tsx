interface GraphReviewLoadBarProps {
  loaded: boolean;
  summaryLabel: string | null;
  onOpenLoad: () => void;
}

export function GraphReviewLoadBar({
  loaded,
  summaryLabel,
  onOpenLoad,
}: GraphReviewLoadBarProps) {
  return (
    <section className="graph-review-load-bar" aria-label="Graph review load controls">
      {loaded && summaryLabel ? (
        <>
          <p>{summaryLabel}</p>
          <button type="button" onClick={onOpenLoad}>
            Change
          </button>
        </>
      ) : (
        <>
          <p>Load a World Graph session to review committed objects in recap prose.</p>
          <button type="button" onClick={onOpenLoad}>
            Load session
          </button>
        </>
      )}
    </section>
  );
}
