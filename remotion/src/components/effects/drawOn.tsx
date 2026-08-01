/**
 * Draw-on SVG strokes — handwritten underlines, circles, arrows via
 * stroke-dashoffset. The "craft moment" primitive (docs/AE_TRENDS_CATALOG.md §22).
 *
 * Uses @remotion/paths evolvePath (verified) — returns dasharray/offset that
 * draw the path over progress 0→1. Deterministic, cheap, GPU-repainted only.
 */
import React from 'react';
import {evolvePath} from '@remotion/paths';
import {interpolate, useCurrentFrame} from 'remotion';

const clamp = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};

export const DrawOnUnderline: React.FC<{
  width: number;
  color: string;
  startFrame?: number;
  frames?: number;
  strokeWidth?: number;
  /** Slight hand-drawn wobble in the path. */
  wobble?: number;
}> = ({width, color, startFrame = 0, frames = 14, strokeWidth = 4, wobble = 3}) => {
  const frame = useCurrentFrame();
  const progress = interpolate(frame, [startFrame, startFrame + frames], [0, 1], clamp);

  // Hand-drawn feel: gentle double-curve across the width.
  const h = strokeWidth * 2;
  const d = `M 2 ${h / 2} C ${width * 0.3} ${h / 2 - wobble}, ${width * 0.65} ${h / 2 + wobble}, ${width - 2} ${h / 2 - wobble / 2}`;
  const {strokeDasharray, strokeDashoffset} = evolvePath(progress, d);

  return (
    <svg width={width} height={h} viewBox={`0 0 ${width} ${h}`} style={{display: 'block', overflow: 'visible'}}>
      <path
        d={d}
        fill="none"
        stroke={color}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeDasharray={strokeDasharray}
        strokeDashoffset={strokeDashoffset}
      />
    </svg>
  );
};

/** Rough hand-drawn circle/ellipse around content (for emphasis beats). */
export const DrawOnCircle: React.FC<{
  width: number;
  height: number;
  color: string;
  startFrame?: number;
  frames?: number;
  strokeWidth?: number;
  children?: React.ReactNode;
}> = ({width, height, color, startFrame = 0, frames = 18, strokeWidth = 4, children}) => {
  const frame = useCurrentFrame();
  const progress = interpolate(frame, [startFrame, startFrame + frames], [0, 1], clamp);

  const rx = width / 2 - strokeWidth;
  const ry = height / 2 - strokeWidth;
  const cx = width / 2;
  const cy = height / 2;
  // Slightly imperfect ellipse reads hand-drawn.
  const d = `M ${cx + rx} ${cy} A ${rx} ${ry * 0.96} 0 1 1 ${cx - rx} ${cy + 2} A ${rx * 0.98} ${ry} 0 1 1 ${cx + rx} ${cy}`;
  const {strokeDasharray, strokeDashoffset} = evolvePath(progress, d);

  return (
    <div style={{position: 'relative', display: 'inline-block'}}>
      {children}
      <svg
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        style={{position: 'absolute', inset: 0, overflow: 'visible', pointerEvents: 'none'}}
      >
        <path
          d={d}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={strokeDasharray}
          strokeDashoffset={strokeDashoffset}
        />
      </svg>
    </div>
  );
};
