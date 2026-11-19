/** Shared visual primitives for Graph circles and read-only graph previews. */
export function shortLabel(value: string, limit: number): string {
  return value.length > limit ? `${value.slice(0, limit - 1)}…` : value;
}

export function GraphCircleGlyph({ center, radius, kind, name, showLabels, fullCorpus }: {
  center: number
  radius: number
  kind: string
  name: string
  showLabels: boolean
  fullCorpus: boolean
}) {
  return <>
        <circle className="world-graph-canvas__node-circle" cx={center} cy={center} r={radius} />
        {showLabels && <>
          <text className="world-graph-canvas__node-kind" style={fullCorpus ? { fontSize: Math.min(11, Math.max(8, radius * 0.25)) } : undefined} x={center} y={center - 5} textAnchor="middle">{shortLabel(kind, Math.max(7, Math.floor(radius / 3.4)))}</text>
          <text className="world-graph-canvas__node-name" style={fullCorpus ? { fontSize: Math.min(15, Math.max(9, radius * 0.35)) } : undefined} x={center} y={center + 17} textAnchor="middle">
            {shortLabel(name, Math.max(7, Math.floor(radius / 4)))}
          </text>
        </>}
      </>
}
