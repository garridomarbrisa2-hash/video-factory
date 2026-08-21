/**
 * Adapters that wrap EXISTING Video Factory looks into the same
 * (text/number/...) prop shape the ported HyperFrames effects use, so the
 * automatic registry (effectRegistry.ts) genuinely chooses from the full
 * pool — old and new — instead of only ever picking a new import.
 */
import React from 'react';
import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {AE_SETTLE, motionVocab} from '../tokens';
import {countUp} from '../choreo';
import {fontsFor} from './fonts';

const clamp = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};

export interface InlineCountUpProps {
  value: number;
  decimals?: number;
  prefix?: string;
  suffix?: string;
  color?: string;
  fontSize?: number;
  startFrame?: number;
  frames?: number;
  global_style?: string;
}

/** The original Stat.tsx number treatment, extracted so it can compete in
 *  the 'number' registry pool alongside CountUpNumber / NumberWheel. */
/** Marker-only adapter for scenes (e.g. Comparison) that branch their own
 *  JSX by picked effect id instead of rendering a shared Component — the
 *  registry still needs a real component to satisfy EffectDef, so this is a
 *  transparent passthrough that is never actually rendered. */
export const ClassicSplitMarker: React.FC<{children?: React.ReactNode}> = ({children}) => <>{children}</>;

export const InlineCountUp: React.FC<InlineCountUpProps> = ({
  value,
  decimals = 0,
  prefix = '',
  suffix = '',
  color = '#fff',
  fontSize = 148,
  startFrame = 0,
  frames = 24,
  global_style,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const fonts = fontsFor(global_style);
  const vocab = motionVocab(global_style);
  const current = vocab.springAllowed
    ? countUp(frame, fps, startFrame, frames, 0, value, true)
    : interpolate(frame, [startFrame, startFrame + frames], [0, value], {...clamp, easing: AE_SETTLE});
  const opacity = Math.min(1, (frame - startFrame) / 4);

  return (
    <div
      style={{
        fontFamily: fonts.display,
        opacity,
        fontSize,
        fontWeight: 900,
        color,
        textAlign: 'center',
        lineHeight: 1,
        fontVariantNumeric: 'tabular-nums',
        textShadow: '0 4px 18px rgba(0,0,0,0.5)',
      }}
    >
      {prefix}
      {current.toLocaleString('en-US', {minimumFractionDigits: decimals, maximumFractionDigits: decimals})}
      {suffix}
    </div>
  );
};
