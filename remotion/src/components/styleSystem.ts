/**
 * Global Style System — loads pipeline/intelligence/styles/<id>.json and
 * exposes resolved motion/visual params to every scene component.
 *
 * Mirrors VidRush themes: one global_style drives palette, typography,
 * transitions, grade, and motion rules. Style values trace to
 * docs/GLOBAL_STYLE_RESEARCH.md; frame counts/darken are design decisions.
 */

import crimeStyle from '../../../pipeline/intelligence/styles/crime.json';
import historyStyle from '../../../pipeline/intelligence/styles/history.json';
import ledgerStyle from '../../../pipeline/intelligence/styles/ledger.json';
import modernStyle from '../../../pipeline/intelligence/styles/modern.json';
import minimalistStyle from '../../../pipeline/intelligence/styles/minimalist.json';
import standardStyle from '../../../pipeline/intelligence/styles/standard.json';

export type GlobalStyleId = 'crime' | 'history' | 'ledger' | 'modern' | 'minimalist' | 'standard';

/** Old timeline names → canonical VidRush-parity ids (research doc §3). */
export const LEGACY_ALIASES: Record<string, GlobalStyleId> = {
  documentary: 'history',
  storytelling: 'standard',
  listicle: 'standard',
  explainer: 'minimalist',
  commentary: 'modern',
};

export interface StylePalette {bg: string; text: string; accent: string}
export interface StyleTypography {family: string; weight: number; tracking: string}
export interface StyleGrade {darken: number; vignette: string; grain: number}
export interface StyleTransition {xfade: string; frames: number; chapter_xfade?: string; alt_xfade?: string}
export interface StyleMotion {
  transition: StyleTransition;
  ken_burns_zoom: number;
  wipe_frames: number;
  plate_frames: number;
  hard_titles: boolean;
  allowed_easings: string[];
  spring_allowed: boolean;
}
export interface StyleVisual {
  palette: StylePalette;
  typography: StyleTypography;
  title_animation: string;
  lower_third: string;
  stat_reveal: string;
  grade: StyleGrade;
}
export interface GlobalStyle {
  style_id: GlobalStyleId;
  name: string;
  visual: StyleVisual;
  motion: StyleMotion;
}

const STYLES: Record<GlobalStyleId, GlobalStyle> = {
  crime: crimeStyle as unknown as GlobalStyle,
  history: historyStyle as unknown as GlobalStyle,
  ledger: ledgerStyle as unknown as GlobalStyle,
  modern: modernStyle as unknown as GlobalStyle,
  minimalist: minimalistStyle as unknown as GlobalStyle,
  standard: standardStyle as unknown as GlobalStyle,
};

/** Resolve any accepted style name/alias to its canonical id. */
export function normalizeStyleId(id: string | null | undefined): GlobalStyleId {
  if (!id) return 'standard';
  const key = id.trim().toLowerCase();
  if (key in STYLES) return key as GlobalStyleId;
  if (key in LEGACY_ALIASES) return LEGACY_ALIASES[key];
  return 'standard';
}

/** Load the resolved global style. Unknown/alias names resolve safely. */
export function getGlobalStyle(id: string | null | undefined): GlobalStyle {
  return STYLES[normalizeStyleId(id)];
}

/** Convenience: motion params with legacy-name tolerance. */
export function motionFor(id: string | null | undefined): StyleMotion {
  return getGlobalStyle(id).motion;
}

export function paletteFor(id: string | null | undefined): StylePalette {
  return getGlobalStyle(id).visual.palette;
}

export function gradeFor(id: string | null | undefined): StyleGrade {
  return getGlobalStyle(id).visual.grade;
}

/** Transition seconds (30fps timeline) for render.js xfade mapping. */
export function transitionSecFor(id: string | null | undefined, fps = 30): number {
  return getGlobalStyle(id).motion.transition.frames / fps;
}
