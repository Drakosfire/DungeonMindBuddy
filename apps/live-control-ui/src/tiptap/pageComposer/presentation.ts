import type { JSONContent } from "@tiptap/core";
import { parseMarkdownAst } from "../markdown/parseMarkdownAst";
import { markdownToTiptapDoc } from "../markdown/markdownToTiptap";
import { tiptapJsonToSemanticMarkdown } from "../markdown/calloutMarkdown";
import { semanticMarkdownSerializationDiagnostics } from "../markdown/semanticMarkdownSafety";
import { splitLeadingYamlFrontmatter, preserveLeadingYamlFrontmatter } from "../markdown/stripLeadingYamlFrontmatter";
import { MEDIA_ASSET_ID, mediaMarkdown } from "../../media/mediaReferences";
import { presentationSha256 } from "./presentationHash";

export interface PageBlockBinding { kind: "block"; id: string; byte_start: number; byte_end: number; sha256: string }
export const IMAGE_TEXT_ANCHORS = ["top-left", "top-center", "top-right", "middle-left", "middle-center", "middle-right", "bottom-left", "bottom-center", "bottom-right"] as const;
export type ImageTextAnchor = typeof IMAGE_TEXT_ANCHORS[number];
export interface PageImageText { kind: "image_text"; id: string; image: PageBlockBinding; text: PageBlockBinding; anchor: ImageTextAnchor; inset: "none" | "small" | "medium"; backing: "none" | "contrast" }
export type PageSlotBlock = PageBlockBinding | PageImageText;
export interface PageSlot { id: string; width: number; blocks: PageSlotBlock[] }
export interface PageRow { kind: "row"; id: string; slots: PageSlot[]; min_height: number; line_mode: "guide" | "border" | "clean" }
export interface PagePresentation { schema_version: "dmb_page_presentation_v1"; markdown_sha256: string; items: (PageBlockBinding | PageRow | PageImageText)[] }
export { presentationSha256 };
const fail = (reason: string): never => { throw new Error(`Page composition unavailable: ${reason}. The source and draft are unchanged.`); };
const identifier = /^[A-Za-z0-9_-]{1,80}$/;
const encoder = new TextEncoder();
const allowedSource = new Set(["paragraph", "heading", "table", "blockquote", "list", "thematicBreak"]);

/** The stack retains the existing managed image and editable text, never a duplicate. */
export function validateImageTextContent(content: JSONContent[] | undefined): void {
  const [image, text] = content ?? [];
  if (content?.length !== 2 || image?.type !== "paragraph" || image.content?.length !== 1 || image.content[0].type !== "mediaImage") return fail("image/text needs one standalone managed image then one text block");
  const media = image.content[0];
  if (!MEDIA_ASSET_ID.test(String(media.attrs?.assetId ?? "")) || Object.keys(media.attrs ?? {}).some(key => !["assetId","alt","width","collapsed"].includes(key)) || media.content?.length || media.marks?.length) return fail("invalid managed image");
  try { mediaMarkdown(String(media.attrs?.assetId ?? ""), String(media.attrs?.alt ?? ""), media.attrs?.width, media.attrs?.collapsed); }
  catch { return fail("invalid managed image presentation"); }
  if (!text || !["paragraph", "heading"].includes(text.type ?? "") || !text.content?.length
    || text.content.some(child => !["text", "hardBreak"].includes(child.type ?? "") || !!child.content?.length || child.marks?.some(mark => !["bold","italic","code","link"].includes(mark.type)))
    || !text.content.some(child => child.type === "text" && child.text?.trim())
    || semanticMarkdownSerializationDiagnostics({type:"doc",content:[image,text]}).length) return fail("image/text needs a plain editable heading or paragraph");
}

/** Only the owned containers disappear. Unknown editor nodes remain visible to admission. */
export function flattenPresentation(doc: JSONContent): JSONContent {
  function clean(node: JSONContent): JSONContent {
    if (node.type === "pageRow" || node.type === "pageSlot") return fail("nested layout container");
    const result = { ...node };
    if (result.attrs) {
      const { pageBlockId: _id, ...attrs } = result.attrs;
      result.attrs = attrs;
      if (!Object.keys(attrs).length) delete result.attrs;
    }
    if (node.content) result.content = node.content.map(clean);
    return result;
  }
  if (doc.type !== "doc") return fail("expected a document");
  const block = (node: JSONContent): JSONContent[] => {
    if (node.type !== "pageImageText") return [clean(node)];
    // Drafts can contain an empty title while typing. Flatten only the owned
    // wrapper here; project/hydrate enforce the complete saved stack contract.
    // Unknown children stay intact for semantic safety to protect the draft.
    return (node.content ?? []).map(clean);
  };
  const content = (doc.content ?? []).flatMap(node => {
    if (node.type !== "pageRow") return block(node);
    if (!node.content?.length || node.content.some(slot => slot.type !== "pageSlot")) return fail("invalid row");
    return node.content.flatMap(slot => (slot.content ?? []).flatMap(block));
  });
  return { ...doc, content };
}
export function hasPresentation(doc: JSONContent): boolean { return (doc.content ?? []).some(node => node.type === "pageRow" || node.type === "pageImageText"); }

// Sort keys for comparisons/fingerprints; never normalize source text.
export function presentationCanonicalJson(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(presentationCanonicalJson).join(",")}]`;
  if (value && typeof value === "object") return `{${Object.entries(value).sort(([a],[b]) => a < b ? -1 : a > b ? 1 : 0).map(([k,v]) => `${JSON.stringify(k)}:${presentationCanonicalJson(v)}`).join(",")}}`;
  return JSON.stringify(value);
}
export function presentationFingerprint(value: PagePresentation | null | undefined): string | null {
  return value == null ? null : presentationSha256(presentationCanonicalJson(value));
}
interface AdmittedBlock { node: JSONContent; byte_start: number; byte_end: number; sha256: string }
/** mdast owns structure. Raw slicing only preserves the bytes between its block starts. */
export function admittedPresentationBlocks(markdown: string): AdmittedBlock[] {
  const split = splitLeadingYamlFrontmatter(markdown);
  const body = split.markdown;
  const ast = parseMarkdownAst(body);
  if (!ast.children.length) return fail("add content before making a row");
  if (ast.children.some(node => !allowedSource.has(node.type))) return fail("unsupported source block");
  const whole = markdownToTiptapDoc(markdown);
  if (whole.diagnostics.some(d => d.level === "warning")) return fail("source cannot be edited losslessly");
  const starts = ast.children.map(node => {
    const offset = node.position?.start.offset;
    if (typeof offset !== "number") return fail("source block position missing");
    // Parser positions may start after indentation; backend uses whole-line boundaries.
    let lineStart = offset;
    while (lineStart > 0 && body[lineStart - 1] !== "\n" && body[lineStart - 1] !== "\r") lineStart--;
    return lineStart;
  });
  starts[0] = 0;
  const blocks = starts.map((start,i) => {
    const end = starts[i+1] ?? body.length;
    const slice = body.slice(start,end);
    const imported = markdownToTiptapDoc(slice);
    if (imported.diagnostics.some(d => d.level === "warning") || imported.doc.content?.length !== 1) return fail("block cannot be independently reconstructed");
    const byte_start = encoder.encode(split.frontmatter + body.slice(0,start)).length;
    const byte_end = encoder.encode(split.frontmatter + body.slice(0,end)).length;
    return {node: imported.doc.content[0],byte_start,byte_end,sha256:presentationSha256(slice)};
  });
  if (presentationCanonicalJson(blocks.map(b => b.node)) !== presentationCanonicalJson(whole.doc.content)) return fail("block reconstruction changed content");
  return blocks;
}
export function presentationEligibility(markdown: string): { eligible: boolean; reason: string | null } {
  try { admittedPresentationBlocks(markdown); return {eligible:true,reason:null}; }
  catch (error) { return {eligible:false,reason:error instanceof Error ? error.message : "Source cannot be composed"}; }
}
export function composerDisabledReason(markdown: string): string | null { return presentationEligibility(markdown).reason; }
function object(value: unknown, keys: string[]): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) return fail("invalid presentation object");
  if (Object.keys(value).some(key => !keys.includes(key))) return fail("unknown presentation field");
  return value as Record<string,unknown>;
}
function array(value: unknown, max: number): unknown[] { if (!Array.isArray(value) || value.length > max) return fail("invalid presentation list"); return value; }
function integer(value: unknown, min: number, max: number): number { if (typeof value !== "number" || !Number.isSafeInteger(value) || value < min || value > max) return fail("invalid presentation number"); return value; }
export function hydratePresentation(markdown: string, presentation: PagePresentation | unknown): JSONContent {
  const blocks = admittedPresentationBlocks(markdown);
  const p = object(presentation,["schema_version","markdown_sha256","items"]);
  if (p.schema_version !== "dmb_page_presentation_v1" || p.markdown_sha256 !== presentationSha256(markdown)) return fail("presentation belongs to different source bytes");
  const seen = new Set<string>(); let cursor = 0;
  const identity = (id: unknown) => { if (typeof id !== "string" || !identifier.test(id) || seen.has(id)) return fail("duplicate or invalid block identity"); seen.add(id); return id; };
  const bind = (value: unknown): JSONContent => {
    const b = object(value,["kind","id","byte_start","byte_end","sha256"]);
    const id=identity(b.id), expected=blocks[cursor++];
    if (b.kind !== "block" || !expected || b.byte_start !== expected.byte_start || b.byte_end !== expected.byte_end || b.sha256 !== expected.sha256) return fail("invalid source block binding");
    return {...expected.node,attrs:{...expected.node.attrs,pageBlockId:id}};
  };
  const block = (value: unknown): JSONContent => {
    const item = object(value,["kind","id","byte_start","byte_end","sha256","image","text","anchor","inset","backing"]);
    if (item.kind === "block") return bind(value);
    object(value,["kind","id","image","text","anchor","inset","backing"]);
    if (item.kind !== "image_text") return fail("unknown slot item or nested layout");
    const id=identity(item.id);
    if (!IMAGE_TEXT_ANCHORS.includes(item.anchor as ImageTextAnchor) || !["none","small","medium"].includes(String(item.inset)) || !["none","contrast"].includes(String(item.backing))) return fail("invalid image/text style");
    const content=[bind(item.image),bind(item.text)];
    validateImageTextContent(content);
    return {type:"pageImageText",attrs:{id,anchor:item.anchor,inset:item.inset,backing:item.backing},content};
  };
  const content=array(p.items,2048).map(value => {
    const item=object(value,["kind","id","slots","min_height","line_mode","byte_start","byte_end","sha256","image","text","anchor","inset","backing"]);
    if(item.kind !== "row") return block(value);
    object(value,["kind","id","slots","min_height","line_mode"]);
    const id=identity(item.id); const min_height=integer(item.min_height,0,640);
    if(min_height%8 || !["guide","border","clean"].includes(String(item.line_mode))) return fail("invalid row style");
    const slots=array(item.slots,3); if(slots.length < 1) return fail("row must contain one to three slots");
    let sum=0,count=0;
    const content=slots.map(value => {const slot=object(value,["id","width","blocks"]);const slotId=identity(slot.id),width=integer(slot.width,2,12);sum+=width;const content=array(slot.blocks,2048).map(block);count+=content.length;return {type:"pageSlot",attrs:{id:slotId,width},content};});
    if(sum!==12 || !count) return fail("invalid row widths or empty row");
    return {type:"pageRow",attrs:{id,min_height,line_mode:item.line_mode},content};
  });
  if(cursor!==blocks.length) return fail("presentation omits source blocks");
  return {type:"doc",content};
}

export function projectPresentation(doc: JSONContent, originalMarkdown: string, originalDoc: JSONContent, existingPresentation?: PagePresentation | null, retainPlainIdentities = false): {markdown: string; presentation: PagePresentation | null} {
  const flat=flattenPresentation(doc), originalFlat=flattenPresentation(originalDoc);
  if(semanticMarkdownSerializationDiagnostics(flat).length) return fail("unsupported editor structure");
  const unchanged=presentationCanonicalJson(flat)===presentationCanonicalJson(originalFlat)
    || (semanticMarkdownSerializationDiagnostics(originalFlat).length === 0
      && tiptapJsonToSemanticMarkdown(flat) === tiptapJsonToSemanticMarkdown(originalFlat));
  const markdown=unchanged ? originalMarkdown : preserveLeadingYamlFrontmatter(originalMarkdown,tiptapJsonToSemanticMarkdown(flat));
  const retainIdentities = retainPlainIdentities || (existingPresentation != null && existingPresentation.items.every(item => item.kind === 'block'));
  if (retainIdentities && existingPresentation != null) hydratePresentation(originalMarkdown, existingPresentation);
  if(!hasPresentation(doc) && !retainIdentities) return {markdown,presentation:null};
  const admitted=admittedPresentationBlocks(markdown);
  if(admitted.length !== flat.content?.length) return fail("edited block boundaries cannot be preserved");
  const used=new Set<string>();let serial=0,cursor=0;
  // New blocks must not consume an identity belonging to a later existing block.
  const reserved = new Set<string>(retainIdentities ? (existingPresentation?.items.map(item => item.id) ?? []) : []);
  const reserve = (node: JSONContent) => {
    if (typeof node.attrs?.pageBlockId === 'string') reserved.add(node.attrs.pageBlockId);
    node.content?.forEach(reserve);
  };
  if (retainIdentities) reserve(doc);
  const identity=(candidate:unknown,prefix:string):string => {
    if(typeof candidate==='string' && identifier.test(candidate) && !used.has(candidate)){used.add(candidate);return candidate;}
    if(retainIdentities && candidate != null) return fail('duplicate or invalid retained block identity');
    let id:string;do{id=`${prefix}-${serial++}`;}while(used.has(id) || reserved.has(id));used.add(id);return id;
  };
  const bind=(node:JSONContent):PageBlockBinding=>{const b=admitted[cursor++];if(!b) return fail("missing edited block");return {kind:"block",id:identity(node.attrs?.pageBlockId,"block"),byte_start:b.byte_start,byte_end:b.byte_end,sha256:b.sha256};};
  const block=(node:JSONContent):PageSlotBlock=>{
    if(node.type!=="pageImageText")return bind(node);
    validateImageTextContent(node.content);
    return {kind:"image_text",id:identity(node.attrs?.id,"image-text"),image:bind(node.content![0]),text:bind(node.content![1]),anchor:node.attrs?.anchor,inset:node.attrs?.inset,backing:node.attrs?.backing};
  };
  const items=(doc.content??[]).map((node):PageBlockBinding|PageRow|PageImageText=>{
    if(node.type!=="pageRow") return block(node);
    const id=identity(node.attrs?.id,"row");
    return {kind:"row",id,min_height:node.attrs?.min_height??0,line_mode:node.attrs?.line_mode??"guide",slots:(node.content??[]).map(slot=>({id:identity(slot.attrs?.id,"slot"),width:slot.attrs?.width,blocks:(slot.content??[]).map(block)}))};
  });
  const presentation:PagePresentation={schema_version:"dmb_page_presentation_v1",markdown_sha256:presentationSha256(markdown),items};
  // Reuse the same validation as cold hydration; malformed local wrappers never save.
  hydratePresentation(markdown,presentation);
  return {markdown,presentation};
}
