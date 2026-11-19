import {authenticatedApiFetch} from './liveApi';
import {ExtractPromoteApiError} from './extractPromoteApi';
import type {ExtractPromoteErrorBody, FirstWorldDisposition} from './types';
import type {FirstWorldPublicationReceipt, FirstWorldPublicationRequest, NativeFirstWorldPlan} from './nativeFirstWorldPublicationTypes';

async function post<T>(path: string, body: unknown): Promise<T> {
  const {response} = await authenticatedApiFetch(path, {method: 'POST', body: JSON.stringify(body)});
  let payload: unknown;
  try { payload = JSON.parse(await response.text()); }
  catch { throw new ExtractPromoteApiError(`Invalid publication response (HTTP ${response.status}). Recover the saved request.`, response.status); }
  if (!response.ok) {
    const detail = payload as ExtractPromoteErrorBody | null;
    throw new ExtractPromoteApiError(detail?.message || `Publication failed (HTTP ${response.status}).`, response.status, detail?.code ?? null, detail);
  }
  return payload as T;
}
export function prepareNativeFirstWorld(input: {runId: string; decisions: FirstWorldDisposition[]}): Promise<NativeFirstWorldPlan> {
  return post('/api/live/extract-promote/worldbuilding/first-world/prepare', {
    schema: 'dmb_native_first_world_prepare_request_v1', runId: input.runId, decisions: input.decisions,
  });
}
/** The retained versioned request is sent intact; retries never prepare again. */
export function confirmNativeFirstWorld(request: FirstWorldPublicationRequest): Promise<FirstWorldPublicationReceipt> {
  return post('/api/live/extract-promote/worldbuilding/first-world/confirm', request);
}
