/**
 * Camera life — organic frame motion from continuous simplex noise.
 * Deterministic (seeded) so multithreaded rendering is frame-identical.
 *
 * Three behaviors:
 *  - drift: slow handheld wander (translate + micro rotate), never still
 *  - shake: decaying impulse after a beat (build → settle)
 *  - punch: whole-frame punch-and-settle on a beat (scale 1 → amount → ~1)
 *
 * Always pair with overscan (scale ≥ 1.03) so motion never reveals edges.
 * Source: docs/REMOTION_AE_TECHNIQUES.md §15, docs/AE_TRENDS_CATALOG.md §14.
 */
import {noise3D} from '@remotion/noise';
import {interpolate, spring} from 'remotion';

const clamp = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};

/**
 * Slow positional float — NOT handheld shake. Real documentary drift is
 * nearly imperceptible: sub-pixel to ~1.5px wander over seconds, and almost
 * no rotation (rotation is what makes drift read as "shaky"). timeScale is
 * very low so the noise evolves slowly. amp in px; rot is capped at ±0.06°.
 */
export function cameraDrift(
  frame: number,
  seed: string,
  amp: number,
  timeScale = 0.04,
): {x: number; y: number; r: number} {
  if (amp <= 0) return {x: 0, y: 0, r: 0};
  const t = frame * timeScale;
  return {
    x: noise3D(`${seed}-dx`, 0, 0, t) * amp,
    y: noise3D(`${seed}-dy`, 0, 0, t) * amp,
    // Rotation is the shake tell — keep it essentially zero for drift.
    r: noise3D(`${seed}-dr`, 0, 0, t * 0.5) * 0.06,
  };
}

/** Dominant direction of an impact kick. Director intent; default 'x' (horizontal hit). */
export type ShakeDir = 'x' | 'y' | 'diag';

/**
 * Impact shake — a single hard directional HIT that settles, NOT jelly.
 *
 * Real AE impact shake (docs/AE_TRENDS_CATALOG.md §14): the camera gets kicked
 * mostly along ONE axis 2–4px, then decays to rest over ~10 frames. It reads as
 * a strike (a blow, a reveal, an explosion), not a wobble. The old isotropic
 * ±0.5° rotation + 5px noise read as "jelly" — this replaces it.
 *
 *  - One dominant axis (dir), the cross-axis gets a much smaller secondary jolt.
 *  - No rotation — rotation is what made it feel cheap.
 *  - A tiny 1-frame horizontal smear (the caller may use it for a blur-ish hit).
 *  - intensity 0..1; the kick peaks at ~2–4px and settles to 0 over `frames`.
 */
export function impactShake(
  frame: number,
  seed: string,
  intensity: number,
  startFrame: number,
  frames: number,
  dir: ShakeDir = 'x',
): {x: number; y: number; r: number; smear: number} {
  const local = frame - startFrame;
  if (local < 0 || local > frames || intensity <= 0) return {x: 0, y: 0, r: 0, smear: 0};

  // Single fast attack → smooth decay to rest (kick, not oscillation).
  // attack over ~2 frames, then exp-ish decay.
  const attack = Math.min(1, local / 2);
  const decay = Math.pow(1 - Math.min(1, local / frames), 2.2);
  const env = attack * decay;

  // Peak travel: 2–4px scaled by intensity.
  const peak = 2 + intensity * 2;
  // Deterministic per-seed kick polarity (+/-) so it doesn't always go the same way.
  const sign = noise3D(`${seed}-sign`, 0, 0, 0) >= 0 ? 1 : -1;
  // Small secondary axis jolt (a hit is never perfectly clean) — much weaker.
  const cross = noise3D(`${seed}-sx2`, 0, 0, frame * 0.7) * 0.35;

  let x = 0;
  let y = 0;
  if (dir === 'x') {
    x = sign * peak * env;
    y = cross * peak * env;
  } else if (dir === 'y') {
    y = sign * peak * env;
    x = cross * peak * env;
  } else {
    // diag — split the hit across both axes.
    x = sign * peak * env * 0.8;
    y = sign * peak * env * 0.6;
  }

  // 1-frame horizontal smear right at the hit (motion-blur-ish). Peaks early, gone fast.
  const smear = local <= 3 ? peak * (1 - local / 4) * 0.5 : 0;

  // No rotation — rotation is the jelly tell.
  return {x, y, r: 0, smear};
}

/**
 * @deprecated Use `impactShake` — the directional kick. Kept so existing call
 * sites compile; now delegates to `impactShake` (no jelly rotation).
 */
export function cameraShake(
  frame: number,
  seed: string,
  intensity: number,
  startFrame: number,
  frames: number,
): {x: number; y: number; r: number} {
  const {x, y, r} = impactShake(frame, seed, intensity, startFrame, frames, 'x');
  return {x, y, r};
}

/** Punch-and-settle scale on a beat. amount 1.04–1.12. */
export function punchZoom(frame: number, fps: number, beatFrame: number, amount: number): number {
  const local = Math.max(0, frame - beatFrame);
  const s = spring({frame: local, fps, config: {stiffness: 260, damping: 20, mass: 0.8}, durationInFrames: 18});
  return 1 + (1 - s) * (amount - 1);
}

/** Overscan so drift/shake never reveals edges. */
export function overscanFor(amp: number): number {
  return 1.02 + Math.min(0.05, Math.abs(amp) * 0.006);
}

// ---------------------------------------------------------------------------
// Eased camera grammar (Phase 7) — kills the "constant-velocity slide" tell.
// ---------------------------------------------------------------------------

/**
 * Ease-out progress 0..1 for a camera move. Real AE keyframes decelerate:
 * fast start, soft landing. `settleFrac` is the fraction of the move spent
 * easing (rest is a slow drift tail). Strong ease-out, no overshoot.
 */
export function easeOutProgress(t: number): number {
  const c = Math.min(1, Math.max(0, t));
  // cubic ease-out
  return 1 - Math.pow(1 - c, 3);
}

/**
 * Cinematic camera move: an eased primary move (zoom/pan) that settles early,
 * then continues as a slow drift so the frame never goes dead-still.
 * Returns a 0..1-ish progress that eases hard then creeps.
 *  - `settleAt` (0..1): when the primary move finishes easing (e.g. 0.4).
 *  - `tail`: extra slow drift after settle (e.g. 0.12 = 12% more travel).
 */
export function easedCameraProgress(
  frame: number,
  durationInFrames: number,
  settleAt = 0.4,
  tail = 0.12,
): number {
  const t = Math.min(1, frame / Math.max(1, durationInFrames));
  if (t <= settleAt) {
    // Primary move eases out across [0, settleAt].
    return easeOutProgress(t / settleAt) * (1 - tail);
  }
  // Drift tail: linear creep from (1-tail) to 1 across the remaining time.
  const tailT = (t - settleAt) / Math.max(1e-6, 1 - settleAt);
  return 1 - tail + tailT * tail;
}
