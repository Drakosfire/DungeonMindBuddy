/** Stable structural equality for retained complete intents, not display text. */
export function exactIntent(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(exactIntent).join(',')}]`;
  if (value !== null && typeof value === 'object') return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${exactIntent((value as Record<string, unknown>)[key])}`).join(',')}}`;
  return JSON.stringify(value);
}

/** Serialize same-origin retention changes so two views cannot overwrite recovery. */
export async function withIntentLock<T>(key:string,work:()=>T|Promise<T>):Promise<T>{
 if(!navigator.locks)throw new Error('This browser cannot safely retain this operation. Use a browser with Web Locks.');
 return navigator.locks.request(`dmb.intent:${key}`,{mode:'exclusive'},work);
}
