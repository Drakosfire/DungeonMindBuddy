import { createContext } from "react";
import { getAgentNativeAssertionSource } from "../api/liveApi";
import { isNativeAssertionCitationShape } from "../shared/nativeAssertionProtocol";
import { SourceCitationEvidence } from "../planSurface/components/SourceCitationEvidence";
import { parseAssertionPdfCitationId } from "../tiptap/references/runbookReferences";

export const SavedPdfCitationWorld = createContext<string | null>(null);

export function SavedPdfCitation({ worldId, refId, label }: {
  worldId: string;
  refId: string;
  label: string;
}) {
  const selector = parseAssertionPdfCitationId(refId);
  if (!selector) return label;
  return <SourceCitationEvidence identity={`${worldId}:${refId}`} statements={[{choices:[{
    key:refId, number:0, buttonText:label, title:label, label, kind:"section", load:async()=>{
      const result = await getAgentNativeAssertionSource(worldId, selector.turnId, selector.citationIndex);
      if (result.schema !== "dmb_native_assertion_pdf_source_read_v1"
          || result.world_id !== worldId || result.turn_id !== selector.turnId
          || result.citation_index !== selector.citationIndex
          || !isNativeAssertionCitationShape(result.citation) || !("region" in result.citation)
          || result.citation.managed_world_id !== worldId
          || typeof result.png_base64 !== "string" || !result.png_base64.startsWith("iVBORw0KGgo")) {
        throw new Error("Saved PDF citation binding differs");
      }
      return {pngBase64:result.png_base64,title:`${label} · page ${result.citation.region.page}`};
    },
  }]}]} />;
}
