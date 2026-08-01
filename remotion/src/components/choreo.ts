/**
 * Choreography vocabulary — reusable editorial animation primitives.
 * Every function takes `frame` and returns style objects; scenes compose these.
 * All frame-driven (never CSS animation) so renders are deterministic.
 */
import {interpolate, random, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {HOUSE_EASE, LINEAR, SPRING_SMOOTH, DURATION, dur, motionVocab} from './tokens';
import {normalizeStyleId} from './styleSystem';

const clamp = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};

// ---------------------------------------------------------------------------
// Entrances
// ---------------------------------------------------------------------------

/** Opacity fade-in on HOUSE_EASE. */
export function fadeIn(frame: number, start: number, frames: number): number {
  return interpolate(frame, [start, start + frames], [0, 1], {...clamp, easing: HOUSE_EASE});
}

/** Hard linear opacity cut (0..1) — editorial default. */
export function cutIn(frame: number, start: number, frames: number): number {
  return interpolate(frame, [start, start + frames], [0, 1], {...clamp, easing: LINEAR});
}

/** Mask wipe progress 0..100 (clip-path inset) on a linear curve. */
export function maskWipe(frame: number, start: number, frames: number): number {
  return interpolate(frame, [start, start + frames], [0, 100], {...clamp, easing: LINEAR});
}

/** clip-path strings for a mask wipe in each direction. */
export const clip = {
  lr: (p: number) => `inset(0 ${100 - p}% 0 0)`,
  rl: (p: number) => `inset(0 0 0 ${100 - p}%)`,
  up: (p: number) => `inset(${100 - p}% 0 0 0)`,
  down: (p: number) => `inset(0 0 ${100 - p}% 0)`,
};

/**
 * Tracking-in: letter-spacing contracts from `from` to `to` em while fading.
 * Cinematic title entrance with zero translateY tell. (modern style)
 */
export function trackingIn(
  frame: number,
  start: number,
  frames: number,
  fromEm = 0.28,
  toEm = 0.02,
): {opacity: number; letterSpacing: string} {
  const progress = interpolate(frame, [start, start + frames], [0, 1], {...clamp, easing: HOUSE_EASE});
  return {
    opacity: progress,
    letterSpacing: `${interpolate(progress, [0, 1], [fromEm, toEm], clamp)}em`,
  };
}

/**
 * Blur-reveal: opacity + blur + small rise settle together on one overdamped
 * spring. Quietly cinematic, no bounce. Use sparingly (large hero text).
 */
export function blurReveal(
  frame: number,
  fps: number,
  start: number,
  frames: number,
  risePx = 16,
): {opacity: number; filter: string; transform: string} {
  const local = Math.max(0, frame - start);
  const progress = spring({frame: local, fps, config: SPRING_SMOOTH, durationInFrames: frames});
  const opacity = interpolate(progress, [0, 1], [0, 1], clamp);
  const blur = interpolate(progress, [0, 1], [10, 0], clamp);
  const y = interpolate(progress, [0, 1], [risePx, 0], clamp);
  return {opacity, filter: `blur(${blur}px)`, transform: `translateY(${y}px)`};
}

// ---------------------------------------------------------------------------
// Accents (two-phase: draw AFTER the text has settled)
// ---------------------------------------------------------------------------

/** Underline draw progress 0..100 (width %) — starts `afterText` frames late. */
export function underlineDraw(frame: number, start: number, frames: number): number {
  return interpolate(frame, [start, start + frames], [0, 100], {...clamp, easing: HOUSE_EASE});
}

/** Highlight box slide progress 0..100 (width %) behind text. */
export function highlightSlide(frame: number, start: number, frames: number): number {
  return interpolate(frame, [start, start + frames], [0, 100], {...clamp, easing: LINEAR});
}

// ---------------------------------------------------------------------------
// Camera
// ---------------------------------------------------------------------------

/** Linear Ken Burns progress 0..1 — deliberately no easing (steady drift). */
export function kenBurns(frame: number, durationInFrames: number): number {
  return interpolate(frame, [0, durationInFrames], [0, 1], {...clamp, easing: LINEAR});
}

/**
 * Seeded-noise camera drift — smooth organic micro-motion, deterministic.
 * amplitude in px. Uses random() (seeded per frame) smoothed by averaging
 * neighbors so it drifts rather than jitters.
 */
export function cameraDrift(frame: number, seed: string, amplitude: number): {x: number; y: number} {
  if (amplitude <= 0) return {x: 0, y: 0};
  const f = Math.floor(frame / 3); // slow the noise down
  const x = (random(`${seed}-dx-${f}`) - 0.5) * 2 * amplitude;
  const y = (random(`${seed}-dy-${f}`) - 0.5) * 2 * amplitude;
  return {x, y};
}

/**
 * Decaying contained camera shake (crime style) — an event that settles.
 * intensity 0..1; decays to 0 over `frames`.
 */
export function cameraShake(
  frame: number,
  seed: string,
  intensity: number,
  startFrame: number,
  frames: number,
): {x: number; y: number; r: number} {
  const local = frame - startFrame;
  if (local < 0 || local > frames || intensity <= 0) return {x: 0, y: 0, r: 0};
  const decay = 1 - local / frames;
  const amp = intensity * 4 * decay;
  return {
    x: (random(`${seed}-sx-${frame}`) - 0.5) * 2 * amp,
    y: (random(`${seed}-sy-${frame}`) - 0.5) * 2 * amp,
    r: (random(`${seed}-sr-${frame}`) - 0.5) * 0.4 * decay,
  };
}

/** Whole-frame punch-and-settle on a beat (modern style). */
export function punch(frame: number, fps: number, beat: number, amount: number): number {
  const local = Math.max(0, frame - beat);
  const s = spring({frame: local, fps, config: {stiffness: 300, damping: 18, mass: 0.8}});
  return 1 + (1 - s) * (amount - 1);
}

// ---------------------------------------------------------------------------
// Exits — ~30% faster than entrances, easing not spring
// ---------------------------------------------------------------------------

/** Exit fade: 1 → 0 over the last `exit` frames. */
export function exitFade(frame: number, durationInFrames: number, exit: number): number {
  return interpolate(frame, [durationInFrames - exit, durationInFrames - 1], [1, 0], {
    ...clamp,
    easing: HOUSE_EASE,
  });
}

/** Exit fade + small downward drift (the default pro exit). */
export function exitFadeFall(
  frame: number,
  durationInFrames: number,
  exit: number,
  travelPx = 8,
): {opacity: number; transform: string} {
  const progress = interpolate(frame, [durationInFrames - exit, durationInFrames - 1], [0, 1], {
    ...clamp,
    easing: HOUSE_EASE,
  });
  return {opacity: 1 - progress, transform: `translateY(${progress * travelPx}px)`};
}

// ---------------------------------------------------------------------------
// Counters
// ---------------------------------------------------------------------------

/**
 * Count-up value for stat scenes. Same spring drives opacity elsewhere so
 * number and entrance settle together. modern uses SPRING_SNAPPY (clamped).
 */
export function countUp(
  frame: number,
  fps: number,
  start: number,
  frames: number,
  from: number,
  to: number,
  springAllowed: boolean,
): number {
  if (springAllowed) {
    const local = Math.max(0, frame - start);
    const s = spring({frame: local, fps, config: {damping: 120, stiffness: 180, mass: 1}, durationInFrames: frames});
    return interpolate(s, [0, 1], [from, to], clamp);
  }
  return interpolate(frame, [start, start + frames], [from, to], {...clamp, easing: HOUSE_EASE});
}

export {DURATION, dur, motionVocab, normalizeStyleId, useCurrentFrame, useVideoConfig};
