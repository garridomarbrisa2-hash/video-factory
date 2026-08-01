/**
 * Transition helpers — in-scene energy that sits UNDER the FFmpeg xfade.
 *
 * Our batch pipeline keeps FFmpeg xfade between per-scene clips (GPU-first,
 * AGENTS.md principle #5). These helpers add craft INSIDE scenes so the
 * xfade isn't the only motion: cut-masking light leaks at scene head/tail,
 * whip-in entrances, and accent frames.
 *
 * <LightLeak> is WebGL — renders need chromiumOptions {gl:'angle'} (already set).
 */
import React from 'react';
import {LightLeak} from '@remotion/light-leaks';
import {useCurrentFrame, useVideoConfig} from 'remotion';

/**
 * Light leak that masks the head of a scene (plays under the incoming xfade)
 * or the tail (under the outgoing). Retracts over its second half, so placing
 * it at scene start reads as "the cut flashed warm then settled."
 * Tail leaks are timed to END on the last frame so the peak sits inside the
 * FFmpeg xfade window (12f @30fps) — that's what actually masks the cut.
 */
export const CutLeak: React.FC<{
  when: 'head' | 'tail';
  frames?: number;
  seed?: number;
  hueShift?: number;
}> = ({when, frames = 18, seed = 0, hueShift = 0}) => {
  const {durationInFrames} = useVideoConfig();
  const frame = useCurrentFrame();
  // Tail: the leak's final frame = scene's final frame.
  const start = when === 'head' ? 0 : durationInFrames - frames;
  if (frame < start || frame > start + frames) return null;

  return (
    <div style={{position: 'absolute', inset: 0, mixBlendMode: 'screen', pointerEvents: 'none'}}>
      <LightLeak durationInFrames={frames} seed={seed} hueShift={hueShift} />
    </div>
  );
};

/**
 * Whip-in entrance — fast expo settle from off-axis. Use on content layers
 * (not background) so the frame "catches" the graphic. 8–12 frames.
 * Returns transform + opacity for the entering layer.
 */
export function whipIn(
  frame: number,
  startFrame: number,
  frames: number,
  fromXPx = 160,
): {transform: string; opacity: number} {
  const local = frame - startFrame;
  if (local < 0) return {transform: `translateX(${fromXPx}px)`, opacity: 0};
  const p = Math.min(1, local / frames);
  // Expo-out: fast cover, hard landing (AE "snap" curve 0.85,0,0.15,1)
  const eased = 1 - Math.pow(1 - p, 4);
  return {
    transform: `translateX(${fromXPx * (1 - eased)}px)`,
    opacity: Math.min(1, local / 3),
  };
}
