import {
  validateSurfaceInteractionPublication,
} from "../surfaceInteraction/publication";
import { sameSurfaceInteractionIdentity } from "../surfaceInteraction/surfaceIdentity";
import type {
  SurfaceInteractionEditCommandContribution,
  SurfaceInteractionIdentity,
  SurfaceInteractionPublication,
  SurfaceInteractionToolContribution,
  SurfaceInteractionValidationIssue,
} from "../surfaceInteraction/types";

export type SurfaceInteractionLeaseSource = "native" | "legacy_projection" | "legacy_route";

export interface SurfaceInteractionChromeFragment {
  tools: readonly SurfaceInteractionToolContribution[];
  editCommands: readonly SurfaceInteractionEditCommandContribution[];
}

export interface SurfaceInteractionLeaseSnapshot {
  token: symbol;
  boundIdentity: SurfaceInteractionIdentity | null;
  leaseSource: SurfaceInteractionLeaseSource;
  rawBasePublication: SurfaceInteractionPublication | null;
  chromeFragment: SurfaceInteractionChromeFragment | null;
  chromeFragmentToken: symbol | null;
  rawEffectivePublication: SurfaceInteractionPublication | null;
  effectivePublication: SurfaceInteractionPublication | null;
  validationIssues: readonly SurfaceInteractionValidationIssue[];
}

export interface LeaseCallbackGate {
  isAuthorized: (
    token: symbol,
    kind: "tool" | "edit",
    contributionId: string,
    originalInvoke: () => void | Promise<void>,
  ) => boolean;
}

export function createSurfaceInteractionLeaseToken(): symbol {
  return Symbol("surface-interaction-lease");
}

function validateBaseInput(input: unknown): {
  publication: SurfaceInteractionPublication | null;
  boundIdentity: SurfaceInteractionIdentity | null;
  issues: readonly SurfaceInteractionValidationIssue[];
} {
  if (input === null) {
    return { publication: null, boundIdentity: null, issues: [] };
  }
  const result = validateSurfaceInteractionPublication(input);
  if (!result.valid) {
    return { publication: null, boundIdentity: null, issues: result.issues };
  }
  return {
    publication: result.publication,
    boundIdentity: result.publication.identity,
    issues: [],
  };
}

function composeRawEffectivePublication(
  base: SurfaceInteractionPublication | null,
  chromeFragment: SurfaceInteractionChromeFragment | null,
  leaseSource: SurfaceInteractionLeaseSource,
): SurfaceInteractionPublication | null {
  if (!base) return null;
  if (leaseSource === "native" || !chromeFragment) {
    return base;
  }
  return {
    ...base,
    tools: [...base.tools, ...chromeFragment.tools],
    editCommands: [...base.editCommands, ...chromeFragment.editCommands],
  };
}

function finalizeSnapshot(
  snapshot: Omit<
    SurfaceInteractionLeaseSnapshot,
    "rawEffectivePublication" | "effectivePublication" | "validationIssues"
  >,
  gate: LeaseCallbackGate,
): SurfaceInteractionLeaseSnapshot {
  const rawEffectivePublication = composeRawEffectivePublication(
    snapshot.rawBasePublication,
    snapshot.chromeFragment,
    snapshot.leaseSource,
  );
  if (!rawEffectivePublication) {
    return {
      ...snapshot,
      rawEffectivePublication: null,
      effectivePublication: null,
      validationIssues: snapshot.rawBasePublication ? [] : [],
    };
  }
  const validated = validateSurfaceInteractionPublication(rawEffectivePublication);
  if (!validated.valid) {
    return {
      ...snapshot,
      rawEffectivePublication,
      effectivePublication: null,
      validationIssues: validated.issues,
    };
  }
  return {
    ...snapshot,
    rawEffectivePublication,
    effectivePublication: wrapPublicationCallbacks(validated.publication, snapshot.token, gate),
    validationIssues: [],
  };
}

export function wrapPublicationCallbacks(
  publication: SurfaceInteractionPublication,
  token: symbol,
  gate: LeaseCallbackGate,
): SurfaceInteractionPublication {
  return {
    ...publication,
    tools: publication.tools.map((tool) => wrapToolContribution(tool, token, gate)),
    editCommands: publication.editCommands.map((command) => wrapEditCommand(command, token, gate)),
  };
}

function wrapToolContribution(
  tool: SurfaceInteractionToolContribution,
  token: symbol,
  gate: LeaseCallbackGate,
): SurfaceInteractionToolContribution {
  if (tool.activation.kind !== "command") return tool;
  const originalInvoke = tool.activation.invoke;
  return {
    ...tool,
    activation: {
      kind: "command",
      invoke: () => {
        if (!gate.isAuthorized(token, "tool", tool.id, originalInvoke)) return undefined;
        return originalInvoke();
      },
    },
  };
}

function wrapEditCommand(
  command: SurfaceInteractionEditCommandContribution,
  token: symbol,
  gate: LeaseCallbackGate,
): SurfaceInteractionEditCommandContribution {
  const originalInvoke = command.invoke;
  return {
    ...command,
    invoke: () => {
      if (!gate.isAuthorized(token, "edit", command.id, originalInvoke)) return undefined;
      return originalInvoke();
    },
  };
}

export function createLeaseCallbackGate(
  getSnapshot: () => SurfaceInteractionLeaseSnapshot | null,
): LeaseCallbackGate {
  return {
    isAuthorized(token, kind, contributionId, originalInvoke) {
      const snapshot = getSnapshot();
      if (!snapshot || snapshot.token !== token) return false;
      if (!snapshot.rawEffectivePublication) return false;
      if (kind === "tool") {
        const contribution = snapshot.rawEffectivePublication.tools.find((entry) => entry.id === contributionId);
        if (!contribution || contribution.availability.status !== "enabled") return false;
        if (contribution.activation.kind !== "command") return false;
        return contribution.activation.invoke === originalInvoke;
      }
      const contribution = snapshot.rawEffectivePublication.editCommands.find((entry) => entry.id === contributionId);
      if (!contribution || contribution.availability.status !== "enabled") return false;
      return contribution.invoke === originalInvoke;
    },
  };
}

export function bindSurfaceInteractionLease(
  input: unknown | null,
  leaseSource: SurfaceInteractionLeaseSource,
  gate: LeaseCallbackGate,
): SurfaceInteractionLeaseSnapshot {
  const token = createSurfaceInteractionLeaseToken();
  if (input === null) {
    return finalizeSnapshot(
      {
        token,
        boundIdentity: null,
        leaseSource,
        rawBasePublication: null,
        chromeFragment: null,
        chromeFragmentToken: null,
      },
      gate,
    );
  }
  const validated = validateBaseInput(input);
  if (!validated.publication) {
    return finalizeSnapshot(
      {
        token,
        boundIdentity: null,
        leaseSource,
        rawBasePublication: null,
        chromeFragment: null,
        chromeFragmentToken: null,
      },
      gate,
    );
  }
  return finalizeSnapshot(
    {
      token,
      boundIdentity: validated.boundIdentity,
      leaseSource,
      rawBasePublication: validated.publication,
      chromeFragment: null,
      chromeFragmentToken: null,
    },
    gate,
  );
}

export function updateSurfaceInteractionLease(
  snapshot: SurfaceInteractionLeaseSnapshot,
  capturedToken: symbol,
  input: unknown,
  gate: LeaseCallbackGate,
): SurfaceInteractionLeaseSnapshot | null {
  if (snapshot.token !== capturedToken) return null;
  const validated = validateBaseInput(input);
  if (!validated.publication || !validated.boundIdentity) {
    return finalizeSnapshot(
      {
        ...snapshot,
        rawBasePublication: validated.publication,
        boundIdentity: snapshot.boundIdentity,
      },
      gate,
    );
  }
  if (!snapshot.boundIdentity || !sameSurfaceInteractionIdentity(snapshot.boundIdentity, validated.boundIdentity)) {
    return finalizeSnapshot(
      {
        ...snapshot,
        rawBasePublication: null,
        boundIdentity: snapshot.boundIdentity,
      },
      gate,
    );
  }
  return finalizeSnapshot(
    {
      ...snapshot,
      boundIdentity: validated.boundIdentity,
      rawBasePublication: validated.publication,
    },
    gate,
  );
}

export function isChromeFragmentAllowed(snapshot: SurfaceInteractionLeaseSnapshot): boolean {
  return snapshot.leaseSource !== "native";
}

export function registerChromeCompatibilityFragment(
  snapshot: SurfaceInteractionLeaseSnapshot,
  capturedSurfaceToken: symbol,
  fragmentToken: symbol,
  fragment: SurfaceInteractionChromeFragment,
  gate: LeaseCallbackGate,
): SurfaceInteractionLeaseSnapshot | null {
  if (snapshot.token !== capturedSurfaceToken) return null;
  if (!isChromeFragmentAllowed(snapshot)) return snapshot;
  return finalizeSnapshot(
    {
      ...snapshot,
      chromeFragment: fragment,
      chromeFragmentToken: fragmentToken,
    },
    gate,
  );
}

export function unregisterChromeCompatibilityFragment(
  snapshot: SurfaceInteractionLeaseSnapshot,
  capturedSurfaceToken: symbol,
  fragmentToken: symbol,
  gate: LeaseCallbackGate,
): SurfaceInteractionLeaseSnapshot | null {
  if (snapshot.token !== capturedSurfaceToken) return null;
  if (!isChromeFragmentAllowed(snapshot)) return snapshot;
  if (snapshot.chromeFragmentToken !== fragmentToken) return snapshot;
  return finalizeSnapshot(
    {
      ...snapshot,
      chromeFragment: null,
      chromeFragmentToken: null,
    },
    gate,
  );
}

export function resolveGuardedToolInvoke(
  publication: SurfaceInteractionPublication | null,
  toolId: string,
): (() => void | Promise<void>) | null {
  if (!publication) return null;
  const tool = publication.tools.find((entry) => entry.id === toolId);
  if (!tool || tool.availability.status !== "enabled") return null;
  if (tool.activation.kind !== "command") return null;
  return tool.activation.invoke;
}

export function resolveGuardedEditInvoke(
  publication: SurfaceInteractionPublication | null,
  editId: string,
): (() => void | Promise<void>) | null {
  if (!publication) return null;
  const command = publication.editCommands.find((entry) => entry.id === editId);
  if (!command || command.availability.status !== "enabled") return null;
  return command.invoke;
}
