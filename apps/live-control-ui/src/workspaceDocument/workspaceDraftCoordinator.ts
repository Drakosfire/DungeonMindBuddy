import {workspaceDocumentStorageKey, type WorkspaceDocumentLocalState} from '../tiptap/state/tiptapLocalState';
import {appendDraftRecoveryCopies, writeVerifiedDraftBytes} from './workspaceDocumentRecovery';

type DraftStorage = Pick<Storage, 'getItem'|'setItem'|'removeItem'>;
export interface DraftPersistenceStatus {pending: boolean; error: string|null}
export const workspaceDraftLock = (id: string) => `dmb:workspace-draft:${id}`;

/** One admitted hook owner; every source-key mutation uses this shared document lock. */
export class WorkspaceDraftCoordinator {
  private tail: Promise<unknown> = Promise.resolve();
  private pending = 0;
  private expected: string|null;
  private error: string|null = null;
  constructor(private storage: DraftStorage, readonly documentId: string,
    private changed: (status: DraftPersistenceStatus)=>void) {
    this.expected = null;
  }
  get status(): DraftPersistenceStatus {return {pending: this.pending > 0, error: this.error};}
  private notify() {this.changed(this.status);}
  settled(): Promise<void> {return this.tail.then(()=>{},()=>{});}
  drain(): Promise<void> {return this.tail.then(()=>{if(this.error)throw new Error(this.error);});}
  run<T>(operation: ()=>T, options: {expectedRaw?: string|null; guard?: ()=>boolean; refusedSnapshot?: WorkspaceDocumentLocalState | (() => WorkspaceDocumentLocalState); preserveAdmission?: boolean} = {}): Promise<T|undefined> {
    this.pending++;this.notify();
    const task = this.tail.catch(()=>{}).then(async()=>{
      if (!navigator.locks) throw new Error('This browser cannot coordinate safe draft writes. Your working copy is still here.');
      return navigator.locks.request(workspaceDraftLock(this.documentId), ()=>{
        if(options.guard && !options.guard())return undefined;
        const expected = Object.hasOwn(options,'expectedRaw') ? options.expectedRaw! : this.expected;
        if(this.storage.getItem(workspaceDocumentStorageKey(this.documentId)) !== expected) {
          const snapshot = typeof options.refusedSnapshot === 'function' ? options.refusedSnapshot() : options.refusedSnapshot;
          if(snapshot)appendDraftRecoveryCopies(this.storage,this.documentId,[{label:'Unwritten working draft',state:snapshot}]);
          throw new Error('The browser draft changed in another tab. Reopen or review retained copies before replacing it.');
        }
        const result = operation();
        if(!options.preserveAdmission){this.expected = this.storage.getItem(workspaceDocumentStorageKey(this.documentId));this.error = null;}
        return result;
      });
    }).catch(error=>{
      this.error = error instanceof Error ? error.message : 'The browser draft could not be verified.';
      throw error;
    }).finally(()=>{this.pending--;this.notify();});
    this.tail = task;
    return task;
  }
  write(state: WorkspaceDocumentLocalState, guard?: ()=>boolean, expectedRaw?: string|null): Promise<void> {
    // Snapshot before queuing; unmount never turns this into a read of another page.
    const documentId = state.document_id;
    const raw = JSON.stringify(state);
    const captured = () => JSON.parse(raw) as WorkspaceDocumentLocalState;
    const options = arguments.length > 2 ? {guard,expectedRaw,refusedSnapshot:captured} : {guard,refusedSnapshot:captured};
    return this.run(()=>writeVerifiedDraftBytes(this.storage,documentId,raw),options).then(()=>{});
  }

  clear(guard?: ()=>boolean): Promise<void> {
    return this.run(()=>{
      if(guard && !guard())throw new Error('The draft changed before discard. Keep editing or review again.');
      const key=workspaceDocumentStorageKey(this.documentId);this.storage.removeItem(key);
      if(this.storage.getItem(key)!==null)throw new Error('Browser storage did not verify the discarded draft.');
    }).then(()=>{});
  }
}
