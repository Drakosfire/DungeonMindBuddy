import {
  BlobReader,
  BlobWriter,
  Uint8ArrayReader,
  ZipReader,
  ZipWriter,
} from "@zip.js/zip.js";
import {
  isLocalWorldPackageMemberPath,
  LOCAL_WORLD_PACKAGE_V1,
  parseLocalWorldPackageV1,
  type ParseLocalWorldPackageV1Result,
} from "./localWorldPackageV1";

export const LOCAL_WORLD_PACKAGE_ZIP_V1 = {
  maxArchiveBytes: 17 * 1024 * 1024,
  maxCentralDirectoryBytes: 256 * (46 + 256),
  maxPathBytes: 256,
  maxPathSegments: 16,
  supportedMethods: [0, 8] as const,
} as const;

export type LocalWorldPackageZipErrorCode = "invalid-archive" | "limit-exceeded" | "invalid-package" | "unsupported-version";
export type EncodeLocalWorldPackageZipV1Result =
  | { readonly status: "encoded"; readonly blob: Blob }
  | { readonly status: "error"; readonly code: LocalWorldPackageZipErrorCode; readonly message: string };
export type DecodeLocalWorldPackageZipV1Result =
  | { readonly status: "staged"; readonly parsed: Extract<ParseLocalWorldPackageV1Result, { status: "staged" }> }
  | { readonly status: "error"; readonly code: LocalWorldPackageZipErrorCode; readonly message: string };

class ZipProblem extends Error {
  constructor(readonly code: LocalWorldPackageZipErrorCode, message: string) { super(message); }
}
const fail = (code: LocalWorldPackageZipErrorCode, message: string): never => { throw new ZipProblem(code, message); };
const utf8 = new TextDecoder("utf-8", { fatal: true });

function safePackagePath(path: string): boolean {
  return path === "manifest.json" || isLocalWorldPackageMemberPath(path);
}

function readU16(view: DataView, offset: number): number { return view.getUint16(offset, true); }
function readU32(view: DataView, offset: number): number { return view.getUint32(offset, true); }

interface CentralEntry {
  name: string;
  nameBytes: Uint8Array;
  flags: number;
  method: number;
  crc32: number;
  compressedSize: number;
  expandedSize: number;
  localOffset: number;
  dataOffset: number;
  endOffset: number;
}

/** Bounded ZIP32 structure check. It reads only the capped tail, central directory, and each local header. */
async function preflight(blob: Blob): Promise<CentralEntry[]> {
  if (blob.size > LOCAL_WORLD_PACKAGE_ZIP_V1.maxArchiveBytes) fail("limit-exceeded", "ZIP archive exceeds the 17 MiB transport limit.");
  if (blob.size < 22) fail("invalid-archive", "ZIP end record is missing.");
  const tailStart = Math.max(0, blob.size - 65_557);
  const tail = new Uint8Array(await blob.slice(tailStart).arrayBuffer());
  const tailView = new DataView(tail.buffer, tail.byteOffset, tail.byteLength);
  let eocd = -1;
  for (let i = tail.length - 22; i >= 0; i -= 1) {
    if (readU32(tailView, i) === 0x06054b50 && i + 22 + readU16(tailView, i + 20) === tail.length) { eocd = i; break; }
  }
  if (eocd < 0) fail("invalid-archive", "ZIP must end with one comment-free ZIP32 end record.");
  const eocdAbsolute = tailStart + eocd;
  const disk = readU16(tailView, eocd + 4);
  const centralDisk = readU16(tailView, eocd + 6);
  const diskCount = readU16(tailView, eocd + 8);
  const count = readU16(tailView, eocd + 10);
  const centralSize = readU32(tailView, eocd + 12);
  const centralOffset = readU32(tailView, eocd + 16);
  const commentLength = readU16(tailView, eocd + 20);
  if (disk || centralDisk || diskCount !== count) fail("invalid-archive", "Multi-disk archives are unsupported.");
  if (commentLength !== 0) fail("invalid-archive", "Archive comments are unsupported.");
  if (count < 1 || count > LOCAL_WORLD_PACKAGE_V1.limits.memberCount) fail("limit-exceeded", "ZIP member count is outside the package limit.");
  if (centralSize > LOCAL_WORLD_PACKAGE_ZIP_V1.maxCentralDirectoryBytes) fail("limit-exceeded", "ZIP central directory exceeds its bounded metadata limit.");
  if (centralOffset + centralSize !== eocdAbsolute || centralOffset > blob.size) fail("invalid-archive", "ZIP central directory bounds are inconsistent.");

  const centralBytes = new Uint8Array(await blob.slice(centralOffset, eocdAbsolute).arrayBuffer());
  const view = new DataView(centralBytes.buffer, centralBytes.byteOffset, centralBytes.byteLength);
  const entries: CentralEntry[] = [];
  const exactNames = new Set<string>();
  const portableNames = new Set<string>();
  let cursor = 0;
  let totalExpanded = 0;
  for (let index = 0; index < count; index += 1) {
    if (cursor + 46 > centralBytes.length || readU32(view, cursor) !== 0x02014b50) fail("invalid-archive", "Central directory entry is truncated or malformed.");
    const flags = readU16(view, cursor + 8);
    const method = readU16(view, cursor + 10);
    const crc32 = readU32(view, cursor + 16);
    const compressedSize = readU32(view, cursor + 20);
    const expandedSize = readU32(view, cursor + 24);
    const nameLength = readU16(view, cursor + 28);
    const extraLength = readU16(view, cursor + 30);
    const entryCommentLength = readU16(view, cursor + 32);
    const startDisk = readU16(view, cursor + 34);
    const localOffset = readU32(view, cursor + 42);
    const end = cursor + 46 + nameLength + extraLength + entryCommentLength;
    if (end > centralBytes.length || nameLength < 1) fail("invalid-archive", "Central directory filename or metadata is truncated.");
    if (extraLength || entryCommentLength) fail("invalid-archive", "ZIP extra fields and per-entry comments are unsupported.");
    if (startDisk !== 0 || localOffset === 0xffff_ffff || compressedSize === 0xffff_ffff || expandedSize === 0xffff_ffff) fail("invalid-archive", "ZIP64 and multi-disk entries are unsupported.");
    if ((flags & 1) || (flags & 8) || (flags & ~(0x800 | 0x6))) fail("invalid-archive", "Encrypted, descriptor-based, or unsupported ZIP flags are rejected.");
    if (method === 0 && (flags & 0x6)) fail("invalid-archive", "Deflate-level flags are invalid for stored ZIP members.");
    if (!(flags & 0x800) && centralBytes.slice(cursor + 46, cursor + 46 + nameLength).some((byte) => byte >= 0x80)) fail("invalid-archive", "Non-ASCII ZIP filenames must be explicitly UTF-8 encoded.");
    if (!(LOCAL_WORLD_PACKAGE_ZIP_V1.supportedMethods as readonly number[]).includes(method)) fail("invalid-archive", `ZIP compression method ${method} is unsupported.`);
    if (method === 0 && compressedSize !== expandedSize) fail("invalid-archive", "Stored ZIP member sizes disagree.");
    const nameBytes = centralBytes.slice(cursor + 46, cursor + 46 + nameLength);
    let name = "";
    try { name = utf8.decode(nameBytes); } catch { fail("invalid-archive", "ZIP filename is not valid UTF-8."); }
    if (nameLength > LOCAL_WORLD_PACKAGE_ZIP_V1.maxPathBytes || name.split("/").length > LOCAL_WORLD_PACKAGE_ZIP_V1.maxPathSegments || !safePackagePath(name)) fail("invalid-archive", "ZIP member path is unsafe or outside package v1.");
    const portable = name.normalize("NFC").toLocaleLowerCase("en-US");
    if (exactNames.has(name) || portableNames.has(portable)) fail("invalid-archive", "ZIP contains duplicate or portable-filesystem-colliding paths.");
    exactNames.add(name); portableNames.add(portable);
    const json = name === "manifest.json" || name === "semantic.json" || name === "layout.json" || name === "history.json";
    const perMemberLimit = json ? LOCAL_WORLD_PACKAGE_V1.limits.jsonMemberBytes : LOCAL_WORLD_PACKAGE_V1.limits.attachmentBytes;
    if (expandedSize > perMemberLimit) fail("limit-exceeded", `ZIP member exceeds its package expansion limit: ${name}`);
    totalExpanded += expandedSize;
    if (totalExpanded > LOCAL_WORLD_PACKAGE_V1.limits.totalBytes) fail("limit-exceeded", "ZIP expanded payload exceeds the 16 MiB package limit.");
    if (compressedSize > LOCAL_WORLD_PACKAGE_ZIP_V1.maxArchiveBytes) fail("limit-exceeded", "ZIP compressed member size exceeds archive limit.");
    entries.push({ name, nameBytes, flags, method, crc32, compressedSize, expandedSize, localOffset, dataOffset: 0, endOffset: 0 });
    cursor = end;
  }
  if (cursor !== centralBytes.length) fail("invalid-archive", "Central directory has unaccounted records or bytes.");
  const ordered = [...entries].sort((a, b) => a.localOffset - b.localOffset);
  let expectedOffset = 0;
  for (const entry of ordered) {
    if (entry.localOffset !== expectedOffset || entry.localOffset + 30 > centralOffset) fail("invalid-archive", "ZIP local records overlap, contain gaps, or are out of bounds.");
    const header = new Uint8Array(await blob.slice(entry.localOffset, entry.localOffset + 30).arrayBuffer());
    const local = new DataView(header.buffer, header.byteOffset, header.byteLength);
    if (readU32(local, 0) !== 0x04034b50) fail("invalid-archive", "Local file header signature is invalid.");
    const localFlags = readU16(local, 6);
    const localMethod = readU16(local, 8);
    const localCrc = readU32(local, 14);
    const localCompressed = readU32(local, 18);
    const localExpanded = readU32(local, 22);
    const localNameLength = readU16(local, 26);
    const localExtraLength = readU16(local, 28);
    if (localExtraLength || localFlags !== entry.flags || localMethod !== entry.method || localCrc !== entry.crc32 || localCompressed !== entry.compressedSize || localExpanded !== entry.expandedSize || localNameLength !== entry.nameBytes.length) {
      fail("invalid-archive", "Local and central ZIP headers disagree or contain extras.");
    }
    const nameAndExtra = new Uint8Array(await blob.slice(entry.localOffset + 30, entry.localOffset + 30 + localNameLength + localExtraLength).arrayBuffer());
    if (nameAndExtra.length !== entry.nameBytes.length || nameAndExtra.some((byte, i) => byte !== entry.nameBytes[i])) fail("invalid-archive", "Local and central ZIP filenames disagree.");
    entry.dataOffset = entry.localOffset + 30 + localNameLength;
    entry.endOffset = entry.dataOffset + entry.compressedSize;
    if (entry.endOffset > centralOffset) fail("invalid-archive", "ZIP entry data overlaps its central directory.");
    expectedOffset = entry.endOffset;
  }
  if (expectedOffset !== centralOffset) fail("invalid-archive", "ZIP has a gap or unrecognized bytes before the central directory.");
  return entries;
}

function mapFromInput(input: ReadonlyMap<string, Uint8Array>): Map<string, Uint8Array> {
  if (!input || typeof input[Symbol.iterator] !== "function") fail("invalid-package", "Package members must be an iterable map.");
  const source = [...input];
  if (source.length > LOCAL_WORLD_PACKAGE_V1.limits.memberCount) fail("limit-exceeded", "Package member count exceeds 256.");
  let total = 0;
  const captured = new Map<string, Uint8Array>();
  for (const [path, value] of source) {
    if (typeof path !== "string" || !safePackagePath(path) || captured.has(path)) fail("invalid-package", "Package contains an invalid or duplicate member path.");
    if (!ArrayBuffer.isView(value) || Object.prototype.toString.call(value) !== "[object Uint8Array]") fail("invalid-package", "Package member data must be Uint8Array.");
    total += value.byteLength;
    if (total > LOCAL_WORLD_PACKAGE_V1.limits.totalBytes) fail("limit-exceeded", "Package exceeds its 16 MiB total byte limit.");
    captured.set(path, Uint8Array.from(value as Uint8Array));
  }
  return captured;
}

export async function encodeLocalWorldPackageZipV1(input: ReadonlyMap<string, Uint8Array>): Promise<EncodeLocalWorldPackageZipV1Result> {
  try {
    const members = mapFromInput(input); // capture all caller-owned bytes before the first await
    const parsed = await parseLocalWorldPackageV1(members);
    if (parsed.status !== "staged") fail(parsed.code === "unsupported-version" ? "unsupported-version" : "invalid-package", parsed.message);
    const writer = new BlobWriter("application/zip");
    const zip = new ZipWriter(writer, { zip64: false, dataDescriptor: false, extendedTimestamp: false, useUnicodeFileNames: true, level: 0, useCompressionStream: false, useWebWorkers: false });
    for (const [path, bytes] of [...members].sort(([a], [b]) => a.localeCompare(b))) {
      await zip.add(path, new Uint8ArrayReader(bytes), { compressionMethod: 0, dataDescriptor: false, extendedTimestamp: false, useUnicodeFileNames: true });
    }
    await zip.close();
    const blob = await writer.getData();
    if (blob.size > LOCAL_WORLD_PACKAGE_ZIP_V1.maxArchiveBytes) fail("limit-exceeded", "Encoded ZIP exceeds the 17 MiB archive limit.");
    return { status: "encoded", blob };
  } catch (error) {
    const problem = error instanceof ZipProblem ? error : new ZipProblem("invalid-package", error instanceof Error ? error.message : "ZIP encoding failed.");
    return { status: "error", code: problem.code, message: problem.message };
  }
}

export async function decodeLocalWorldPackageZipV1(blob: Blob): Promise<DecodeLocalWorldPackageZipV1Result> {
  let zip: ZipReader<Blob> | undefined;
  try {
    const expected = await preflight(blob); // bounded metadata checks precede library entry parsing/inflation
    zip = new ZipReader(new BlobReader(blob), { strictness: "strict", filenameValidation: "strict", checkCrc32: true, checkOverlappingEntry: true, useWebWorkers: false });
    const entries = await zip.getEntries();
    if (entries.length !== expected.length) fail("invalid-archive", "ZIP entry count changed between preflight and strict parsing.");
    const expectedByName = new Map(expected.map((entry) => [entry.name, entry]));
    const members = new Map<string, Uint8Array>();
    let streamedTotal = 0;
    for (const entry of entries) {
      if (entry.directory) throw new ZipProblem("invalid-archive", "Directory members are unsupported.");
      const meta = expectedByName.get(entry.filename);
      if (!meta) throw new ZipProblem("invalid-archive", "ZIP parsed a member absent from bounded preflight.");
      if (meta.expandedSize !== entry.uncompressedSize || meta.compressedSize !== entry.compressedSize || meta.method !== entry.compressionMethod) fail("invalid-archive", "ZIP parsed metadata differs from bounded preflight.");
      const chunks: Uint8Array[] = [];
      let entryTotal = 0;
      const sink = new WritableStream<Uint8Array>({
        write(chunk) {
          const bytes = new Uint8Array(chunk);
          entryTotal += bytes.byteLength;
          streamedTotal += bytes.byteLength;
          const json = meta.name === "manifest.json" || meta.name === "semantic.json" || meta.name === "layout.json" || meta.name === "history.json";
          const limit = json ? LOCAL_WORLD_PACKAGE_V1.limits.jsonMemberBytes : LOCAL_WORLD_PACKAGE_V1.limits.attachmentBytes;
          if (entryTotal > limit || streamedTotal > LOCAL_WORLD_PACKAGE_V1.limits.totalBytes) throw new ZipProblem("limit-exceeded", "Inflated ZIP output exceeded a package byte limit.");
          chunks.push(bytes);
        },
      });
      await entry.getData(sink);
      if (entryTotal !== meta.expandedSize) fail("invalid-archive", `Inflated length disagrees with ZIP metadata: ${meta.name}`);
      const combined = new Uint8Array(entryTotal);
      let offset = 0;
      for (const chunk of chunks) { combined.set(chunk, offset); offset += chunk.byteLength; }
      members.set(meta.name, combined);
    }
    const parsed = await parseLocalWorldPackageV1(members);
    if (parsed.status !== "staged") throw new ZipProblem(parsed.code === "unsupported-version" ? "unsupported-version" : "invalid-package", parsed.message);
    return { status: "staged", parsed };
  } catch (error) {
    const problem = error instanceof ZipProblem ? error : new ZipProblem("invalid-archive", error instanceof Error ? error.message : "ZIP decoding failed.");
    return { status: "error", code: problem.code, message: problem.message };
  } finally {
    await zip?.close().catch(() => undefined);
  }
}
