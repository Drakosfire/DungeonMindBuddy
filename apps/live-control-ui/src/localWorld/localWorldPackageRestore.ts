import { cloneLocalWorldValue, validateLocalWorldSnapshot } from "./localWorldRepository";
import type { LocalWorldPackageData, LocalWorldPackageRepository, LocalWorldRecord } from "./localWorldRepository";
import { parseLocalWorldPackageV1, type StagedLocalWorldPackageV1 } from "./localWorldPackageV1";

export type RestoreStagedPackageResult =
  | { readonly status: "restored"; readonly record: LocalWorldRecord }
  | { readonly status: "collision" }
  | { readonly status: "error"; readonly message: string };

/** Revalidates staged bytes, then asks the repository to atomically add record and attachments. */
export async function restoreStagedLocalWorldPackage(
  repository: LocalWorldPackageRepository,
  staged: StagedLocalWorldPackageV1,
): Promise<RestoreStagedPackageResult> {
  // Capture caller-controlled map contents synchronously before parsing awaits.
  let members: Map<string, Uint8Array>;
  try {
    members = new Map([...staged.members].map(([path, bytes]) => [path, new Uint8Array(bytes)]));
  } catch {
    return { status: "error", message: "The staged package members could not be copied safely." };
  }
  const parsed = await parseLocalWorldPackageV1(members);
  if (parsed.status !== "staged") return { status: "error", message: parsed.message };
  const candidate = parsed.candidate;
  const worldId = candidate.record.snapshot.worldId;
  const invalidSnapshot = validateLocalWorldSnapshot(candidate.record.snapshot, worldId);
  if (invalidSnapshot) return { status: "error", message: invalidSnapshot };

  const bundledMembers: Record<string, number[]> = {};
  const refs = [...candidate.documents, ...candidate.assets];
  for (const ref of refs) {
    if (ref.status !== "bundled") continue;
    if (!ref.path) return { status: "error", message: "A bundled attachment has no member path." };
    const bytes = candidate.members.get(ref.path);
    if (!bytes) return { status: "error", message: `Bundled attachment ${ref.path} is missing.` };
    bundledMembers[ref.path] = Array.from(bytes);
  }
  const data: LocalWorldPackageData = {
    localWorldId: worldId,
    documents: cloneLocalWorldValue(candidate.documents),
    assets: cloneLocalWorldValue(candidate.assets),
    bundledMembers,
    fidelity: cloneLocalWorldValue(candidate.manifest.fidelity),
    creatorProfileAssumptions: cloneLocalWorldValue(candidate.manifest.creatorProfileAssumptions),
  };
  return repository.restorePackage(cloneLocalWorldValue(candidate.record), data);
}
