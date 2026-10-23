import type {StatblockDefinitionV1_Input,StatblockRevisionResourceV1} from '../../contracts/dungeonbuddy-statblocks-v1/client';
export interface SavedMechanicsLocator {provider:'dungeonmind';statblock_id:string;revision_id:string;contract:string;contract_version:string;definition_digest:string}
export interface RevisionSaveIntent {operation_id:string;world_id:string;base:SavedMechanicsLocator;definition:StatblockDefinitionV1_Input;change_summary:string}
export interface RevisionSaveOutcome {operation_id:string;state:'prepared'|'outcome_unknown'|'committed'|'refused';base:SavedMechanicsLocator;result:SavedMechanicsLocator|null;refusal_code:string|null;change_summary:string;created_at:string}
export interface SavedMechanicsVersionList {world_id:string;draft_id:string;name:string;original:SavedMechanicsLocator;operations:RevisionSaveOutcome[];pending:RevisionSaveOutcome|null;next_offset:number|null}
export interface OpenSavedMechanicsVersion {world_id:string;draft_id:string;locator:SavedMechanicsLocator;resource:StatblockRevisionResourceV1}
