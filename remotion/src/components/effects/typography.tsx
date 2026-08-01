/**
 * Kinetic typography — AE text-animator grammar (docs/AE_TRENDS_CATALOG §1–4).
 *
 *   MaskLineReveal — per-line rise from behind a mask, ease-out settle
 *   WordPop        — per-word entrance in reading order (VO-sync beats)
 *   TrackingTitle  — letter-spacing contraction (cinematic settle)
 *
 * All motion is Y-translate + opacity + tracking only — no scale-pop, no
 * rotation (PRO_EDIT_STYLE bans). Springs only via tokens (modern style).
 */
import React from 'react';
import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {AE_EASE, AE_SNAP, STAGGER} from '../tokens';
import {fontsFor} from './fonts';

const clamp = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};

// ---------------------------------------------------------------------------
// Line breaking + sizing — the fix for "stiff one-line titles".
// ---------------------------------------------------------------------------

/**
 * Greedy word-wrap into balanced lines. Respects explicit \n first; otherwise
 * wraps to maxCharsPerLine and rebalances so the last line isn't a 1-word orphan.
 */
export function breakLines(text: string, maxCharsPerLine = 24): string[] {
  if (text.includes('\n')) {
    return text.split('\n').filter((l) => l.trim().length > 0);
  }
  const words = text.split(' ').filter(Boolean);
  if (words.length === 0) return [];
  const lines: string[] = [];
  let cur = '';
  for (const w of words) {
    const next = cur ? `${cur} ${w}` : w;
    if (next.length <= maxCharsPerLine || !cur) {
      cur = next;
    } else {
      lines.push(cur);
      cur = w;
    }
  }
  if (cur) lines.push(cur);

  // Rebalance: if last line is a single short word and we have ≥2 lines,
  // pull one word down so it doesn't read as an orphan.
  if (lines.length >= 2) {
    const last = lines[lines.length - 1];
    const prev = lines[lines.length - 2];
    if (last.split(' ').length === 1 && prev.split(' ').length > 1) {
      const prevWords = prev.split(' ');
      const moved = prevWords.pop()!;
      lines[lines.length - 2] = prevWords.join(' ');
      lines[lines.length - 1] = `${moved} ${last}`;
    }
  }
  return lines;
}

/**
 * Responsive display size — longer text scales down so it never overflows.
 * Base is the size for a short (≤12 char) title; scales down by total length.
 */
export function fontSizeFor(text: string, base: number, min = 0.55): number {
  const longest = Math.max(...breakLines(text).map((l) => l.length), 1);
  // Shrink as the longest line grows past ~14 chars.
  const factor = Math.max(min, Math.min(1, 14 / longest));
  return Math.round(base * factor);
}

/** Split into display lines on explicit newlines (skills own line breaks). */
function toLines(text: string): string[] {
  return breakLines(text);
}

// ---------------------------------------------------------------------------
// MaskLineReveal — THE documentary text entrance.
// Each line rises out of an overflow-hidden slot on AE_EASE, staggered.
// ---------------------------------------------------------------------------
export const MaskLineReveal: React.FC<{
  text: string;
  color?: string;
  accent?: string;
  accentWords?: string[];
  fontSize?: number;
  fontFamily?: string;
  fontWeight?: number;
  lineHeight?: number;
  align?: 'left' | 'center' | 'right';
  startFrame?: number;
  stagger?: number;
  frames?: number;
  uppercase?: boolean;
  /** Max chars per line for auto word-wrap (default 24). */
  maxCharsPerLine?: number;
  /** Auto-size: shrink when text is long (default true). */
  autoSize?: boolean;
  global_style?: string;
}> = ({
  text,
  color = '#fff',
  accent,
  accentWords = [],
  fontSize = 64,
  fontFamily,
  fontWeight = 700,
  lineHeight = 1.12,
  align = 'left',
  startFrame = 0,
  stagger = STAGGER,
  frames = 16,
  uppercase = false,
  maxCharsPerLine = 24,
  autoSize = true,
  global_style,
}) => {
  const frame = useCurrentFrame();
  const fonts = fontsFor(global_style);
  const lines = breakLines(text, maxCharsPerLine);
  const size = autoSize ? fontSizeFor(text, fontSize) : fontSize;

  const renderLine = (line: string) => {
    if (!accent || accentWords.length === 0) return line;
    // Wrap accent words in colored spans (word-boundary, case-insensitive).
    const parts = line.split(new RegExp(`(${accentWords.map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})`, 'gi'));
    return parts.map((p, i) =>
      accentWords.some((w) => w.toLowerCase() === p.toLowerCase()) ? (
        <span key={i} style={{color: accent}}>
          {p}
        </span>
      ) : (
        <span key={i}>{p}</span>
      ),
    );
  };

  return (
    <div style={{textAlign: align, fontFamily: fontFamily ?? fonts.display}}>
      {lines.map((line, i) => {
        const start = startFrame + i * stagger;
        const p = interpolate(frame, [start, start + frames], [0, 1], {...clamp, easing: AE_EASE});
        return (
          <div key={i} style={{overflow: 'hidden', paddingBottom: '0.08em', marginBottom: '-0.08em'}}>
            <div
              style={{
                transform: `translateY(${(1 - p) * 110}%)`,
                opacity: Math.min(1, p * 2.5),
                fontSize: size,
                fontWeight,
                color,
                lineHeight,
                textTransform: uppercase ? 'uppercase' : 'none',
              }}
            >
              {renderLine(line)}
            </div>
          </div>
        );
      })}
    </div>
  );
};

// ---------------------------------------------------------------------------
// WordPop — per-word entrance in reading order. When the pipeline passes
// `word_times` (VO→visual sync, P1), words pop on the spoken syllables; else
// it falls back to even spacing.
// ---------------------------------------------------------------------------
export const WordPop: React.FC<{
  text: string;
  color?: string;
  accent?: string;
  accentWords?: string[];
  fontSize?: number;
  fontFamily?: string;
  fontWeight?: number;
  align?: 'left' | 'center' | 'right';
  startFrame?: number;
  /** Frames between words (fallback when no word_times). 2–3 = brisk, 4–6 = dramatic. */
  perWord?: number;
  maxWidth?: number | string;
  /**
   * Per-word onset times in SECONDS from scene start (VO→visual sync, P1).
   * From the orchestrator's `word_times`. When present, words pop on the spoken
   * syllables (relative to `startFrame`), not on even spacing.
   */
  word_times?: Array<[string, number]>;
  global_style?: string;
}> = ({text, color = '#fff', accent, accentWords = [], fontSize = 56, fontFamily, fontWeight = 700, align = 'left', startFrame = 0, perWord = 3, maxWidth, word_times, global_style}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const fonts = fontsFor(global_style);
  const words = text.split(' ');

  return (
    <div style={{textAlign: align, fontFamily: fontFamily ?? fonts.display, maxWidth, fontSize, fontWeight, color, lineHeight: 1.15}}>
      {words.map((w, i) => {
        // VO-sync: this word's spoken onset (frames), relative to the scene start.
        const sync = word_times?.[i]?.[1];
        const start = startFrame + (sync != null ? Math.round(sync * fps) : i * perWord);
        const p = interpolate(frame, [start, start + 6], [0, 1], {...clamp, easing: AE_SNAP});
        const isAccent = accent && accentWords.some((a) => w.toLowerCase().includes(a.toLowerCase()));
        return (
          <span
            key={i}
            style={{
              display: 'inline-block',
              opacity: p,
              transform: `translateY(${(1 - p) * 0.35}em)`,
              color: isAccent ? accent : color,
              marginRight: '0.28em',
            }}
          >
            {w}
          </span>
        );
      })}
    </div>
  );
};

// ---------------------------------------------------------------------------
// TrackingTitle — wide-tracked caps contracting to rest (cinematic settle).
// ---------------------------------------------------------------------------
export const TrackingTitle: React.FC<{
  text: string;
  color?: string;
  fontSize?: number;
  fontFamily?: string;
  fontWeight?: number;
  align?: 'left' | 'center' | 'right';
  startFrame?: number;
  frames?: number;
  fromEm?: number;
  toEm?: number;
  global_style?: string;
}> = ({text, color = '#fff', fontSize = 40, fontFamily, fontWeight = 600, align = 'left', startFrame = 0, frames = 20, fromEm = 0.3, toEm = 0.04, global_style}) => {
  const frame = useCurrentFrame();
  const fonts = fontsFor(global_style);
  const p = interpolate(frame, [startFrame, startFrame + frames], [0, 1], {...clamp, easing: AE_EASE});

  return (
    <div
      style={{
        fontFamily: fontFamily ?? fonts.display,
        fontSize,
        fontWeight,
        color,
        textAlign: align,
        textTransform: 'uppercase',
        letterSpacing: `${fromEm + (toEm - fromEm) * p}em`,
        opacity: Math.min(1, p * 2),
      }}
    >
      {text}
    </div>
  );
};
