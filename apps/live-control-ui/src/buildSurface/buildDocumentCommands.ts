import { DOCUMENT_SAVE_COMMAND_ID } from "../markdownCanvas/markdownCanvasTypes";

/** Build-owned document command ids. Keep out of markdownCanvas/. */
export const BUILD_EXTRACT_COMMAND_ID = "build.extract";
export const BUILD_REFRESH_RUN_COMMAND_ID = "build.refresh-run";
/** Typed alias of Canvas DOCUMENT_SAVE_COMMAND_ID — Edit Host Save targets Canvas save. */
export const BUILD_DOCUMENT_SAVE_COMMAND_ID = DOCUMENT_SAVE_COMMAND_ID;

export const BUILD_SAVE_CONFLICTS_WITH = [BUILD_EXTRACT_COMMAND_ID] as const;
