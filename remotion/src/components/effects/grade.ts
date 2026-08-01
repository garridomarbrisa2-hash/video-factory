/**
 * Cinematic grade looks — per-style color treatment that replaces the old
 * one-size-fits-all "contrast(1.08) saturate(1.12)" filter.
 *
 * Each look is a CSS filter chain (compositor-applied by Chrome, no canvas
 * cost) + optional duotone overlay. Values are design decisions informed by
 * docs/AE_TRENDS_CATALOG.md (texture over polish; per-style identity).
 */
import {normalizeStyleId, type GlobalStyleId} from '../styleSystem';

export interface GradeLook {
  /** Filter applied to the background media layer. */
  filter: string;
  /** Optional color wash composited over the media (blend-mode). */
  wash?: {background: string; blend: string; opacity: number};
}

/**
 *  crime       — silver-desat, cold shadows, crushed blacks (Fincher-ish)
 *  history     — warm sepia print, lifted blacks, soft contrast
 *  modern      — clean punchy teal-leaning digital
 *  minimalist  — neutral bright, airy, low contrast
 *  standard    — balanced cinematic (mild contrast + saturation)
 */
const LOOKS: Record<GlobalStyleId, GradeLook> = {
  crime: {
    filter: 'contrast(1.18) saturate(0.72) brightness(0.9) sepia(0.12) hue-rotate(-8deg)',
    wash: {background: 'linear-gradient(180deg, rgba(10,14,20,0.10), rgba(4,6,10,0.28))', blend: 'multiply', opacity: 1},
  },
  history: {
    filter: 'contrast(1.05) saturate(0.82) brightness(0.97) sepia(0.28)',
    wash: {background: 'linear-gradient(180deg, rgba(64,44,18,0.10), rgba(30,20,8,0.22))', blend: 'overlay', opacity: 1},
  },
  // ledger — near-black bg, crushed shadows, restrained sat. VidIQ audit:
  // "near-black backgrounds, deep red + gold". Charcoal-warm wash.
  ledger: {
    filter: 'contrast(1.2) saturate(0.78) brightness(0.88) sepia(0.14)',
    wash: {background: 'linear-gradient(180deg, rgba(28,18,10,0.14), rgba(8,6,4,0.34))', blend: 'multiply', opacity: 1},
  },
  modern: {
    filter: 'contrast(1.12) saturate(1.18) brightness(0.98)',
    wash: {background: 'linear-gradient(180deg, rgba(12,26,30,0.06), rgba(8,18,24,0.16))', blend: 'multiply', opacity: 1},
  },
  minimalist: {
    filter: 'contrast(0.98) saturate(1.0) brightness(1.04)',
  },
  standard: {
    filter: 'contrast(1.1) saturate(1.12) brightness(0.96)',
  },
};

export function gradeLookFor(globalStyle: string | null | undefined): GradeLook {
  return LOOKS[normalizeStyleId(globalStyle)];
}

// ---------------------------------------------------------------------------
// Sculpted grade (Phase 7) — split-tone + filmic contrast + focal depth.
// A flat filter chain reads as "printed slide". Real grades SCULPT: shadows
// lifted toward a tint, highlights toward another (split-tone), a filmic
// S-curve for contrast, and a focal plane so the subject separates.
// ---------------------------------------------------------------------------

export interface SculptGrade {
  /** Filmic-ish filter applied to the media (stronger than LOOKS). */
  filter: string;
  /** Shadow tint (CSS rgb) + strength — lifts/cools the blacks. */
  shadowTint: {color: string; strength: number};
  /** Highlight tint (CSS rgb) + strength — warms/cools the lights. */
  highlightTint: {color: string; strength: number};
  /** Focal separation: edge blur px + edge desat (0 = off). */
  focal: {edgeBlur: number; edgeDesat: number; centerKeep: number};
}

/**
 * Per-style sculpted grade. Design decisions from PRO_EDIT_STYLE + AE trends:
 *  crime      — cold lifted shadows, desat silver mids, hard S-curve
 *  history    — warm lifted shadows, golden highlights, gentle curve
 *  modern     — clean, slight teal shadows, crisp highlights, punchy curve
 *  minimalist — neutral, airy, almost no curve or tint
 *  standard   — balanced warm-neutral, moderate curve
 */
const SCULPT: Record<GlobalStyleId, SculptGrade> = {
  crime: {
    filter: 'contrast(1.22) saturate(0.68) brightness(0.92)',
    shadowTint: {color: 'rgb(14,20,28)', strength: 0.28},
    highlightTint: {color: 'rgb(200,210,220)', strength: 0.08},
    focal: {edgeBlur: 3, edgeDesat: 0.12, centerKeep: 0.62},
  },
  history: {
    filter: 'contrast(1.12) saturate(0.92) brightness(0.98) sepia(0.18)',
    shadowTint: {color: 'rgb(46,30,14)', strength: 0.24},
    highlightTint: {color: 'rgb(255,224,170)', strength: 0.14},
    focal: {edgeBlur: 3.5, edgeDesat: 0.1, centerKeep: 0.6},
  },
  // ledger — crushed blacks, warm-gold highlights (ledger ink), hard S-curve.
  ledger: {
    filter: 'contrast(1.24) saturate(0.82) brightness(0.9) sepia(0.1)',
    shadowTint: {color: 'rgb(12,10,8)', strength: 0.32},
    highlightTint: {color: 'rgb(255,224,160)', strength: 0.14},
    focal: {edgeBlur: 3.5, edgeDesat: 0.1, centerKeep: 0.62},
  },
  modern: {
    filter: 'contrast(1.16) saturate(1.12) brightness(0.99)',
    shadowTint: {color: 'rgb(10,24,28)', strength: 0.18},
    highlightTint: {color: 'rgb(210,240,244)', strength: 0.08},
    focal: {edgeBlur: 2, edgeDesat: 0.06, centerKeep: 0.66},
  },
  minimalist: {
    filter: 'contrast(1.02) saturate(1.0) brightness(1.03)',
    shadowTint: {color: 'rgb(20,20,20)', strength: 0.1},
    highlightTint: {color: 'rgb(255,255,255)', strength: 0.04},
    focal: {edgeBlur: 0, edgeDesat: 0, centerKeep: 1},
  },
  standard: {
    filter: 'contrast(1.14) saturate(1.08) brightness(0.97)',
    shadowTint: {color: 'rgb(24,20,16)', strength: 0.16},
    highlightTint: {color: 'rgb(255,236,210)', strength: 0.08},
    focal: {edgeBlur: 2.5, edgeDesat: 0.08, centerKeep: 0.64},
  },
};

export function sculptGradeFor(globalStyle: string | null | undefined): SculptGrade {
  return SCULPT[normalizeStyleId(globalStyle)];
}

// ---------------------------------------------------------------------------
// Per-scene grade intent (Phase 8, P7) — the director signposts era/mood for ONE
// scene without leaving the global style. The override is a MEANING (archival =
// old footage, clean = present day, noir = hard crime, sepia = warm history,
// halftone = print/document), mapped onto the style's palette so the scene still
// belongs to the film. Style owns how strong; the director owns whether/where.
// ---------------------------------------------------------------------------

export type GradeOverride = 'archival' | 'clean' | 'noir' | 'sepia' | 'halftone';

export interface ResolvedGrade {
  /** Media filter chain for this scene. */
  filter: string;
  /** Optional wash overlay (null = none). */
  wash: GradeLook['wash'] | null;
  /** Grain opacity multiplier (1 = style default). */
  grain: number;
  /** Drive the archival scratch/dust overlay (0 = off). */
  archival: number;
}

/** era/mood intensity per style — how far the style lets an override push it.
 *  minimalist/standard stay restrained; crime/history lean in. */
const OVERRIDE_WEIGHT: Record<GlobalStyleId, number> = {
  crime: 1.0,
  history: 1.0,
  ledger: 1.0,
  modern: 0.7,
  minimalist: 0.4,
  standard: 0.7,
};

/**
 * Resolve a per-scene grade override onto the global style. Returns the base
 * look unchanged when no override is set. `halftone` is handled by the document
 * scene's dot screen (it doesn't change the media filter), so here it only
 * desaturates toward print.
 */
export function resolveGrade(
  globalStyle: string | null | undefined,
  override: GradeOverride | string | null | undefined,
): ResolvedGrade {
  const styleId = normalizeStyleId(globalStyle);
  const base = gradeLookFor(styleId);
  const w = OVERRIDE_WEIGHT[styleId];
  const none: ResolvedGrade = {filter: base.filter, wash: base.wash ?? null, grain: 1, archival: 0};
  if (!override) return none;

  switch (override) {
    case 'archival':
      // Old-footage look: heavier sepia/soft-contrast print + scratch/dust overlay.
      return {
        filter: `contrast(1.02) saturate(${0.7 - 0.1 * w}) brightness(0.96) sepia(${0.3 + 0.25 * w})`,
        wash: {background: 'linear-gradient(180deg, rgba(70,48,20,0.14), rgba(34,22,8,0.26))', blend: 'overlay', opacity: 1},
        grain: 1 + 0.8 * w,
        archival: 0.5 * w,
      };
    case 'clean':
      // Present-day / modern-doc: neutralize the style's character toward crisp
      // neutral digital (drops sepia/desat toward a bright, true-color read).
      return {
        filter: 'contrast(1.1) saturate(1.08) brightness(1.0)',
        wash: null,
        grain: Math.max(0.3, 1 - 0.5 * w),
        archival: 0,
      };
    case 'noir':
      // Hard crime: crush blacks, cold desat, deep shadow wash.
      return {
        filter: `contrast(${1.2 + 0.1 * w}) saturate(${0.6 - 0.08 * w}) brightness(0.86) sepia(0.1) hue-rotate(-10deg)`,
        wash: {background: 'linear-gradient(180deg, rgba(6,10,16,0.16), rgba(2,4,8,0.4))', blend: 'multiply', opacity: 1},
        grain: 1 + 0.5 * w,
        archival: 0,
      };
    case 'sepia':
      // Warm history print: gentle sepia + lifted blacks (no scratch — the clean
      // cousin of archival).
      return {
        filter: `contrast(1.05) saturate(0.82) brightness(0.98) sepia(${0.24 + 0.18 * w})`,
        wash: {background: 'linear-gradient(180deg, rgba(64,44,18,0.10), rgba(30,20,8,0.2))', blend: 'overlay', opacity: 1},
        grain: 1,
        archival: 0,
      };
    case 'halftone':
      // Print/document: desaturate toward newsprint; the dot screen itself is
      // drawn by the document scene (HalftoneDoc), not a filter.
      return {
        filter: `contrast(1.12) saturate(${0.5 - 0.1 * w}) brightness(1.0)`,
        wash: null,
        grain: 1 + 0.3 * w,
        archival: 0,
      };
    default:
      return none;
  }
}
