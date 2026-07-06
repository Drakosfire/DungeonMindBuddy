import { useCallback, useState } from "react";

import type { GraphAuthoringSelection } from "./graphAuthoringSelection";
import {
  buildGraphObjectAuthoringLinkExistingProposal,
  buildGraphObjectAuthoringProposal,
  buildGraphObjectAuthoringRelationshipProposal,
  createDefaultGraphObjectAuthoringFormState,
  createDefaultGraphObjectAuthoringLinkExistingFormState,
  createDefaultGraphObjectAuthoringRelationshipFormState,
  createLocalGraphObjectProposalId,
  type GraphObjectAuthoringFormState,
  type GraphObjectAuthoringLinkExistingFormState,
  type GraphObjectAuthoringProposal,
  type GraphObjectAuthoringRelationshipFormState,
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

  linkExistingFormState: GraphObjectAuthoringLinkExistingFormState;
  updateLinkExistingField: <K extends keyof GraphObjectAuthoringLinkExistingFormState>(
    field: K,
    value: GraphObjectAuthoringLinkExistingFormState[K],
  ) => void;
  stageLinkExistingProposal: () => void;

  relationshipFormState: GraphObjectAuthoringRelationshipFormState;
  updateRelationshipField: <K extends keyof GraphObjectAuthoringRelationshipFormState>(
    field: K,
    value: GraphObjectAuthoringRelationshipFormState[K],
  ) => void;
  stageRelationshipProposal: () => void;
}

export function useGraphObjectAuthoringDraft(): UseGraphObjectAuthoringDraftResult {
  const [selectedSource, setSelectedSource] = useState<GraphAuthoringSelection | null>(null);
  const [formState, setFormState] = useState<GraphObjectAuthoringFormState>(
    createDefaultGraphObjectAuthoringFormState(null),
  );
  const [linkExistingFormState, setLinkExistingFormState] =
    useState<GraphObjectAuthoringLinkExistingFormState>(
      createDefaultGraphObjectAuthoringLinkExistingFormState(),
    );
  const [relationshipFormState, setRelationshipFormState] =
    useState<GraphObjectAuthoringRelationshipFormState>(
      createDefaultGraphObjectAuthoringRelationshipFormState(),
    );
  const [proposals, setProposals] = useState<GraphObjectAuthoringProposal[]>([]);

  const openWithSelection = useCallback((selection: GraphAuthoringSelection) => {
    setSelectedSource(selection);
    setFormState(createDefaultGraphObjectAuthoringFormState(selection));
    setLinkExistingFormState(createDefaultGraphObjectAuthoringLinkExistingFormState());
  }, []);

  const dismissSelection = useCallback(() => {
    setSelectedSource(null);
    setFormState(createDefaultGraphObjectAuthoringFormState(null));
    setLinkExistingFormState(createDefaultGraphObjectAuthoringLinkExistingFormState());
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
    setLinkExistingFormState(createDefaultGraphObjectAuthoringLinkExistingFormState());
  }, [selectedSource, formState]);

  const updateLinkExistingField = useCallback(
    <K extends keyof GraphObjectAuthoringLinkExistingFormState>(
      field: K,
      value: GraphObjectAuthoringLinkExistingFormState[K],
    ) => {
      setLinkExistingFormState((prev) => ({ ...prev, [field]: value }));
    },
    [],
  );

  const stageLinkExistingProposal = useCallback(() => {
    if (!selectedSource) {
      return;
    }
    const proposal = buildGraphObjectAuthoringLinkExistingProposal(
      selectedSource,
      linkExistingFormState,
      createLocalGraphObjectProposalId(),
    );
    if (!proposal) {
      return;
    }
    setProposals((prev) => [...prev, proposal]);
    setSelectedSource(null);
    setFormState(createDefaultGraphObjectAuthoringFormState(null));
    setLinkExistingFormState(createDefaultGraphObjectAuthoringLinkExistingFormState());
  }, [selectedSource, linkExistingFormState]);

  const updateRelationshipField = useCallback(
    <K extends keyof GraphObjectAuthoringRelationshipFormState>(
      field: K,
      value: GraphObjectAuthoringRelationshipFormState[K],
    ) => {
      setRelationshipFormState((prev) => ({ ...prev, [field]: value }));
    },
    [],
  );

  const stageRelationshipProposal = useCallback(() => {
    const proposal = buildGraphObjectAuthoringRelationshipProposal(
      relationshipFormState,
      selectedSource,
      createLocalGraphObjectProposalId(),
    );
    if (!proposal) {
      return;
    }
    setProposals((prev) => [...prev, proposal]);
    setRelationshipFormState(createDefaultGraphObjectAuthoringRelationshipFormState());
  }, [relationshipFormState, selectedSource]);

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
    linkExistingFormState,
    updateLinkExistingField,
    stageLinkExistingProposal,
    relationshipFormState,
    updateRelationshipField,
    stageRelationshipProposal,
  };
}
