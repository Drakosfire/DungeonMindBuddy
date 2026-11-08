import { cloneLocalWorldValue, validateLocalWorldSnapshot } from "./localWorldRepository";
import type { LocalWorldPackageData, LocalWorldPackageRepository, LocalWorldRecord } from "./localWorldRepository";
import {
  LOCAL_WORLD_PACKAGE_V1,
  parseLocalWorldPackageV1,
  validateLocalWorldPackageMemberPaths,
  type StagedLocalWorldPackageV1,
} from "./localWorldPackageV1";

export type RestoreStagedPackageResult =
  | { readonly status: "restored"; readonly record: LocalWorldRecord }
  | { readonly status: "collision" }
  | { readonly status: "error"; readonly message: string };

/** Revalidates staged bytes, then asks the repository to atomically add record and attachments. */
export async function restoreStagedLocalWorldPackage(
  repository: LocalWorldPackageRepository,
  staged: StagedLocalWorldPackageV1,
): Promise<RestoreStagedPackageResult> {
  // Bound the map before cloning: a forged/mutated staged object must not make
  // restore allocate unbounded attachment copies before the parser checks it.
  if (!staged || !(staged.members instanceof Map)) {
    return { status: "error", message: "The staged package member map is unavailable or unsupported." };
  }
  const limits = LOCAL_WORLD_PACKAGE_V1.limits;
  if (staged.members.size < 1 || staged.members.size > limits.memberCount) {
    return { status: "error", message: "The staged package member count is outside the package limit." };
  }
  let boundedBytes = 0;
  const paths: string[] = [];
  for (const [path, bytes] of staged.members) {
    if (typeof path !== "string" || !(bytes instanceof Uint8Array)) {
      return { status: "error", message: "The staged package contains an invalid member." };
    }
    const perMemberLimit = path.startsWith("documents/") || path.startsWith("assets/")
      ? limits.attachmentBytes
      : limits.jsonMemberBytes;
    if (bytes.byteLength > perMemberLimit) return { status: "error", message: `Package member exceeds its size limit: ${path}` };
    boundedBytes += bytes.byteLength;
    if (boundedBytes > limits.totalBytes) return { status: "error", message: "The staged package exceeds the total byte limit." };
    paths.push(path);
  }
  const pathError = validateLocalWorldPackageMemberPaths(paths);
  if (pathError) return { status: "error", message: pathError };

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
