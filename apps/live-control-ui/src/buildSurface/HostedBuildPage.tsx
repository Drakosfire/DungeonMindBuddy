import { BuildPdfPreview } from "./BuildPdfPreview";
import { BuildPdfStatblockReview } from "./BuildPdfStatblockReview";
import { SavedStatblockFullView } from "../statblocks/StatblockPage";
import { readSavedStatblockTarget } from "../statblocks/savedStatblockLocation";
import "./buildSurface.css";

export function HostedBuildPage({ worldId, locationSnapshot }: {
  readonly worldId: string;
  readonly locationSnapshot: string;
}) {
  const url = new URL(locationSnapshot, "http://localhost");
  const params = url.searchParams;
  const scoped = params.getAll("world");
  const matchesWorld = scoped.length === 1 && scoped[0] === worldId;
  const reviewId = matchesWorld ? params.get("pdfReview") : null;
  const statblock = matchesWorld ? readSavedStatblockTarget(locationSnapshot) : null;

  if (reviewId) {
    return <BuildPdfStatblockReview key={reviewId} worldId={worldId} reviewId={reviewId} />;
  }
  if (statblock?.sourceReviewId && statblock.worldId === worldId) {
    return <SavedStatblockFullView target={statblock} toolbarHost={null} />;
  }
  return (
    <main className="build-pdf-workspace" aria-label="Build">
      <h1>Build</h1>
      <BuildPdfPreview worldId={worldId} persistShortcuts={false} />
    </main>
  );
}
