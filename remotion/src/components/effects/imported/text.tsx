/**
 * Ported text-reveal effects (Video Factory × HyperFrames integration).
 * See titles.tsx header for the porting note.
 */
import React from 'react';
import {interpolate, random, useCurrentFrame} from 'remotion';
import {AE_EASE} from '../../tokens';
import {fontsFor} from '../fonts';

const clamp = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};

export interface TextEffectProps {
  text: string;
  color?: string;
  accent?: string;
  accentWords?: string[];
  fontSize?: number;
  align?: 'left' | 'center' | 'right';
  startFrame?: number;
  global_style?: string;
  seed?: number;
}

/** hyperframes_source: per-word-rise — words rise in a blur-to-sharp cascade,
 *  settling softly, staggered in reading order. */
export const PerWordRise: React.FC<TextEffectProps> = ({
  text,
  color = '#fff',
  accent,
  accentWords = [],
  fontSize = 44,
  align = 'left',
  startFrame = 0,
  global_style,
}) => {
  const frame = useCurrentFrame();
  const fonts = fontsFor(global_style);
  const words = text.split(' ');

  return (
    <div style={{textAlign: align, fontFamily: fonts.display, fontSize, fontWeight: 700, lineHeight: 1.2}}>
      {words.map((w, i) => {
        const start = startFrame + i * 3;
        const p = interpolate(frame, [start, start + 14], [0, 1], {...clamp, easing: AE_EASE});
        const isAccent = accent && accentWords.some((a) => w.toLowerCase().includes(a.toLowerCase()));
        return (
          <span
            key={i}
            style={{
              display: 'inline-block',
              opacity: p,
              transform: `translateY(${(1 - p) * 26}px)`,
              filter: `blur(${(1 - p) * 5}px)`,
              color: isAccent ? accent : color,
              marginRight: '0.3em',
            }}
          >
            {w}
          </span>
        );
      })}
    </div>
  );
};

const GLYPHS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789#%&*';

/** hyperframes_source: scramble-reveal — deterministic hacker-style text
 *  reveal that cycles fixed glyph rows and locks the target left to right. */
export const ScrambleReveal: React.FC<TextEffectProps> = ({
  text,
  color = '#fff',
  accent,
  fontSize = 40,
  align = 'left',
  startFrame = 0,
  global_style,
  seed = 0,
}) => {
  const frame = useCurrentFrame();
  const fonts = fontsFor(global_style);
  const chars = text.split('');
  const lockFrames = 2; // frames per character lock, left to right
  const scrambleWindow = 10; // frames a character scrambles before locking

  return (
    <div
      style={{
        textAlign: align,
        fontFamily: fonts.label,
        fontSize,
        fontWeight: 600,
        letterSpacing: '0.04em',
        color: accent ?? color,
      }}
    >
      {chars.map((ch, i) => {
        const lockAt = startFrame + i * lockFrames;
        const local = frame - (lockAt - scrambleWindow);
        if (ch === ' ') return <span key={i}>&nbsp;</span>;
        if (local < 0) return <span key={i} style={{opacity: 0}}>{ch}</span>;
        if (frame >= lockAt) return <span key={i}>{ch}</span>;
        const tick = Math.floor(local / 2);
        const glyph = GLYPHS[Math.floor(random(`${seed}-scramble-${i}-${tick}`) * GLYPHS.length)];
        return (
          <span key={i} style={{color: 'rgba(255,255,255,0.55)'}}>
            {glyph}
          </span>
        );
      })}
    </div>
  );
};
