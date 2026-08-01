/**
 * AE / Premiere motion language — not CSS product UI.
 * docs/PRO_EDIT_STYLE.md
 *
 * Style params now come from the global style system
 * (pipeline/intelligence/styles/*.json via styleSystem.ts).
 * The old 5-name switch is gone; legacy names resolve through aliases.
 */
import {Easing} from 'remotion';
import {getGlobalStyle, normalizeStyleId, type GlobalStyleId} from './styleSystem';

/** Legacy edit-style names (kept so old scene props keep compiling). */
export type EditStyle =
  | 'documentary'
  | 'storytelling'
  | 'listicle'
  | 'explainer'
  | 'commentary'
  | GlobalStyleId;

/** Linear only for editorial opacity / wipes */
export const linear = Easing.linear;
export const easeLinear = Easing.linear;

export const clamp = {
  extrapolateLeft: 'clamp' as const,
  extrapolateRight: 'clamp' as const,
};

export interface MotionParams {
  wipeFrames: number;
  plateFrames: number;
  darken: number;
  kenZoom: number;
  hardTitles: boolean;
  springAllowed: boolean;
}

/** Style-driven motion params — from styles/<id>.json, any alias accepted. */
export function styleParams(style: EditStyle | string = 'standard'): MotionParams {
  const s = getGlobalStyle(normalizeStyleId(style));
  return {
    wipeFrames: s.motion.wipe_frames,
    plateFrames: s.motion.plate_frames,
    darken: s.visual.grade.darken,
    kenZoom: s.motion.ken_burns_zoom,
    hardTitles: s.motion.hard_titles,
    springAllowed: s.motion.spring_allowed,
  };
}
