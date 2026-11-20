import {useOptionalMarkdownCanvasSession} from '../markdownCanvas/MarkdownCanvasSession';
import type {BuildWorkspaceDocumentController} from './useBuildWorkspaceDocumentController';
import {ConnectedPageReviewControl} from '../shared/ConnectedPageReviewControl';

/** Build supplies its actual editor session and destination activation adapter. */
export function BuildConnectedPageControl(props:{relationshipsHost?:HTMLElement|null;selectDocument:BuildWorkspaceDocumentController['selectDocument'];refreshDocuments:()=>unknown}){
  const session=useOptionalMarkdownCanvasSession();
  return <ConnectedPageReviewControl surface="build" session={session} {...props}/>;
}
