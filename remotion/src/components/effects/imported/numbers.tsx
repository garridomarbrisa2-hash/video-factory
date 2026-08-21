/**
 * Ported number effects (Video Factory × HyperFrames integration).
 * See titles.tsx header for the porting note.
 */
import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {SPRING_SNAPPY} from '../../tokens';
import {fontsFor} from '../fonts';

const clamp = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};

export interface NumberEffectProps {
  value: number;
  decimals?: number;
  prefix?: string;
  suffix?: string;
  color?: string;
  accent?: string;
  fontSize?: number;
  startFrame?: number;
  frames?: number;
  global_style?: string;
  glow?: boolean;
}

/** hyperframes_source: count-up — eases between values, lands with a
 *  restrained scale pulse (optional glow on the accent). */
export const CountUpNumber: React.FC<NumberEffectProps> = ({
  value,
  decimals = 0,
  prefix = '',
  suffix = '',
  color = '#fff',
  accent,
  fontSize = 120,
  startFrame = 0,
  frames = 26,
  global_style,
  glow = false,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const fonts = fontsFor(global_style);
  const local = Math.max(0, frame - startFrame);
  const s = spring({frame: local, fps, config: SPRING_SNAPPY, durationInFrames: frames});
  const current = interpolate(s, [0, 1], [0, value], clamp);
  const landFrame = startFrame + frames;
  const pulse = interpolate(frame, [landFrame, landFrame + 3, landFrame + 10], [1, 1.06, 1], clamp);

  return (
    <div
      style={{
        fontFamily: fonts.display,
        fontSize,
        fontWeight: 900,
        color,
        fontVariantNumeric: 'tabular-nums',
        transform: `scale(${pulse})`,
        textShadow: glow && accent ? `0 0 24px ${accent}88` : undefined,
      }}
    >
      {prefix}
      {current.toLocaleString('en-US', {minimumFractionDigits: decimals, maximumFractionDigits: decimals})}
      {suffix}
    </div>
  );
};

/** hyperframes_source: number-wheel — rolling digit counter; each digit spins
 *  independently on a vertical strip and settles on the target. */
export const NumberWheel: React.FC<NumberEffectProps> = ({
  value,
  decimals = 0,
  prefix = '',
  suffix = '',
  color = '#fff',
  fontSize = 120,
  startFrame = 0,
  frames = 22,
  global_style,
}) => {
  const frame = useCurrentFrame();
  const fonts = fontsFor(global_style);
  const text = value.toLocaleString('en-US', {minimumFractionDigits: decimals, maximumFractionDigits: decimals});
  const digitH = fontSize * 1.15;

  return (
    <div style={{display: 'flex', fontFamily: fonts.display, fontSize, fontWeight: 900, color, fontVariantNumeric: 'tabular-nums'}}>
      {prefix ? <span>{prefix}</span> : null}
      {text.split('').map((ch, i) => {
        if (!/[0-9]/.test(ch)) return <span key={i}>{ch}</span>;
        const digit = parseInt(ch, 10);
        const start = startFrame + i * 2;
        const p = interpolate(frame, [start, start + frames], [0, 1], clamp);
        // Spin down from a random-looking higher digit onto the target.
        const spinFrom = 9;
        const settledDigit = digit + (1 - p) * ((spinFrom - digit + 10) % 10);
        return (
          <span key={i} style={{display: 'inline-block', height: digitH, overflow: 'hidden', width: '0.62em'}}>
            <span style={{display: 'block', transform: `translateY(${(1 - p) * -digitH * 0.15}px)`}}>
              {Math.round(settledDigit) % 10}
            </span>
          </span>
        );
      })}
      {suffix ? <span>{suffix}</span> : null}
    </div>
  );
};
