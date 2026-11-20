import type {ReactNode} from 'react';
import {useWorldAgentConversationState} from '../agentInteraction/WorldAgentConversation';
import {GuidedTourProvider} from './GuidedTour';
/** Read-only bridge to the conversation owner's accepted history projection. */
export function WorldGuidedTour({worldId,worldName,children}:{worldId:string|null;worldName?:string;children:ReactNode}){
 const conversation=useWorldAgentConversationState();
 return <GuidedTourProvider worldId={worldId} worldName={worldName} history={conversation?.history??null}>{children}</GuidedTourProvider>;
}
