/**
 * ArchivalPulse — the "old tape" era overlay (§11): animated scratch lines, dust
 * flecks, and a gentle gate weave (vertical jitter) that signposts archival footage.
 * The history genre's era beat. Opt-in (grade_override/director). Deterministic.
 *
 * Cheap: a few seeded CSS lines + dots re-jittered per frame, no canvas. Intensity
 * capped by signatureCaps.archival.
 */
import React from 'react';
import {useCurrentFrame} from 'remotion';
import {noise3D} from '@remotion/noise';

export const ArchivalPulse: React.FC<{
  /** 0..1 — capped by style signatureCaps.archival. */
  intensity?: number;
  seed?: number;
}> = ({intensity = 1, seed = 0}) => {
  const frame = useCurrentFrame();
  if (intensity <= 0) return null;
  const s = `arch-${seed}`;

  // Gate weave — the whole frame breathes vertically a couple px (projector jitter).
  const weave = noise3D(`${s}-weave`, 0, 0, frame * 0.5) * 2 * intensity;

  // Vertical scratch lines that flicker in/out.
  const scratches = [0, 1, 2].map((i) => {
    const on = Math.abs(noise3D(`${s}-sc${i}`, 0, 0, frame * 1.9)) > 0.42;
    const x = ((i * 619 + seed * 131) % 100);
    const driftX = noise3D(`${s}-scx${i}`, 0, 0, frame * 0.2) * 3;
    return {on, left: x + driftX, op: 0.10 + 0.10 * intensity};
  });

  // Dust flecks.
  const dust = [0, 1, 2, 3, 4].map((i) => {
    const on = Math.abs(noise3D(`${s}-d${i}`, 0, 0, frame * 2.3)) > 0.5;
    return {
      on,
      left: ((i * 233 + seed * 71) % 100),
      top: ((i * 419 + seed * 37) % 100),
      r: 1 + ((i * 7) % 3),
    };
  });

  return (
    <div style={{position: 'absolute', inset: 0, overflow: 'hidden', pointerEvents: 'none', transform: `translateY(${weave}px)`}}>
      {scratches.map((sc, i) =>
        sc.on ? (
          <div key={`s${i}`} style={{position: 'absolute', top: 0, bottom: 0, left: `${sc.left}%`, width: 1, backgroundColor: '#fff', opacity: sc.op}} />
        ) : null,
      )}
      {dust.map((d, i) =>
        d.on ? (
          <div key={`d${i}`} style={{position: 'absolute', left: `${d.left}%`, top: `${d.top}%`, width: d.r, height: d.r, borderRadius: '50%', backgroundColor: '#fff', opacity: 0.18}} />
        ) : null,
      )}
      {/* soft vignette flicker */}
      <div style={{position: 'absolute', inset: 0, boxShadow: 'inset 0 0 180px rgba(0,0,0,0.5)', opacity: 0.5 * intensity}} />
    </div>
  );
};
