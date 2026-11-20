import {inspectNativeGraph} from '../../api/liveApi';
import {sameInspectionPin} from '../../api/nativeGraphInspection';
import type {SavedStatblockPdfSources} from '../../api/conversationLibraryApi';
import {SourceCitationEvidence, type CitationChoice} from './SourceCitationEvidence';

export function SavedStatblockPdfEvidence({sources}: {sources: SavedStatblockPdfSources}) {
  const choices = sources.support.map((source, index): CitationChoice => ({
    key: source.evidence_ref_id,
    number: index + 1,
    buttonText: `Open PDF region ${index + 1}`,
    title: 'Reviewed statblock PDF source',
    label: 'Open reviewed PDF region',
    kind: 'passage',
    load: async () => {
      const result = await inspectNativeGraph(sources.scope, {kind: 'source', ...source});
      if (result.schema !== 'dmb_native_graph_pdf_region_v1'
        || !sameInspectionPin(result.scope, sources.scope)
        || result.evidence_ref_id !== source.evidence_ref_id
        || !/^[A-Za-z0-9+/]+={0,2}$/.test(result.png_base64)) {
        throw new Error('PDF source unavailable');
      }
      return {title: `PDF evidence · Page ${result.region.page}`, pngBase64: result.png_base64};
    },
  }));
  return choices.length > 0 && <details>
    <summary>Reviewed statblock PDF sources</summary>
    <SourceCitationEvidence identity={JSON.stringify(sources)} statements={[{choices}]}/>
  </details>;
}
