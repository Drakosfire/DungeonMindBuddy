import { useEffect, useState } from "react";
import "./IngestionActivity.css";

/** Request activity, not model reasoning or inferred backend stage progress. */
export function IngestionActivity({ session }: { session: number }) {
  const [startedAt] = useState(() => Date.now());
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  useEffect(() => {
    const timer = window.setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - startedAt) / 1000));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [startedAt]);
  const elapsed = `${Math.floor(elapsedSeconds / 60)}:${String(elapsedSeconds % 60).padStart(2, "0")}`;

  return (
    <section className="ingestion-activity" aria-label="Extraction activity">
      <div className="ingestion-activity__heading">
        <h2>Working on Session {session}</h2>
        <span role="timer" aria-label="Time waiting for extraction">{elapsed} elapsed</span>
      </div>
      <p role="status">Your recap is submitted. Waiting for extraction and validation to finish…</p>
      <p>The extraction looks for people, places, events, clues, and their relationships, using your recap as the source.</p>
      <p>What comes next:</p>
      <ol>
        <li>Inspect the extracted nodes and relationships.</li>
        <li>Review what belongs in your World Graph before publishing.</li>
      </ol>
      <p className="ingestion-activity__detail">This request returns its results together. Nodes will appear when the response arrives; nothing is published automatically.</p>
    </section>
  );
}
