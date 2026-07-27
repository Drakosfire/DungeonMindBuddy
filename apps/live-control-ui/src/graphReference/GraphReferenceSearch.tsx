import {
  PlanGraphRefSearch,
  type PlanGraphRefSearchProps,
} from "../planSurface/components/PlanGraphRefSearch";

export type GraphReferenceSearchProps = PlanGraphRefSearchProps;

/** Surface-neutral wrapper around Plan graph reference search UI. */
export function GraphReferenceSearch(props: GraphReferenceSearchProps) {
  return <PlanGraphRefSearch {...props} />;
}
