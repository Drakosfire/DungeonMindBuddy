import type {WorldPlayRunRecordV2} from '../api/types';
import {useTourOwnerReading} from './GuidedTour';
import {samePin} from './protocol';
import {runPins} from './ownerPins';
export interface RecordedRollReceipt {
 world_id:string;run_id:string;command_id:string;
 source:Pick<WorldPlayRunRecordV2,'playable_artifact_id'|'playable_revision'|'playable_work_revision_id'|'playable_content_sha256'>;
 table_id:string;table_sha256:string;die_sides:number;physical_value:number;row_id:string;recorded_at:string;expected_run_revision:number;resulting_run_revision:number;
}
export interface AcknowledgedRoll {receipt:RecordedRollReceipt;run:WorldPlayRunRecordV2}
/** Only the table owner supplies receipts after validating the exact entered-value command. */
export function RecordedRollTourObservation({run,history,acknowledged,blocked,error}:{run:WorldPlayRunRecordV2;history:RecordedRollReceipt[];acknowledged:AcknowledgedRoll|null;blocked:boolean;error:string|null}){
 const fresh=!!acknowledged&&acknowledged.run.world_id===run.world_id&&acknowledged.run.run_id===run.run_id&&samePin(runPins(acknowledged.run).parent,runPins(run).parent);
 const receipt=fresh?acknowledged.receipt:history[0],basis=fresh?acknowledged.run:run;
 const pins=runPins(basis);
 const usable=!!receipt&&!blocked&&!error&&receipt.world_id===run.world_id&&receipt.run_id===run.run_id&&basis.run_revision>=receipt.resulting_run_revision
  &&receipt.source.playable_artifact_id===pins.parent.objectId&&receipt.source.playable_revision===pins.parent.revision&&receipt.source.playable_work_revision_id===pins.parent.revisionId&&receipt.source.playable_content_sha256===pins.parent.digest
  &&Number.isSafeInteger(receipt.die_sides)&&receipt.die_sides>0&&Number.isSafeInteger(receipt.physical_value)&&receipt.physical_value>=1&&receipt.physical_value<=receipt.die_sides;
 const target=usable?{...pins.target,revision:receipt.resulting_run_revision}:pins.target;
 useTourOwnerReading({step:'roll',target,parent:pins.parent,control:'roll',status:error?'failed':usable?'ready':'unavailable',reason:error??(usable?undefined:blocked?'Resolve pending session work or the retained roll command.':'Enter your physical die result through Prepared tables. Opening a table or generating a random value does not record a supplied roll.'),
  ...(usable?{observation:{step:'roll',target,parent:pins.parent,origin:fresh?'acknowledged':'existing',observedAt:receipt.recorded_at,receiptId:`roll:${receipt.command_id}`,proof:{kind:'recorded-roll',commandId:receipt.command_id,tableId:receipt.table_id,tableDigest:receipt.table_sha256,dieSides:receipt.die_sides,physicalValue:receipt.physical_value,rowId:receipt.row_id,expectedRunRevision:receipt.expected_run_revision,resultingRunRevision:receipt.resulting_run_revision}}}:{})});
 return null;
}
