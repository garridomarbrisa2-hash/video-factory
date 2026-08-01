/**
 * CrimeBoard — the evidence-wall collage (§18): pinned photos/cards laid out on a
 * corkboard, connected by red string that draws itself between them. The crime
 * genre's "connecting the dots" beat. Items drop in pinned, strings draw on in
 * sequence, the whole board breathes with a slow push-in.
 *
 * Opt-in only (director calls it for an evidence/connection beat). Item count
 * capped by the style's signatureCaps.crimeBoard. Deterministic layout.
 */
import React from 'react';
import {AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {evolvePath} from '@remotion/paths';
import {fontsFor} from '../fonts';

const clamp = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};

export interface BoardItem {
  /** Image in public/ OR a short text label (a name, place, date). */
  src?: string;
  label?: string;
}

/** Deterministic pseudo-scatter for item i (no real randomness at render). */
function slotFor(i: number, n: number): {x: number; y: number; r: number} {
  const col = i % 3;
  const row = Math.floor(i / 3);
  // Base thirds grid, jittered deterministically by index.
  const jx = ((i * 37) % 11) - 5;
  const jy = ((i * 53) % 9) - 4;
  return {
    x: 18 + col * 30 + jx, // % from left
    y: 24 + row * 34 + jy, // % from top
    r: (((i * 29) % 7) - 3) * 0.9, // deg tilt
  };
}

export const CrimeBoard: React.FC<{
  items: BoardItem[];
  /** Accent (string) color — defaults to crime red. */
  accent?: string;
  global_style?: string;
  /** Per-scene seed. */
  seed?: number;
  /** Beat (frames) the board starts building. Default 0. */
  startFrame?: number;
}> = ({items, accent = '#c0392b', global_style = 'crime', seed = 0, startFrame = 0}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const fonts = fontsFor(global_style);
  const n = Math.min(items.length, 6);
  const shown = items.slice(0, n);

  // Each item lands pinned on its own beat; strings draw after the last pair.
  const itemGap = Math.round(fps * 0.45);
  const itemAt = (i: number) => startFrame + i * itemGap;
  const stringAt = (i: number) => startFrame + (i + 1) * itemGap; // connects item i→i+1

  // Slow push across the whole board (the camera leans into the wall).
  const push = interpolate(frame, [startFrame, startFrame + n * itemGap + fps * 2], [1, 1.06], clamp);

  return (
    <AbsoluteFill style={{transform: `scale(${push})`, transformOrigin: '50% 50%'}}>
      {/* Strings — drawn behind the cards, connecting consecutive items. */}
      <svg style={{position: 'absolute', inset: 0, width: '100%', height: '100%'}} viewBox="0 0 100 100" preserveAspectRatio="none">
        {shown.slice(0, -1).map((_, i) => {
          const a = slotFor(i, n);
          const b = slotFor(i + 1, n);
          const d = `M ${a.x} ${a.y} L ${b.x} ${b.y}`;
          const p = interpolate(frame, [stringAt(i), stringAt(i) + Math.round(fps * 0.6)], [0, 1], clamp);
          const {strokeDasharray, strokeDashoffset} = evolvePath(p, d);
          return (
            <path
              key={i}
              d={d}
              fill="none"
              stroke={accent}
              strokeWidth={0.5}
              strokeDasharray={strokeDasharray}
              strokeDashoffset={strokeDashoffset}
              opacity={0.9}
              vectorEffect="non-scaling-stroke"
            />
          );
        })}
      </svg>

      {/* Cards — photo or label, pinned with a red push-pin. */}
      {shown.map((it, i) => {
        const s = slotFor(i, n);
        const at = itemAt(i);
        const enter = interpolate(frame, [at, at + Math.round(fps * 0.35)], [0, 1], {...clamp});
        const settle = interpolate(frame, [at, at + Math.round(fps * 0.35)], [1.12, 1], clamp);
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: `${s.x}%`,
              top: `${s.y}%`,
              transform: `translate(-50%, -50%) rotate(${s.r}deg) scale(${settle})`,
              opacity: enter,
              boxShadow: '0 16px 40px rgba(0,0,0,0.6)',
            }}
          >
            {/* push-pin */}
            <div
              style={{
                position: 'absolute',
                top: -8,
                left: '50%',
                transform: 'translateX(-50%)',
                width: 14,
                height: 14,
                borderRadius: '50%',
                backgroundColor: accent,
                boxShadow: '0 3px 6px rgba(0,0,0,0.6)',
                zIndex: 2,
              }}
            />
            {it.src ? (
              <div style={{backgroundColor: '#f4f1ea', padding: 8, paddingBottom: 26}}>
                <Img src={staticFile(it.src)} style={{display: 'block', width: 240, height: 170, objectFit: 'cover'}} />
              </div>
            ) : (
              <div
                style={{
                  backgroundColor: '#14161a',
                  border: `1px solid ${accent}33`,
                  padding: '14px 20px',
                  fontFamily: fonts.body,
                  fontSize: 22,
                  fontWeight: 700,
                  letterSpacing: '0.04em',
                  color: '#f2f2f2',
                  whiteSpace: 'nowrap',
                }}
              >
                {it.label}
              </div>
            )}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
