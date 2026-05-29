import type { ProjectionTargetType } from "../api/types";
import { formatTargetType } from "./targetTypes";

interface TargetChipProps {
  targetType: ProjectionTargetType;
  label: string;
  onSelectTarget?: () => void;
}

export function TargetChip({ targetType, label, onSelectTarget }: TargetChipProps) {
  const text = `${formatTargetType(targetType)} · ${label}`;
  if (onSelectTarget) {
    return (
      <button type="button" className="timeline-ref-chip timeline-ref-button" onClick={onSelectTarget}>
        {text}
      </button>
    );
  }
  return <span className="timeline-ref-chip">{text}</span>;
}
