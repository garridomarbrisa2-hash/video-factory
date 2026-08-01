/**
 * Depth-parallax renderer (Phase 7) — the single biggest "AE vs slideshow" tell.
 *
 * Instead of one rigid full-frame transform, we render the still as THREE soft
 * planes (far / mid / near, baked by pipeline/assets/depth_planes.py) and move
 * each at a different rate + scale + rotate. Differential motion = perceived
 * depth. Soft masks mean no hard cutout edges — it reads as a 2.5D scene, not
 * a collage.
 *
 * Motion is deterministic (seeded simplex noise) and eased (settle + drift tail).
 * Per-plane amounts come from `depthVocab` in tokens — scenes never hardcode.
 */
import React from 'react';
import {Img, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {cameraDrift, easedCameraProgress, overscanFor} from './camera';

export interface DepthPlanes {
  base: string;
  far: string;
  mid: string;
  near: string;
}

/** Per-plane motion multipliers. Near moves most (foreground sweeps past),
 * far moves least (background barely shifts) — the parallax invariant. */
export interface ParallaxAmounts {
  /** Base zoom applied over the whole move (1.0 = none). */
  zoom: number;
  /** Pan travel in % of frame for the NEAR plane at full move. */
  pan: number;
  /** Extra scale separation between near and far (e.g. 0.06). */
  separation: number;
  /** Micro rotation amplitude in degrees on the near plane. */
  rotate: number;
}

interface Props {
  planes: DepthPlanes;
  amounts: ParallaxAmounts;
  seed: number;
  filter?: string;
}

/** One soft plane drifting at its own rate. */
const Plane: React.FC<{
  src: string;
  depth: number; // 0=far … 1=near
  amounts: ParallaxAmounts;
  seed: number;
  filter?: string;
}> = ({src, depth, amounts, seed, filter}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();

  // Eased primary move + drift tail (no constant-velocity slide).
  const prog = easedCameraProgress(frame, durationInFrames, 0.42, 0.1);

  // Per-plane rates: far ~ 0.35×, mid ~ 0.65×, near ~ 1.0× the master move.
  const rate = 0.35 + depth * 0.65;
  const scale = amounts.zoom * (1 + amounts.separation * depth * prog);
  const panX = amounts.pan * rate * (prog - 0.5) * 2; // centered sweep
  const rot = amounts.rotate * depth * Math.sin((prog - 0.5) * Math.PI);

  // Organic per-plane drift (different seed per plane so they don't lock together).
  const drift = cameraDrift(frame, `plane-${seed}-${depth}`, 1.2 * rate, 0.05);

  const overscan = overscanFor(1.5 + amounts.separation * 4);

  return (
    <Img
      src={staticFile(src)}
      style={{
        position: 'absolute',
        inset: 0,
        width: '100%',
        height: '100%',
        objectFit: 'cover',
        transform: `scale(${scale * overscan}) translate(calc(${panX}% + ${drift.x}px), ${drift.y}px) rotate(${rot}deg)`,
        filter,
        willChange: 'transform',
      }}
    />
  );
};

/**
 * Render a still as a 2-plane parallax scene (bg + foreground). Two planes are
 * enough for the eye to read depth from differential motion — and each extra
 * full-screen layer is real Chrome compositing cost. The base doubles as the
 * far plane (no separate layer). Near plane carries the parallax sweep.
 *
 * Cost note: we render exactly 2 layers, no backdrop-filters, no giant blur.
 * This keeps it near the cost of a single graded image while killing the flat
 * "slideshow" tell.
 */
export const DepthParallax: React.FC<Props> = ({planes, amounts, seed, filter}) => {
  return (
    <>
      {/* Far/base: the full image, weakest motion. Doubles as the background. */}
      <Plane src={planes.base} depth={0.3} amounts={amounts} seed={seed} filter={filter} />
      {/* Near plane: the lit/foreground band, sweeps most. This is the parallax. */}
      <Plane src={planes.near} depth={1.0} amounts={amounts} seed={seed + 37} filter={filter} />
    </>
  );
};
