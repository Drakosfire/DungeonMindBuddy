import {changeConversationLifecycle, type ConversationLifecycleOperation} from '../api/conversationLibraryApi';
import {LiveApiError} from '../api/liveApi';

export type BulkConversationOperation = Extract<ConversationLifecycleOperation, 'trash' | 'restore'>;

export interface BulkConversationTarget {
  conversationId: string;
  title: string;
  commandId: string;
}

export interface BulkConversationPlan {
  worldId: string;
  operation: BulkConversationOperation;
  pointer: { revision: number; activeId: string | null };
  targets: readonly BulkConversationTarget[];
}

export interface BulkConversationResult {
  applied: BulkConversationTarget[];
  failed: { target: BulkConversationTarget; reason: string }[];
  stopped: BulkConversationTarget[];
  retry: BulkConversationPlan | null;
}

/** Execute existing pointer-checked commands serially. An unconfirmed result
 * must be retried with the same target, command ID, and expected pointer. */
export async function runBulkConversationLifecycle(
  plan: BulkConversationPlan,
  isCurrent: () => boolean,
  change = changeConversationLifecycle,
): Promise<BulkConversationResult> {
  const result: BulkConversationResult = {applied: [], failed: [], stopped: [], retry: null};
  let pointer = plan.pointer;
  for (const [index, target] of plan.targets.entries()) {
    if (!isCurrent()) {
      result.stopped = plan.targets.slice(index);
      break;
    }
    try {
      const receipt = await change({
        world_id: plan.worldId,
        conversation_id: target.conversationId,
        command_id: target.commandId,
        expected_pointer_revision: pointer.revision,
        expected_active_conversation_id: pointer.activeId,
      }, plan.operation);
      result.applied.push(target);
      pointer = {revision: receipt.pointer_revision, activeId: receipt.active_conversation_id};
    } catch (reason) {
      const remaining = plan.targets.slice(index + 1);
      if (reason instanceof LiveApiError && [401, 403, 404, 409, 422].includes(reason.status)) {
        result.failed.push({target, reason: reason.message});
        if (reason.status === 404) continue;
        result.stopped = remaining;
      } else {
        result.stopped = [target, ...remaining];
        result.retry = {...plan, pointer, targets: result.stopped};
      }
      break;
    }
  }
  return result;
}
