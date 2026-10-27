import "@testing-library/jest-dom/vitest";

// Model the browser's per-name exclusive Web Locks; production has no unlocked fallback.
const draftLocks=new Map<string,Promise<unknown>>();
Object.defineProperty(navigator,"locks",{configurable:true,value:{request(name:string,callback:()=>unknown){
  const task=(draftLocks.get(name)??Promise.resolve()).catch(()=>{}).then(callback);
  draftLocks.set(name,task.catch(()=>{}));
  return task;
}}});
