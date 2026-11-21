export type SavedExample = { version: "owner_saved_scene_v1"; title: string; body: string;
  references: string[]; image: null | { id: string; description: string } };

/** Absence is an old copy; a malformed present example must not be approved. */
export function isSavedExample(value: unknown, sources: { id: string }[], assets: { id: string }[]): value is SavedExample {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const item = value as Record<string, unknown>;
  const keys = Object.keys(item).sort().join(",");
  if (keys !== "body,image,references,title,version" || item.version !== "owner_saved_scene_v1"
    || typeof item.title !== "string" || !item.title.trim() || item.title.length > 120
    || typeof item.body !== "string" || !item.body.trim() || item.body.length > 10000
    || !Array.isArray(item.references) || item.references.length < 2 || item.references.length > 10
    || new Set(item.references).size !== item.references.length
    || !item.references.every(id => typeof id === "string" && sources.some(source => source.id === id))) return false;
  if (item.image === null) return true;
  if (!item.image || typeof item.image !== "object" || Array.isArray(item.image)) return false;
  const image = item.image as Record<string, unknown>;
  return Object.keys(image).sort().join(",") === "description,id" && typeof image.id === "string"
    && assets.some(asset => asset.id === image.id) && typeof image.description === "string"
    && image.description.trim().length > 0 && image.description.length <= 240;
}
