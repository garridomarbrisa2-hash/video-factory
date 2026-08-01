/**
 * Motion token system — the single source of truth for all animation values.
 *
 * Architecture from the onda registry (github.com/degueba/onda): scene files
 * NEVER invent easings, durations, or spring configs. They pick from this
 * closed vocabulary, scaled per global style. This is what makes a render read
 * as one editorial hand instead of assembled React parts.
 *
 * Values at 30fps. Durations deliberately LONGER than product-UI (0.6–1.5s)
 * because video gives the eye time to follow — there are no user gestures.
 */
import {Easing} from 'remotion';
import {normalizeStyleId} from './styleSystem';

/** Spring configs — overdamped, never bouncy. */
export const SPRING_SMOOTH = {damping: 200, stiffness: 100, mass: 1} as const;
/** Snappier rise for modern stat counters — still clamped, no overshoot past target. */
export const SPRING_SNAPPY = {damping: 120, stiffness: 180, mass: 1} as const;

/** House easing for exits (an exit doesn't settle — never a spring). */
export const HOUSE_EASE = Easing.out(Easing.quad);
/** Linear for editorial wipes / Ken Burns / opacity cuts. */
export const LINEAR = Easing.linear;

/**
 * AE speed-graph equivalents (docs/REMOTION_AE_TECHNIQUES.md §13).
 * Linear stays the default for editorial wipes; these are for ENTRANCES
 * (landings settle, which is what real AE keyframes do). Design decision.
 */
/** AE Easy Ease strong — default entrance curve (fast start, soft landing). */
export const AE_EASE = Easing.bezier(0.25, 0.46, 0.45, 0.94);
/** AE snap/whip — fast in, hard out (punch-zoom landings, whip entrances). */
export const AE_SNAP = Easing.bezier(0.85, 0, 0.15, 1);
/** Gentle expo-out for stat counters and draw-ons. */
export const AE_SETTLE = Easing.bezier(0.16, 1, 0.3, 1);

/** Base duration tokens (frames @30fps), before per-style scaling. */
export const DURATION = {
  instant: 6, // micro shift, accent ticks
  fast: 10, // exits — faster than entrances
  base: 18, // default entrance
  slow: 24, // large entrances / titles
  slower: 30, // scene-scale moves
  hold: 45, // minimum settled hold
} as const;

/** Stagger between sibling elements (frames). */
export const STAGGER = 4;
/** Phrase-level stagger for multi-line text beats. */
export const PHRASE_STAGGER = 8;

/**
 * Per-style motion vocabulary. The differentiators are duration scale,
 * travel distance, spring permission, camera behavior, and accent style.
 * This is the motion half of each VidRush theme.
 */
export interface MotionVocab {
  /** Multiply all durations by this (crime slower/heavier, modern faster). */
  tempo: number;
  /** Ken Burns zoom range for VIDEO bg (kept subtle, 1.03–1.06). */
  ken: number;
  /** Ken Burns zoom range for a STILL bg pushed/panned (visible, 1.10–1.16).
   *  A still needs a readable move or it reads frozen; this is the default
   *  magnitude when the director picks `push`/`pan`. */
  stillKen: number;
  /** Camera drift amplitude in px (0 = locked-off/static). */
  drift: number;
  /** Ceiling for director-requested impact shake (0 = style forbids shake). */
  max_shake: number;
  /** Whole-frame punch-in amount on key beats (1 = none, 1.04 = 4%). */
  punch: number;
  /** Whether modern-style springs are allowed (stat counters only). */
  springAllowed: boolean;
  /** Accent behavior on key phrases: 'underline' | 'highlight' | 'drawon' | 'none'. */
  accentMode: 'underline' | 'highlight' | 'drawon' | 'none';
  /** Title entrance: 'mask' | 'kinetic' | 'tracking' | 'cut'. */
  titleMode: 'mask' | 'kinetic' | 'tracking' | 'cut';
  /** Exit window (frames) at scene end. */
  exit: number;
  /** Grain overlay opacity (0 = off). */
  grain: number;
  /** Light-leak frequency: 0 = never, N = every Nth cut (rest are plain xfade). */
  leakEvery: number;
}

/**
 * Still-motion intent (director's per-scene choice for a bg_image still).
 * The user rejected jittery background drift/shake (headache) — so stills get
 * ONE smooth, deliberate, single-direction move, never wobble:
 *   push     — slow eased Ken Burns push-in (default; the safest motion)
 *   pan      — slow eased lateral/vertical slide
 *   parallax — near-plane differential drift (2.5D), background holds
 *   light    — living-light sweep + dust over a held frame
 *   hold     — locked frame; ONLY justified for a document/map artifact
 * The renderer guarantees a bg_image scene never sits frozen: anything other
 * than an explicit `hold` produces visible, smooth motion.
 */
export type StillMotion = 'push' | 'pan' | 'parallax' | 'light' | 'hold';

/** Phase 7 presence vocab — how much depth parallax + living light per style. */
export interface PresenceVocab {
  /** Parallax master zoom (1.0 = none). */
  pZoom: number;
  /** Parallax pan travel % on the near plane. */
  pPan: number;
  /** Near-vs-far scale separation. */
  pSeparation: number;
  /** Near-plane micro-rotate degrees. */
  pRotate: number;
  /** Volumetric light sweep 0..1. */
  lightSweep: number;
  /** Dust mote count. */
  lightDust: number;
  /** Beat flare 0..1. */
  lightFlare: number;
  /** Warm light (true) vs cool (false). */
  lightWarm: boolean;
}

/** Per-style presence. The point is DIFFERENCE:
 *  crime — cool, hard light, restrained parallax (tension is stillness)
 *  history — warm volumetric dust, slow gentle parallax (archive float)
 *  modern — crisp, subtle light, tight parallax
 *  minimalist — almost nothing; only the content breathes
 *  standard — the safe warm middle
 */
export function presenceVocab(globalStyle: string | null | undefined): PresenceVocab {
  const id = normalizeStyleId(globalStyle);
  switch (id) {
    case 'crime':
      return {pZoom: 1.05, pPan: 2.0, pSeparation: 0.05, pRotate: 0.2, lightSweep: 0.5, lightDust: 10, lightFlare: 0.4, lightWarm: false};
    case 'history':
      return {pZoom: 1.05, pPan: 2.6, pSeparation: 0.07, pRotate: 0.25, lightSweep: 0.7, lightDust: 10, lightFlare: 0.5, lightWarm: true};
    case 'ledger':
      // Near-still frame — the figures are meant to be *read*, not danced under.
      return {pZoom: 1.04, pPan: 2.0, pSeparation: 0.05, pRotate: 0.15, lightSweep: 0.5, lightDust: 8, lightFlare: 0.4, lightWarm: true};
    case 'modern':
      return {pZoom: 1.04, pPan: 2.0, pSeparation: 0.05, pRotate: 0.15, lightSweep: 0.4, lightDust: 8, lightFlare: 0.5, lightWarm: false};
    case 'minimalist':
      return {pZoom: 1.02, pPan: 1.2, pSeparation: 0.03, pRotate: 0.05, lightSweep: 0.2, lightDust: 0, lightFlare: 0, lightWarm: true};
    case 'standard':
    default:
      return {pZoom: 1.05, pPan: 2.2, pSeparation: 0.06, pRotate: 0.2, lightSweep: 0.55, lightDust: 8, lightFlare: 0.4, lightWarm: true};
  }
}

/**
 * Camera grammar per style — the point is DIFFERENCE, not uniform motion.
 *  crime      — nearly locked-off. Tension comes from stillness, not shake.
 *  history    — slow constant drift (the archive-camera float).
 *  modern     — static between beats; energy comes from punch accents only.
 *  minimalist — fully static. Nothing moves but the content.
 *  standard   — gentle drift, the safe middle.
 */
export function motionVocab(globalStyle: string | null | undefined): MotionVocab {
  const id = normalizeStyleId(globalStyle);
  switch (id) {
    case 'crime':
      // HEAVY AND STILL. Tension is a locked camera you can't look away from.
      return {
        tempo: 1.15,
        ken: 1.04,
        stillKen: 1.14,
        drift: 0.15,
        max_shake: 0.8,
        punch: 1.0,
        springAllowed: false,
        accentMode: 'underline',
        titleMode: 'kinetic',
        exit: 12,
        grain: 0.08,
        leakEvery: 3,
      };
    case 'history':
      // Slow archival float — the only style where constant drift is right.
      return {
        tempo: 1.3,
        ken: 1.04,
        stillKen: 1.14,
        drift: 0.5,
        max_shake: 0,
        punch: 1.0,
        springAllowed: false,
        accentMode: 'underline',
        titleMode: 'kinetic',
        exit: 14,
        grain: 0.08,
        leakEvery: 0,
      };
    case 'ledger':
      // Accountability desk — near-locked, slow tempo, underline on figures.
      return {
        tempo: 1.2,
        ken: 1.04,
        stillKen: 1.12,
        drift: 0.2,
        max_shake: 0.6,
        punch: 1.02,
        springAllowed: false,
        accentMode: 'underline',
        titleMode: 'mask',
        exit: 12,
        grain: 0.06,
        leakEvery: 3,
      };
    case 'modern':
      // Static frame; energy lives in the stat punch, not camera wander.
      return {
        tempo: 0.9,
        ken: 1.03,
        stillKen: 1.12,
        drift: 0,
        max_shake: 0.5,
        punch: 1.05,
        springAllowed: true,
        accentMode: 'highlight',
        titleMode: 'kinetic',
        exit: 8,
        grain: 0.02,
        leakEvery: 2,
      };
    case 'minimalist':
      // Fully static. Only the content moves.
      return {
        tempo: 1.0,
        ken: 1.02,
        stillKen: 1.10,
        drift: 0,
        max_shake: 0,
        punch: 1.0,
        springAllowed: false,
        accentMode: 'none',
        titleMode: 'cut',
        exit: 10,
        grain: 0,
        leakEvery: 0,
      };
    case 'standard':
    default:
      // Gentle drift, light grain, occasional leak. The safe editorial middle.
      return {
        tempo: 1.0,
        ken: 1.04,
        stillKen: 1.14,
        drift: 0.25,
        punch: 1.0,
        springAllowed: false,
        accentMode: 'underline',
        titleMode: 'kinetic',
        exit: 10,
        grain: 0.05,
        leakEvery: 3,
      };
  }
}

/** Per-style caps for signature moves (Phase 8, P5) — intensity ceilings, NOT
 *  defaults. A move fires ONLY when the director calls it; these cap how strong
 *  it may be so a style never loses its editorial hand. 0 = the style forbids it. */
export interface SignatureCaps {
  /** GlitchBeat (§9 RGB-split + slice shear): max intensity 0..1, 0 = forbidden. */
  glitch: number;
  /** WhipPan (§5 directional-blur cut): max blur px, 0 = forbidden. */
  whipPan: number;
  /** CrimeBoard (§18 pinned collage + string): max items, 0 = forbidden. */
  crimeBoard: number;
  /** ChartDrawOn (§20 data draw-on): 1 = allowed, 0 = forbidden. */
  chart: number;
  /** ArchivalPulse (§11 scratch/dust era overlay): max intensity 0..1. */
  archival: number;
  /** HalftoneDoc (§12 print halftone on documents): 1 = allowed, 0 = forbidden. */
  halftone: number;
}

/** The point is DIFFERENCE: each genre's signature moves are what make it read
 *  instantly. minimalist/standard forbid nearly all — restraint IS their genre. */
export function signatureCaps(globalStyle: string | null | undefined): SignatureCaps {
  const id = normalizeStyleId(globalStyle);
  switch (id) {
    case 'crime':
      // glitch (the twist), crime-board (evidence), halftone docs, archival tape.
      return {glitch: 1, whipPan: 0, crimeBoard: 6, chart: 0, archival: 0.5, halftone: 1};
    case 'history':
      // archival pulse + era wipe; NO glitch/whip (wrong era entirely).
      return {glitch: 0, whipPan: 0, crimeBoard: 0, chart: 0, archival: 1, halftone: 1};
    case 'modern':
      // whip-pan + chart draw-on + kinetic data; NO glitch/halftone (wrong register).
      return {glitch: 0, whipPan: 24, crimeBoard: 0, chart: 1, archival: 0, halftone: 0};
    case 'ledger':
      // plunging red chart is the SIGNATURE. archival for old docs, halftone for
      // budget line-items. NO glitch/whip — wrong register for the desk.
      return {glitch: 0, whipPan: 0, crimeBoard: 0, chart: 1, archival: 0.7, halftone: 1};
    case 'minimalist':
      // nothing. restraint is the move.
      return {glitch: 0, whipPan: 0, crimeBoard: 0, chart: 0, archival: 0, halftone: 0};
    case 'standard':
    default:
      // the safe middle: a light chart only, nothing flashy.
      return {glitch: 0, whipPan: 0, crimeBoard: 0, chart: 1, archival: 0, halftone: 0};
  }
}

/** Scale a duration token by the style tempo. */
export function dur(token: number, tempo: number): number {
  return Math.max(2, Math.round(token * tempo));
}
