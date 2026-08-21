/**
 * Ported highlight/emphasis effects (Video Factory × HyperFrames integration).
 * See titles.tsx header for the porting note.
 */
import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import {AE_SETTLE} from '../../tokens';
import {fontsFor} from '../fonts';

const clamp = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};

export interface HighlightEffectProps {
  text: string;
  emphasisWord?: string;
  color?: string;
  accent?: string;
  fontSize?: number;
  align?: 'left' | 'center' | 'right';
  startFrame?: number;
  /** Fraction (0..1) of the reveal window at which the marker draws. */
  drawAt?: number;
  global_style?: string;
}

function splitOnWord(text: string, word?: string): [string, string, string] | null {
  if (!word) return null;
  const idx = text.toLowerCase().indexOf(word.toLowerCase());
  if (idx < 0) return null;
  return [text.slice(0, idx), text.slice(idx, idx + word.length), text.slice(idx + word.length)];
}

/** hyperframes_source: marker-highlight — text settles, then one hand-drawn
 *  marker stroke draws under the emphasized word on cue. */
export const MarkerHighlight: React.FC<HighlightEffectProps> = ({
  text,
  emphasisWord,
  color = '#fff',
  accent = '#ffb84d',
  fontSize = 42,
  align = 'left',
  startFrame = 0,
  global_style,
}) => {
  const frame = useCurrentFrame();
  const fonts = fontsFor(global_style);
  const textP = interpolate(frame, [startFrame, startFrame + 16], [0, 1], clamp);
  const drawStart = startFrame + 18;
  const drawP = interpolate(frame, [drawStart, drawStart + 12], [0, 100], {...clamp, easing: AE_SETTLE});
  const parts = splitOnWord(text, emphasisWord);

  return (
    <div style={{textAlign: align, fontFamily: fonts.display, fontSize, fontWeight: 700, color, opacity: textP}}>
      {parts ? (
        <>
          {parts[0]}
          <span style={{position: 'relative', display: 'inline-block'}}>
            {parts[1]}
            <svg
              style={{position: 'absolute', left: '-4%', bottom: '-0.12em', width: '108%', height: '0.42em', overflow: 'visible'}}
              viewBox="0 0 100 20"
              preserveAspectRatio="none"
            >
              <path
                d="M2 14 Q 50 22 98 12"
                fill="none"
                stroke={accent}
                strokeWidth={7}
                strokeLinecap="round"
                pathLength={100}
                strokeDasharray={100}
                strokeDashoffset={100 - drawP}
              />
            </svg>
          </span>
          {parts[2]}
        </>
      ) : (
        text
      )}
    </div>
  );
};

/** hyperframes_source: inline-highlight — a marker-style block sweeps in
 *  behind the whole text (or emphasis word), left to right. */
export const InlineHighlight: React.FC<HighlightEffectProps> = ({
  text,
  emphasisWord,
  color = '#111',
  accent = '#ffe066',
  fontSize = 40,
  align = 'left',
  startFrame = 0,
  global_style,
}) => {
  const frame = useCurrentFrame();
  const fonts = fontsFor(global_style);
  const sweepP = interpolate(frame, [startFrame, startFrame + 14], [0, 100], clamp);
  const parts = splitOnWord(text, emphasisWord) ?? ['', text, ''];

  return (
    <div style={{textAlign: align, fontFamily: fonts.display, fontSize, fontWeight: 700}}>
      <span style={{color: '#fff'}}>{parts[0]}</span>
      <span
        style={{
          position: 'relative',
          color,
          padding: '0 0.12em',
          background: `linear-gradient(90deg, ${accent} ${sweepP}%, transparent ${sweepP}%)`,
        }}
      >
        {parts[1]}
      </span>
      <span style={{color: '#fff'}}>{parts[2]}</span>
    </div>
  );
};

/** hyperframes_source: shimmer-sweep — a light band sweeps across the text
 *  once via a moving CSS gradient mask. */
export const ShimmerSweep: React.FC<HighlightEffectProps> = ({
  text,
  color = '#fff',
  accent = '#ffffff',
  fontSize = 44,
  align = 'left',
  startFrame = 0,
  global_style,
}) => {
  const frame = useCurrentFrame();
  const fonts = fontsFor(global_style);
  const introP = interpolate(frame, [startFrame, startFrame + 12], [0, 1], clamp);
  const sweepP = interpolate(frame, [startFrame + 10, startFrame + 34], [-40, 140], clamp);

  return (
    <div
      style={{
        textAlign: align,
        fontFamily: fonts.display,
        fontSize,
        fontWeight: 700,
        color,
        opacity: introP,
        backgroundImage: `linear-gradient(100deg, ${color} 40%, ${accent} 50%, ${color} 60%)`,
        backgroundSize: '250% 100%',
        backgroundPosition: `${sweepP}% 0`,
        WebkitBackgroundClip: 'text',
        backgroundClip: 'text',
        WebkitTextFillColor: 'transparent',
      }}
    >
      {text}
    </div>
  );
};
