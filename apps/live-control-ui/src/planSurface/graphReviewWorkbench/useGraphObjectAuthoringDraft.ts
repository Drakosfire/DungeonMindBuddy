import { useCallback, useState } from "react";

import type { GraphAuthoringSelection } from "./graphAuthoringSelection";
import {
  buildGraphObjectAuthoringProposal,
  createDefaultGraphObjectAuthoringFormState,
  createLocalGraphObjectProposalId,
  type GraphObjectAuthoringFormState,
  type GraphObjectAuthoringProposal,
} from "./graphObjectAuthoringDraft";

export interface UseGraphObjectAuthoringDraftResult {
  selectedSource: GraphAuthoringSelection | null;
  formState: GraphObjectAuthoringFormState;
  proposals: GraphObjectAuthoringProposal[];
  openWithSelection: (selection: GraphAuthoringSelection) => void;
  dismissSelection: () => void;
  updateFormField: <K extends keyof GraphObjectAuthoringFormState>(
    field: K,
    value: GraphObjectAuthoringFormState[K],
  ) => void;
  stageProposal: () => void;
  removeProposal: (localProposalId: string) => void;
}

export function useGraphObjectAuthoringDraft(): UseGraphObjectAuthoringDraftResult {
  const [selectedSource, setSelectedSource] = useState<GraphAuthoringSelection | null>(null);
  const [formState, setFormState] = useState<GraphObjectAuthoringFormState>(
    createDefaultGraphObjectAuthoringFormState(null),
  );
  const [proposals, setProposals] = useState<GraphObjectAuthoringProposal[]>([]);

  const openWithSelection = useCallback((selection: GraphAuthoringSelection) => {
    setSelectedSource(selection);
    setFormState(createDefaultGraphObjectAuthoringFormState(selection));
  }, []);

  const dismissSelection = useCallback(() => {
    setSelectedSource(null);
    setFormState(createDefaultGraphObjectAuthoringFormState(null));
  }, []);

  const updateFormField = useCallback(
    <K extends keyof GraphObjectAuthoringFormState>(
      field: K,
      value: GraphObjectAuthoringFormState[K],
    ) => {
      setFormState((prev) => ({ ...prev, [field]: value }));
    },
    [],
  );

  const stageProposal = useCallback(() => {
    if (!selectedSource || !formState.label.trim()) {
      return;
    }
    const proposal = buildGraphObjectAuthoringProposal(
      selectedSource,
      formState,
      createLocalGraphObjectProposalId(),
    );
    setProposals((prev) => [...prev, proposal]);
    setSelectedSource(null);
    setFormState(createDefaultGraphObjectAuthoringFormState(null));
  }, [selectedSource, formState]);

  const removeProposal = useCallback((localProposalId: string) => {
    setProposals((prev) => prev.filter((proposal) => proposal.localProposalId !== localProposalId));
  }, []);

  return {
    selectedSource,
    formState,
    proposals,
    openWithSelection,
    dismissSelection,
    updateFormField,
    stageProposal,
    removeProposal,
  };
}
