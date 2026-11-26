import {inspectNativeGraph} from '../../api/liveApi';
import {sameInspectionPin} from '../../api/nativeGraphInspection';
import type {SavedStatblockPdfSources} from '../../api/conversationLibraryApi';
import {SourceCitationEvidence, type CitationChoice} from './SourceCitationEvidence';

export function SavedStatblockPdfEvidence({sources}: {sources: SavedStatblockPdfSources}) {
  const stored = sources.support.filter(source => source.evidence_ref_id.startsWith('ev:'));
  const choices = stored.map((source, index): CitationChoice => ({
    key: source.evidence_ref_id,
    number: index + 1,
    buttonText: `Open stored passage ${index + 1}`,
    title: 'Reviewed statblock passage',
    label: 'Open reviewed passage',
    kind: 'passage',
    load: async () => {
      const result = await inspectNativeGraph(sources.scope, {kind: 'source', ...source});
      if (result.schema !== 'dmb_native_graph_source_v1'
        || !sameInspectionPin(result.scope, sources.scope)) {
        throw new Error('Stored passage unavailable');
      }
      return {title: 'Reviewed statblock passage', content: result.source.text};
    },
  }));
  return sources.support.length > 0 && <details>
    <summary>Reviewed statblock sources</summary>
    {stored.length < sources.support.length && <p>Some reviewed passages are unavailable in stored text.</p>}
    <SourceCitationEvidence identity={JSON.stringify(sources)} statements={[{choices}]}/>
  </details>;
}
