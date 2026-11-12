import type { NativeGraphNode } from './nativeGraphDemoApi';
export * from '../graphLens/nodeExplorerModel';
const compare = (a: string, b: string) => a < b ? -1 : a > b ? 1 : 0;
/** A recorded display label only, never a preferred/canonical name decision. */
export function compactNodeLabel(node: NativeGraphNode): string {
  const names = [...new Set(node.presentation?.recorded_names.filter(n => n.trim()) ?? [])];
  if (!names.length || names.includes(node.name)) return node.name;
  const support = (name: string) => names.filter(other => (` ${other} `).includes(` ${name} `)).length;
  return names.sort((a, b) => support(b) - support(a) || a.length - b.length || compare(a, b))[0]!;
}
