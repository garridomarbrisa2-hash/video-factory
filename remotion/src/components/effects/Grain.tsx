/**
 * Animated film grain — procedural, deterministic, zero assets.
 *
 * The old static SVG noise never moved; real grain re-seeds every frame.
 * Implementation: a small feTurbulence tile whose seed changes per frame,
 * upscaled by CSS and composited with soft-light blend. Chrome rasterizes
 * the small tile only — cheap at 1080p.
 *
 * Seeded by scene so different scenes have different grain streams, and by
 * frame so renders are deterministic across threads (Remotion requirement).
 */
import React from 'react';
import {useCurrentFrame} from 'remotion';

export const GrainOverlay: React.FC<{
  /** 0 = off. Typical 0.05–0.14 (style JSON grade.grain * 2 is a good start). */
  opacity: number;
  /** Per-scene seed so each scene's grain stream differs. */
  seed?: number;
  /** Re-seed every N frames. 1 = film grain (buzzy), 2 = calmer. */
  holdFrames?: number;
}> = ({opacity, seed = 0, holdFrames = 1}) => {
  const frame = useCurrentFrame();
  if (opacity <= 0) return null;

  const step = Math.floor(frame / holdFrames);
  // Deterministic per (scene, frame-step) — safe for multithreaded render.
  const grainSeed = (seed * 131 + step * 7) % 97;

  // Small tile (160px) upscaled — feTurbulence on a small rect is cheap;
  // the browser scales the composited layer, not the filter input.
  const svg = `<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 160 160'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' seed='${grainSeed}' stitchTiles='stitch'/><feColorMatrix type='matrix' values='0 0 0 0 0.5 0 0 0 0 0.5 0 0 0 0 0.5 0 0 0 0.9 0'/></filter><rect width='160' height='160' filter='url(%23n)'/></svg>`;
  const uri = `data:image/svg+xml,${svg.replace(/#/g, '%23').replace(/</g, '%3C').replace(/>/g, '%3E')}`;

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        backgroundImage: `url("${uri}")`,
        backgroundSize: '200px 200px',
        mixBlendMode: 'soft-light',
        opacity,
        pointerEvents: 'none',
      }}
    />
  );
};
