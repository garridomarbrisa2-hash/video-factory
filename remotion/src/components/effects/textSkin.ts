/**
 * Per-style TEXT GRAMMAR (text skins) — replaces the single shared black
 * LowerThirdPlate box that made every video look the same (Ep1 pilot bug).
 *
 * Each global style gets its own lower-third / title treatment so the text
 * reads as ONE editorial hand per genre, not a generic box:
 *   crime      — hard dossier: near-opaque dark plate, mono kicker stamp, accent bar
 *   history    — archival plate: warm parchment-tinted wash, thin double rule, serif
 *   modern     — clean kinetic: NO plate, accent highlight chip under the phrase
 *   minimalist — bare: no plate at all, generous tracking, quiet weight
 *   standard   — soft editorial: translucent dark plate, accent edge
 *
 * Scenes read the skin; they never hand-roll plate CSS. This is the typography
 * half of each VidRush theme (motion half lives in tokens.motionVocab).
 */
import type React from 'react';
import {normalizeStyleId} from '../styleSystem';
import {fontsFor} from './fonts';

export type PlateKind = 'solid' | 'archival' | 'chip' | 'none' | 'soft';

export interface TextSkin {
  /** Which lower-third container to render. */
  plate: PlateKind;
  /** Container background (CSS background value), or 'transparent'. */
  plateBg: string;
  /** Accent edge: 'bar' (left block), 'rule' (thin line), 'double-rule', 'none'. */
  edge: 'bar' | 'rule' | 'double-rule' | 'none';
  /** Kicker/label treatment: mono stamp, serif smallcaps, or plain tracked caps. */
  kicker: 'mono-stamp' | 'serif-smallcaps' | 'tracked-caps';
  /** Highlight chip under the emphasis phrase (modern). */
  highlightChip: boolean;
  /** Padding inside the plate container. */
  pad: string;
  /** Extra letter-tracking applied to the kicker. */
  kickerTracking: string;
}

const SKINS: Record<string, TextSkin> = {
  crime: {
    plate: 'solid',
    plateBg: 'rgba(8,10,14,0.92)',
    edge: 'bar',
    kicker: 'mono-stamp',
    highlightChip: false,
    pad: '18px 28px 18px 22px',
    kickerTracking: '0.22em',
  },
  history: {
    plate: 'archival',
    // Warm parchment wash — NOT a black box. Reads as an archival caption card.
    plateBg:
      'linear-gradient(180deg, rgba(38,30,18,0.72) 0%, rgba(24,18,10,0.78) 100%)',
    edge: 'double-rule',
    kicker: 'serif-smallcaps',
    highlightChip: false,
    pad: '16px 26px 16px 20px',
    kickerTracking: '0.28em',
  },
  // ledger — VidIQ audit: near-black plate, deep red accent bar, gold mono
  // stamp kicker. Reads as the desk ledger, not a museum caption.
  ledger: {
    plate: 'solid',
    plateBg: 'rgba(8,6,4,0.94)',
    edge: 'bar',
    kicker: 'mono-stamp',
    highlightChip: false,
    pad: '18px 28px 18px 22px',
    kickerTracking: '0.24em',
  },
  modern: {
    plate: 'chip',
    plateBg: 'transparent',
    edge: 'none',
    kicker: 'tracked-caps',
    highlightChip: true,
    pad: '0',
    kickerTracking: '0.18em',
  },
  minimalist: {
    plate: 'none',
    plateBg: 'transparent',
    edge: 'none',
    kicker: 'tracked-caps',
    highlightChip: false,
    pad: '0',
    kickerTracking: '0.32em',
  },
  standard: {
    plate: 'soft',
    plateBg: 'rgba(0,0,0,0.68)',
    edge: 'rule',
    kicker: 'tracked-caps',
    highlightChip: false,
    pad: '18px 26px 18px 22px',
    kickerTracking: '0.18em',
  },
};

/** Resolve the text skin for a global style (alias-tolerant). */
export function textSkinFor(globalStyle: string | null | undefined): TextSkin {
  return SKINS[normalizeStyleId(globalStyle)] ?? SKINS.standard;
}

/** Container style for the plate, per skin. `accent` is the style accent color. */
export function plateStyle(
  skin: TextSkin,
  accent: string,
  maxWidth: number | string,
): React.CSSProperties {
  if (skin.plate === 'none' || skin.plate === 'chip') {
    return {maxWidth, background: 'transparent'};
  }
  const base: React.CSSProperties = {
    maxWidth,
    background: skin.plateBg,
    padding: skin.pad,
  };
  if (skin.edge === 'bar') {
    base.borderLeft = `4px solid ${accent}`;
  } else if (skin.edge === 'rule') {
    base.borderLeft = `2px solid ${accent}`;
  } else if (skin.edge === 'double-rule') {
    // Archival: thin top+bottom rules frame the caption like a museum plate.
    base.borderTop = `1px solid ${accent}`;
    base.borderBottom = `1px solid ${accent}`;
  }
  return base;
}

/** Kicker (label) style per skin. */
export function kickerStyle(
  skin: TextSkin,
  accent: string,
  globalStyle: string | null | undefined,
): React.CSSProperties {
  const fonts = fontsFor(globalStyle);
  const base: React.CSSProperties = {
    color: accent,
    fontSize: 16,
    fontWeight: 600,
    letterSpacing: skin.kickerTracking,
    textTransform: 'uppercase',
    textShadow: '0 1px 4px rgba(0,0,0,0.6)',
  };
  if (skin.kicker === 'mono-stamp') {
    return {
      ...base,
      fontFamily: fonts.label,
      // Dossier stamp: boxed mono kicker.
      display: 'inline-block',
      border: `1px solid ${accent}`,
      padding: '3px 8px',
    };
  }
  if (skin.kicker === 'serif-smallcaps') {
    return {...base, fontFamily: fonts.label, fontWeight: 400};
  }
  return {...base, fontFamily: fonts.label};
}
