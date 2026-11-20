/** Presentation-only registry. Aliases do not change the graph's recorded type. */
export interface GraphTypeStyle {
  readonly color: string;
  readonly aliases?: readonly string[];
}

export interface GraphTypeStyleRegistry {
  readonly types: Readonly<Record<string, GraphTypeStyle>>;
  readonly fallbackColor: string;
}

export const DEFAULT_GRAPH_TYPE_STYLES: GraphTypeStyleRegistry = {
  types: {
    npc: { color: "#77b5d9" },
    pc: { color: "#d68f9f" },
    item: { color: "#d8a17d" },
    event: { color: "#dbb65c" },
    location: { color: "#a4bd78", aliases: ["place"] },
    character: { color: "#a8b4be", aliases: ["character (role unspecified)", "person"] },
    "session beat": { color: "#b397d0", aliases: ["session_beat"] },
    faction: { color: "#b397d0", aliases: ["group", "organization"] },
  },
  fallbackColor: "#bac0c4",
};

/** Exact configured types win over aliases; unconfigured types remain visible. */
export function graphTypeColor(kind: string, registry: GraphTypeStyleRegistry = DEFAULT_GRAPH_TYPE_STYLES): string {
  const key = kind.toLowerCase();
  const entries = Object.entries(registry.types);
  const direct = entries.find(([name]) => name.toLowerCase() === key);
  if (direct) return direct[1].color;
  return entries.find(([, style]) => style.aliases?.some((alias) => alias.toLowerCase() === key))?.[1].color ?? registry.fallbackColor;
}
