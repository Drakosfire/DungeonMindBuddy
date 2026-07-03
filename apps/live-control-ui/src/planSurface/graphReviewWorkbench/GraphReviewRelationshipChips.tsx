import type { GraphReviewGameRelationship } from "./graphReviewAuthoringMockData";

export function GraphReviewRelationshipChips({ relationships, selectedId, onSelect }: { relationships: GraphReviewGameRelationship[]; selectedId: string | null; onSelect: (id: string) => void }) {
  return (
    <div className="graph-review-relationship-chips" aria-label="Readable relationships">
      {relationships.map((relationship) => (
        <button key={relationship.id} type="button" aria-pressed={selectedId === relationship.id} onClick={() => onSelect(relationship.id)}>
          {relationship.predicate} → {relationship.target}
        </button>
      ))}
    </div>
  );
}
