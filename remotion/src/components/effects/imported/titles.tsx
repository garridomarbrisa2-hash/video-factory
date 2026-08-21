/**
 * Ported title-card effects (Video Factory × HyperFrames integration).
 * Reworked as native Remotion components (interpolate/spring, no GSAP/DOM
 * scrubbing) from HyperFrames registry components — see
 * pipeline/config/hyperframes_catalog.json for the source catalog entry of
 * each `hyperframes_source` id below.
 */
import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {AE_EASE, AE_SETTLE, SPRING_SMOOTH} from '../../tokens';
import {fontsFor} from '../fonts';

const clamp = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};

export interface TitleEffectProps {
  text: string;
  kicker?: string;
  color?: string;
  accent?: string;
  fontSize?: number;
  align?: 'left' | 'center' | 'right';
  startFrame?: number;
  global_style?: string;
}

/** hyperframes_source: titlecard-calm — kicker + headline fade upward, drift, hold clean. */
export const TitleCardCalm: React.FC<TitleEffectProps> = ({
  text,
  kicker,
  color = '#fff',
  accent,
  fontSize = 76,
  align = 'left',
  startFrame = 0,
  global_style,
}) => {
  const frame = useCurrentFrame();
  const fonts = fontsFor(global_style);
  const kickerP = interpolate(frame, [startFrame, startFrame + 14], [0, 1], {...clamp, easing: AE_EASE});
  const headlineP = interpolate(frame, [startFrame + 8, startFrame + 26], [0, 1], {...clamp, easing: AE_EASE});
  const drift = interpolate(frame, [startFrame + 8, startFrame + 60], [10, 0], clamp);

  return (
    <div style={{textAlign: align, display: 'flex', flexDirection: 'column', gap: 12}}>
      {kicker ? (
        <div
          style={{
            opacity: kickerP,
            transform: `translateY(${(1 - kickerP) * 14}px)`,
            fontFamily: fonts.label,
            fontSize: 16,
            letterSpacing: '0.22em',
            textTransform: 'uppercase',
            color: accent ?? color,
          }}
        >
          {kicker}
        </div>
      ) : null}
      <div
        style={{
          opacity: headlineP,
          transform: `translateY(${(1 - headlineP) * 22 + drift}px)`,
          fontFamily: fonts.display,
          fontSize,
          fontWeight: 800,
          lineHeight: 1.05,
          color,
          maxWidth: 900,
          whiteSpace: 'normal',
          wordBreak: 'break-word',
        }}
      >
        {text}
      </div>
    </div>
  );
};

export interface TitleLockupProps extends TitleEffectProps {
  label?: string;
}

/** hyperframes_source: titlecard-lockup — kicker fades, wordmark settles center,
 *  hairline rule draws left→right, label fades beneath. */
export const TitleCardLockup: React.FC<TitleLockupProps> = ({
  text,
  kicker,
  label,
  color = '#fff',
  accent,
  fontSize = 88,
  startFrame = 0,
  global_style,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const fonts = fontsFor(global_style);
  const accentColor = accent ?? color;

  const kickerP = interpolate(frame, [startFrame, startFrame + 12], [0, 1], clamp);
  const local = Math.max(0, frame - startFrame - 6);
  const settle = spring({frame: local, fps, config: SPRING_SMOOTH, durationInFrames: 26});
  const wordmarkOpacity = interpolate(settle, [0, 1], [0, 1], clamp);
  const wordmarkY = interpolate(settle, [0, 1], [16, 0], clamp);
  const ruleP = interpolate(frame, [startFrame + 24, startFrame + 40], [0, 100], {...clamp, easing: AE_SETTLE});
  const labelP = interpolate(frame, [startFrame + 34, startFrame + 46], [0, 1], clamp);

  return (
    <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16, textAlign: 'center'}}>
      {kicker ? (
        <div style={{opacity: kickerP, fontFamily: fonts.label, fontSize: 14, letterSpacing: '0.28em', textTransform: 'uppercase', color: accentColor}}>
          {kicker}
        </div>
      ) : null}
      <div
        style={{
          opacity: wordmarkOpacity,
          transform: `translateY(${wordmarkY}px)`,
          fontFamily: fonts.display,
          fontSize,
          fontWeight: 900,
          color,
          maxWidth: 900,
          whiteSpace: 'normal',
          wordBreak: 'break-word',
        }}
      >
        {text}
      </div>
      <div style={{width: 140, height: 2, background: accentColor, clipPath: `inset(0 ${100 - ruleP}% 0 0)`}} />
      {label ? (
        <div style={{opacity: labelP, fontFamily: fonts.label, fontSize: 13, letterSpacing: '0.18em', textTransform: 'uppercase', color: 'rgba(255,255,255,0.65)'}}>
          {label}
        </div>
      ) : null}
    </div>
  );
};

/** hyperframes_source: tracking-in — wide letter-spacing contracts to rest,
 *  paired with a soft rise (distinct from the existing TrackingTitle: this
 *  variant also blurs in, for a slower documentary-grade settle). */
export const LetterTrackingReveal: React.FC<TitleEffectProps> = ({
  text,
  color = '#fff',
  fontSize = 56,
  align = 'left',
  startFrame = 0,
  global_style,
}) => {
  const frame = useCurrentFrame();
  const fonts = fontsFor(global_style);
  const p = interpolate(frame, [startFrame, startFrame + 22], [0, 1], {...clamp, easing: AE_EASE});
  const tracking = interpolate(p, [0, 1], [0.32, 0.02], clamp);
  const blur = interpolate(p, [0, 1], [6, 0], clamp);

  return (
    <div
      style={{
        textAlign: align,
        fontFamily: fonts.display,
        fontSize,
        fontWeight: 700,
        color,
        textTransform: 'uppercase',
        letterSpacing: `${tracking}em`,
        opacity: Math.min(1, p * 1.6),
        filter: `blur(${blur}px)`,
        maxWidth: 900,
        whiteSpace: 'normal',
        wordBreak: 'break-word',
      }}
    >
      {text}
    </div>
  );
};
