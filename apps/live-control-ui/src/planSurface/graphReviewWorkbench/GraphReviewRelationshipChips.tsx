import type { GraphProjectionAdjacencyCandidate } from "../../api/types";
import {
  groupRelationshipsByEvidence,
  relatedSummaryForRelationship,
  relationshipGroupLabel,
  relationshipGroupMetaLine,
  relationshipSourceExcerpt,
  relationshipSourceExcerptIsFullParagraph,
  relationshipSourceExcerptSegments,
} from "./graphReviewSelectionUtils";

function RelationshipSourceExcerptText({
  relationship,
}: {
  relationship: GraphProjectionAdjacencyCandidate;
}) {
  const segments = relationshipSourceExcerptSegments(relationship);
  if (!segments.length) return null;
  return (
    <p>
      {segments.map((segment, index) =>
        segment.highlighted ? (
          <mark key={index}>{segment.text}</mark>
        ) : (
          <span key={index}>{segment.text}</span>
        ),
      )}
    </p>
  );
}

function RelationshipInlineDetail({
  members,
}: {
  members: GraphProjectionAdjacencyCandidate[];
}) {
  const primary = members[0];
  const sourceExcerpt = relationshipSourceExcerpt(primary);
  const isFullParagraph = relationshipSourceExcerptIsFullParagraph(primary);
  const evidenceRefCount = new Set(members.flatMap((member) => member.evidence_ref_ids)).size;
  const sourceDomains = [...new Set(members.flatMap((member) => member.source_domains))];
  const sessionIds = [...new Set(members.flatMap((member) => member.session_ids ?? []))];

  return (
    <div className="graph-review-relationship-inline-detail">
      {members.map((member) => {
        const relatedSummary = relatedSummaryForRelationship(member);
        if (!relatedSummary) return null;
        return (
          <p key={member.edge_id}>
            <strong>About {member.label}:</strong> {relatedSummary}
          </p>
        );
      })}
      {sourceExcerpt ? (
        <blockquote className="graph-review-relationship-source-excerpt">
          <p className="graph-review-muted">
            {isFullParagraph
              ? members.length > 1
                ? "Source paragraph (shared by these linked objects, highlighted excerpt below)"
                : "Source paragraph (highlighted excerpt below)"
              : "Source excerpt"}
          </p>
          <RelationshipSourceExcerptText relationship={primary} />
        </blockquote>
      ) : (
        <p className="graph-review-muted">No source excerpt is projected for this link yet.</p>
      )}
      <dl className="graph-review-lane-meta">
        <div>
          <dt>Evidence</dt>
          <dd>
            {evidenceRefCount} supporting ref{evidenceRefCount === 1 ? "" : "s"}
          </dd>
        </div>
        <div>
          <dt>Sources</dt>
          <dd>{sourceDomains.length ? sourceDomains.join(", ") : "—"}</dd>
        </div>
        <div>
          <dt>Sessions</dt>
          <dd>{sessionIds.length ? sessionIds.join(", ") : "—"}</dd>
        </div>
      </dl>
      <details className="graph-review-relationship-technical-details">
        <summary>Technical details</summary>
        <p>
          {members
            .map(
              (member) =>
                `Edge ${member.edge_id || "unavailable"}; direction ${member.direction || "unknown"}.`,
            )
            .join(" ")}
        </p>
      </details>
    </div>
  );
}

export function GraphReviewRelationshipChips({
  relationships,
  selectedEdgeId,
  onSelect,
  onClear,
}: {
  relationships: GraphProjectionAdjacencyCandidate[];
  selectedEdgeId: string | null;
  onSelect: (relationship: GraphProjectionAdjacencyCandidate) => void;
  onClear?: () => void;
}) {
  if (!relationships.length) {
    return (
      <p className="graph-review-muted">
        No connected campaign relationships are projected for this node yet.
      </p>
    );
  }

  const groups = groupRelationshipsByEvidence(relationships);

  return (
    <ul className="graph-review-relationship-list" aria-label="Connected relationships">
      {groups.map((group) => {
        const label = relationshipGroupLabel(group.members);
        const metaLine = relationshipGroupMetaLine(group.members);
        const expanded = group.members.some((member) => member.edge_id === selectedEdgeId);

        return (
          <li key={group.key}>
            <button
              type="button"
              className="graph-review-relationship-row"
              aria-expanded={expanded}
              onClick={() => (expanded ? onClear?.() : onSelect(group.members[0]))}
            >
              <span className="graph-review-relationship-target">{label}</span>
              {metaLine ? (
                <span className="graph-review-relationship-meta">{metaLine}</span>
              ) : null}
            </button>
            {expanded ? <RelationshipInlineDetail members={group.members} /> : null}
          </li>
        );
      })}
    </ul>
  );
}
