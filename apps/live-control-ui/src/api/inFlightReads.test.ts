import { afterEach, describe, expect, it, vi } from "vitest";
import { getReadWaveVersion, subscribeReadWave, shareInFlightRead, startReadWave } from "./inFlightReads";
function deferred<T>() { let resolve!:(value:T)=>void;let reject!:(error:unknown)=>void;const promise=new Promise<T>((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject}; }
afterEach(startReadWave);
describe("pending read ownership",()=>{
 it("cancels one subscriber without cancelling the other",async()=>{
  const a=new AbortController(),b=new AbortController(),gate=deferred<string>();let owned!:AbortSignal;
  const loader=vi.fn((signal:AbortSignal)=>{owned=signal;return gate.promise;});
  const first=shareInFlightRead("k",loader,a.signal).catch(error=>error.name);const second=shareInFlightRead("k",loader,b.signal);
  await Promise.resolve();a.abort();expect(await first).toBe("AbortError");expect(owned.aborted).toBe(false);gate.resolve("ok");expect(await second).toBe("ok");expect(loader).toHaveBeenCalledTimes(1);
 });
 it("aborts the last owner's transport and permits a fresh acquisition",async()=>{
  const controller=new AbortController(),gate=deferred<string>();let owned!:AbortSignal;
  const first=shareInFlightRead("k",signal=>{owned=signal;return gate.promise;},controller.signal).catch(error=>error.name);
  await Promise.resolve();controller.abort();expect(await first).toBe("AbortError");expect(owned.aborted).toBe(true);
  expect(await shareInFlightRead("k",async()=>"fresh")).toBe("fresh");gate.resolve("late");
 });
 it("does not let an old wave completion erase the new wave's pending read",async()=>{
  const old=deferred<string>(),fresh=deferred<string>();const a=shareInFlightRead("k",()=>old.promise);startReadWave();const loader=vi.fn(()=>fresh.promise);const b=shareInFlightRead("k",loader);
  old.resolve("old");await a;const c=shareInFlightRead("k",loader);fresh.resolve("fresh");expect(await Promise.all([b,c])).toEqual(["fresh","fresh"]);expect(loader).toHaveBeenCalledTimes(1);
 });
 it("releases both success and error instead of serving settled knowledge",async()=>{
  const loader=vi.fn().mockResolvedValueOnce("v1").mockRejectedValueOnce(new Error("failed")).mockResolvedValueOnce("v2");
  expect(await shareInFlightRead("k",loader)).toBe("v1");await expect(shareInFlightRead("k",loader)).rejects.toThrow("failed");expect(await shareInFlightRead("k",loader)).toBe("v2");expect(loader).toHaveBeenCalledTimes(3);
 });
 it("never dispatches a read already cancelled by its only owner",async()=>{
  const controller=new AbortController();controller.abort();const loader=vi.fn();await expect(shareInFlightRead("k",loader,controller.signal)).rejects.toMatchObject({name:"AbortError"});expect(loader).not.toHaveBeenCalled();
 });
});

it("publishes every authority/read wave and releases observers", () => {
 const listener=vi.fn(), initial=getReadWaveVersion(), unsubscribe=subscribeReadWave(listener);
 startReadWave(); expect(getReadWaveVersion()).toBe(initial+1); expect(listener).toHaveBeenCalledTimes(1);
 unsubscribe();startReadWave();expect(getReadWaveVersion()).toBe(initial+2);expect(listener).toHaveBeenCalledTimes(1);
});

it("reports a failed observer without breaking transport waves or other owners", () => {
 const failure=new Error("broken observer"), log=vi.spyOn(console,"error").mockImplementation(()=>undefined), good=vi.fn();
 const releaseBad=subscribeReadWave(()=>{throw failure;}), releaseGood=subscribeReadWave(good);
 try { expect(()=>startReadWave()).not.toThrow();expect(good).toHaveBeenCalledTimes(1);expect(log).toHaveBeenCalledWith("Read-wave observer failed",failure); }
 finally { releaseBad();releaseGood();log.mockRestore(); }
});
