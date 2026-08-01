/**
 * Living light (Phase 7) — the second "AE vs slideshow" tell.
 *
 * A printed slide has flat, static light. An edited shot has light that LIVES:
 * a volumetric sweep drifts across the frame, dust motes float through the beam,
 * and a soft flare answers the beat. All procedural, seeded, deterministic.
 *
 * Per-style intensity comes from `lightVocab` in tokens — scenes never hardcode.
 */
import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {noise3D} from '@remotion/noise';

export interface LightAmounts {
  /** Volumetric sweep strength 0..1 (0 = off). */
  sweep: number;
  /** Number of dust motes (0 = off). */
  dust: number;
  /** Beat-reactive flare strength 0..1. */
  flare: number;
  /** Warm (true) vs cool (false) light tint. */
  warm: boolean;
}

/** Slow volumetric light sweep — a soft diagonal beam drifting across frame. */
const Sweep: React.FC<{amount: number; seed: number; warm: boolean}> = ({amount, seed, warm}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  if (amount <= 0) return null;

  // Beam drifts slowly across the frame over the scene (deterministic).
  const t = frame / Math.max(1, durationInFrames);
  const baseX = noise3D(`sweep-${seed}`, 0, 0, t * 0.6);
  const x = 20 + baseX * 30; // wanders between ~ -10% and 50%
  const tint = warm ? '255,214,150' : '170,200,235';

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(115deg, rgba(${tint},0) 30%, rgba(${tint},${0.16 * amount}) 46%, rgba(${tint},${0.05 * amount}) 60%, rgba(${tint},0) 78%)`,
        transform: `translateX(${x}%)`,
        mixBlendMode: 'screen',
        pointerEvents: 'none',
      }}
    />
  );
};

/** Floating dust motes — tiny soft dots drifting up/through the light. */
const Dust: React.FC<{count: number; seed: number; warm: boolean}> = ({count, seed, warm}) => {
  const frame = useCurrentFrame();
  const {durationInFrames, width, height} = useVideoConfig();
  if (count <= 0) return null;

  const tint = warm ? '255,226,180' : '200,220,245';
  const motes = [];
  for (let i = 0; i < count; i++) {
    // Deterministic per-mote params from seed.
    const px = noise3D(`dust-x-${seed}-${i}`, 0, 0, 0) * 0.5 + 0.5;
    const speed = 0.15 + (noise3D(`dust-s-${seed}-${i}`, 0, 0, 0) * 0.5 + 0.5) * 0.3;
    const phase = noise3D(`dust-p-${seed}-${i}`, 0, 0, 0);
    const size = 1.5 + (noise3D(`dust-z-${seed}-${i}`, 0, 0, 0) * 0.5 + 0.5) * 3.5;

    // Drift upward + gentle horizontal wander, looping over the scene.
    const life = (frame / durationInFrames + phase) % 1;
    const y = 1 - life; // bottom -> top
    const wander = noise3D(`dust-w-${seed}-${i}`, 0, 0, frame * 0.02) * 4;
    const x = px * 100 + wander;
    const opacity = Math.sin(life * Math.PI) * 0.5; // fade in/out over its loop

    motes.push(
      <div
        key={i}
        style={{
          position: 'absolute',
          left: `${x}%`,
          top: `${y * 100}%`,
          width: size,
          height: size,
          borderRadius: '50%',
          background: `rgba(${tint},${opacity})`,
        }}
      />,
    );
  }
  return (
    <AbsoluteFill style={{mixBlendMode: 'screen', pointerEvents: 'none'}}>{motes}</AbsoluteFill>
  );
};

/** Beat-reactive flare — a soft bloom that swells then settles on the beat. */
const Flare: React.FC<{amount: number; seed: number; at: number; warm: boolean}> = ({amount, seed, at, warm}) => {
  const frame = useCurrentFrame();
  if (amount <= 0) return null;
  const local = frame - at;
  if (local < 0) return null;

  // Swell fast, decay slow (like a real flare answering a hit).
  const swell = Math.min(1, local / 4);
  const decay = Math.max(0, 1 - local / 40);
  const strength = swell * decay * amount;
  const tint = warm ? '255,220,170' : '190,215,245';
  const cx = 30 + (noise3D(`flare-x-${seed}`, 0, 0, 0) * 0.5 + 0.5) * 40;

  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(circle at ${cx}% 38%, rgba(${tint},${0.4 * strength}) 0%, rgba(${tint},${0.12 * strength}) 22%, rgba(${tint},0) 55%)`,
        mixBlendMode: 'screen',
        pointerEvents: 'none',
      }}
    />
  );
};

export const LivingLight: React.FC<LightAmounts & {seed: number; beatAt?: number}> = ({
  sweep,
  dust,
  flare,
  warm,
  seed,
  beatAt = 0,
}) => {
  return (
    <>
      <Sweep amount={sweep} seed={seed} warm={warm} />
      <Dust count={dust} seed={seed} warm={warm} />
      <Flare amount={flare} seed={seed} at={beatAt} warm={warm} />
    </>
  );
};
