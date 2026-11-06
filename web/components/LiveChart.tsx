/** Rolling line for live data, with an optional red-flag line. Auto-scales when min/max are omitted. */
export function LiveChart({ values, min, max, flag, color = "var(--brown)", height = 90, fill = true }: {
  values: (number | null)[]; min?: number; max?: number; flag?: number; color?: string; height?: number; fill?: boolean;
}) {
  const pts = values.map((v, i) => [i, v] as const).filter((p): p is readonly [number, number] => p[1] !== null);
  const W = 300;
  if (pts.length < 2) return <svg viewBox={`0 0 ${W} ${height}`} className="w-full" style={{ height }} />;
  const ys = pts.map((p) => p[1]);
  const lo = min ?? Math.min(...ys) - 1;
  const hi = max ?? Math.max(...ys) + 1;
  const n = Math.max(values.length - 1, 1);
  const x = (i: number) => (i / n) * W;
  const y = (v: number) => height - ((Math.min(Math.max(v, lo), hi) - lo) / (hi - lo || 1)) * (height - 6) - 3;
  const line = pts.map(([i, v]) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  const last = pts[pts.length - 1];
  return (
    <svg viewBox={`0 0 ${W} ${height}`} preserveAspectRatio="none" className="w-full overflow-visible" style={{ height }}>
      {flag !== undefined && flag > lo && flag < hi && (
        <line x1={0} x2={W} y1={y(flag)} y2={y(flag)} stroke="var(--danger)" strokeDasharray="4 4" strokeWidth={1} vectorEffect="non-scaling-stroke" opacity={0.6} />
      )}
      {fill && <polygon points={`${x(pts[0][0])},${height} ${line} ${x(last[0])},${height}`} fill={color} opacity={0.08} />}
      <polyline points={line} fill="none" stroke={color} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
      <circle cx={x(last[0])} cy={y(last[1])} r={3} fill={color} />
    </svg>
  );
}
