/**
 * ChartDrawOn — a data line/bar that draws itself (§20). The modern genre's data
 * beat: a trend line traces on with a leading dot, ending on the takeaway number.
 * Opt-in (director calls it for a data/trend beat). Allowed per signatureCaps.chart.
 */
import React from 'react';
import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {evolvePath} from '@remotion/paths';
import {AE_SETTLE} from '../../tokens';

const clamp = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};

export const ChartDrawOn: React.FC<{
  /** Data points (y values, any scale — normalized internally). */
  points: number[];
  /** Line color (accent). */
  color?: string;
  /** Frame the draw starts. */
  startFrame?: number;
  /** Draw duration (frames). */
  frames?: number;
  /** Chart box size. */
  width?: number;
  height?: number;
}> = ({points, color = '#14b8a6', startFrame = 0, frames = 24, width = 720, height = 360}) => {
  const frame = useCurrentFrame();
  useVideoConfig();
  if (!points || points.length < 2) return null;

  const max = Math.max(...points);
  const min = Math.min(...points);
  const span = max - min || 1;
  const pad = 24;
  const iw = width - pad * 2;
  const ih = height - pad * 2;

  const coords = points.map((v, i) => {
    const x = pad + (i / (points.length - 1)) * iw;
    const y = pad + ih - ((v - min) / span) * ih;
    return {x, y};
  });
  const d = coords.map((c, i) => `${i === 0 ? 'M' : 'L'} ${c.x.toFixed(1)} ${c.y.toFixed(1)}`).join(' ');

  const p = interpolate(frame, [startFrame, startFrame + frames], [0, 1], {...clamp, easing: AE_SETTLE});
  const {strokeDasharray, strokeDashoffset} = evolvePath(p, d);

  // Leading dot rides the current end of the drawn line.
  const headIdx = Math.min(coords.length - 1, Math.floor(p * (coords.length - 1)));
  const head = coords[Math.max(0, headIdx)];

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{display: 'block', overflow: 'visible'}}>
      {/* baseline */}
      <line x1={pad} y1={height - pad} x2={width - pad} y2={height - pad} stroke="rgba(255,255,255,0.2)" strokeWidth={1} />
      <path d={d} fill="none" stroke={color} strokeWidth={4} strokeLinecap="round" strokeLinejoin="round" strokeDasharray={strokeDasharray} strokeDashoffset={strokeDashoffset} />
      {p > 0 ? <circle cx={head.x} cy={head.y} r={7} fill={color} /> : null}
    </svg>
  );
};
