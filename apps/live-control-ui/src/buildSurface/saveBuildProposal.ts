import type {SavedProposalProjection} from './buildComposeBridge';
import type {BuildProposalBasis,BuildProseBoundaryTarget} from '../api/buildDocumentProposalApi';
import {getCommittedPageSnapshot} from '../api/liveApi';
import type {MarkdownCanvasSessionValue} from '../markdownCanvas/markdownCanvasTypes';
import {tiptapJsonToSemanticMarkdown} from '../tiptap/markdown/calloutMarkdown';
import {preserveLeadingYamlFrontmatter} from '../tiptap/markdown/stripLeadingYamlFrontmatter';
import {flattenPresentation,hasPresentation,hydratePresentation,presentationFingerprint,projectPresentation} from '../tiptap/pageComposer/presentation';
import {markdownToTiptapDoc} from '../tiptap/markdown/markdownToTiptap';

type SaveOwner=Pick<MarkdownCanvasSessionValue,'documentId'|'editor'|'snapshot'|'saveMarkdown'>;
async function digest(value:string){
  return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(value))),byte=>byte.toString(16).padStart(2,'0')).join('');
}
/** Confirm through the existing page save owner, never by a resolved void promise alone. */
export async function saveBuildProposal(getCurrent:()=>SaveOwner|null,basis:BuildProposalBasis,afterEditor:string,afterDraft:string,
  savedProjection?:SavedProposalProjection,proseTarget?:BuildProseBoundaryTarget):Promise<void>{
  savedProjection?.assertCurrent();
  const owner=getCurrent();const editor=owner?.editor;const snapshot=owner?.snapshot;
  if(!owner||!editor||editor.isDestroyed||!snapshot||owner.documentId!==basis.document_id
    ||snapshot.record.document_id!==basis.document_id||snapshot.record.world_id!==basis.world_id)
    throw new Error('Open the original page to finish saving this insertion.');
  const documentId=owner.documentId;
  const doc=editor.getJSON(),json=JSON.stringify(doc);
  const body=tiptapJsonToSemanticMarkdown(proseTarget ? flattenPresentation(doc) : doc);
  const markdown=preserveLeadingYamlFrontmatter(snapshot.markdown,body);
  let expectedLayoutHash: string | null | undefined;
  if (proseTarget) {
    const retained = snapshot.page_presentation?.items.every(item => item.kind === 'block') === true;
    const original = snapshot.page_presentation ? hydratePresentation(snapshot.markdown, snapshot.page_presentation)
      : markdownToTiptapDoc(snapshot.markdown).doc;
    const presentation = retained || hasPresentation(doc)
      ? projectPresentation(doc, snapshot.markdown, original, snapshot.page_presentation, retained).presentation : null;
    expectedLayoutHash = presentationFingerprint(presentation);
  }
  const [editorSha,bodySha,fullSha]=await Promise.all([digest(json),digest(body),digest(markdown)]);
  const current=getCurrent();
  if(!current||current.documentId!==documentId||current.editor!==editor||editor.isDestroyed
    ||JSON.stringify(editor.getJSON())!==json||current.snapshot!==snapshot||(savedProjection?editorSha!==savedProjection.editorSha256:editorSha!==afterEditor)||bodySha!==afterDraft)
    throw new Error('The page changed before saving. Your working copy and insertion receipt are retained.');
  savedProjection?.assertCurrent();
  if(savedProjection && snapshot.content_sha256!==fullSha)throw new Error("The intended insertion is not already saved. No page write was attempted.");
  // Reload after a committed save/lost acknowledgment must not issue another write.
  if(!savedProjection && snapshot.content_sha256!==fullSha)await current.saveMarkdown();
  const saved=await getCommittedPageSnapshot(basis.document_id);
  savedProjection?.assertCurrent();
  const now=getCurrent();
  if(!now||now.documentId!==documentId||now.editor!==editor||editor.isDestroyed)
    throw new Error('The page changed while saving. Reopen it to check the saved insertion.');
  if(savedProjection && (now.snapshot!==snapshot||JSON.stringify(editor.getJSON())!==json
    ||saved.loaded_revision!==snapshot.loaded_revision||!saved.file_fingerprint))
    throw new Error('The page changed during saved insertion verification. Check it again.');
  if(saved.record.document_id!==basis.document_id||saved.record.world_id!==basis.world_id
    ||(expectedLayoutHash!==undefined && (saved.page_presentation_sha256??null)!==expectedLayoutHash)
    ||saved.record.content_status!=='committed'||saved.record.status!=='active'
    ||saved.record.visibility_state!==snapshot.record.visibility_state||saved.loaded_revision<basis.registry_revision
    ||saved.record.revision!==saved.loaded_revision||saved.markdown!==markdown||saved.content_sha256!==fullSha)
    throw new Error('The insertion is not verified in the saved page. Your working copy is retained; check the insertion to retry saving.');
  // Newer typing stays in the live editor/local draft; only the exact saved result is acknowledged.
}
