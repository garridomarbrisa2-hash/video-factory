/**
 * GlitchBeat — a single RGB-split + slice-shear "signal break" (§9).
 * The crime genre's twist beat: the frame tears for 5–15 frames, then snaps back
 * clean. Rarity is the whole point — one per video, at the reveal.
 *
 * Technique: two re-rendered copies of `children`, tinted red/cyan, offset on X by
 * seeded noise, masked into thin horizontal slices that shear independently. The
 * base stays intact underneath so the tear reads as a malfunction, not a blur.
 * Deterministic (seeded). Duration + intensity capped by the style's signatureCaps.
 */
import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import {noise3D} from '@remotion/noise';

const clamp = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};

export const GlitchBeat: React.FC<{
  /** Frame the glitch fires on (the twist beat). */
  at: number;
  /** How long the tear lasts (frames). 5–15 reads; default 8. */
  frames?: number;
  /** 0..1 — capped by style signatureCaps.glitch. */
  intensity?: number;
  /** Per-scene seed so the slice pattern is deterministic. */
  seed?: number;
  children?: React.ReactNode;
}> = ({at, frames = 8, intensity = 1, seed = 0, children}) => {
  const frame = useCurrentFrame();
  const local = frame - at;
  if (local < 0 || local > frames || intensity <= 0) {
    return <>{children}</>;
  }

  // Envelope: violent at the start, releases to clean by the end (a break, not a hum).
  const env = interpolate(local, [0, frames], [1, 0], clamp) * intensity;
  const s = `glitch-${seed}`;

  // RGB channel split — copies offset opposite ways on X.
  const split = 10 * env;
  const rx = noise3D(`${s}-r`, 0, 0, frame * 1.3) * split;
  const cx = -noise3D(`${s}-c`, 0, 0, frame * 1.3) * split;

  // 4 horizontal slices shear independently (the "torn scanline" look).
  const slices = [0, 1, 2, 3].map((i) => {
    const top = i * 25;
    const shear = noise3D(`${s}-sl${i}`, 0, 0, frame * 1.7) * 60 * env;
    const show = Math.abs(noise3D(`${s}-on${i}`, 0, 0, frame * 2.1)) > 0.18; // slices drop in/out
    return {top, shear, show};
  });

  return (
    <div style={{position: 'relative', width: '100%', height: '100%'}}>
      {/* Base frame — intact underneath. */}
      {children}

      {/* Red channel copy */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          transform: `translateX(${rx}px)`,
          mixBlendMode: 'screen',
          opacity: 0.55 * env,
          filter: 'saturate(2) hue-rotate(-40deg)',
        }}
      >
        {children}
      </div>
      {/* Cyan channel copy */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          transform: `translateX(${cx}px)`,
          mixBlendMode: 'screen',
          opacity: 0.55 * env,
          filter: 'saturate(2) hue-rotate(150deg)',
        }}
      >
        {children}
      </div>

      {/* Shearing slices — thin horizontal bands torn sideways. */}
      {slices.map((sl, i) =>
        sl.show ? (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: 0,
              right: 0,
              top: `${sl.top}%`,
              height: '25%',
              overflow: 'hidden',
              transform: `translateX(${sl.shear}px)`,
              opacity: 0.9 * env,
            }}
          >
            <div style={{transform: `translateY(-${sl.top}%)`, width: '100%', height: '400%'}}>{children}</div>
          </div>
        ) : null,
      )}
    </div>
  );
};
