/**
 * Style typography — real font families per global style, loaded via
 * @remotion/google-fonts (blocks render until ready). This replaces the old
 * "Arial everywhere" tell with per-style editorial type.
 *
 * Families chosen from docs/FREE_MOTION_ASSETS.md §5 (all OFL, free commercial).
 * Keep weight lists narrow — every weight is a render-time download.
 */
import {loadFont as loadAnton} from '@remotion/google-fonts/Anton';
import {loadFont as loadArchivo} from '@remotion/google-fonts/Archivo';
import {loadFont as loadIBMPlexMono} from '@remotion/google-fonts/IBMPlexMono';
import {loadFont as loadInter} from '@remotion/google-fonts/Inter';
import {loadFont as loadInstrumentSerif} from '@remotion/google-fonts/InstrumentSerif';
import {loadFont as loadNewsreader} from '@remotion/google-fonts/Newsreader';
import {loadFont as loadSpaceMono} from '@remotion/google-fonts/SpaceMono';
import {loadFont as loadWorkSans} from '@remotion/google-fonts/WorkSans';
import {normalizeStyleId, type GlobalStyleId} from '../styleSystem';

// Eager loads — module-level so webpack bundles them once.
const anton = loadAnton('normal', {weights: ['400'], subsets: ['latin']});
const archivo = loadArchivo('normal', {weights: ['500', '700', '900'], subsets: ['latin']});
const plexMono = loadIBMPlexMono('normal', {weights: ['400', '600'], subsets: ['latin']});
const inter = loadInter('normal', {weights: ['400', '600', '700'], subsets: ['latin']});
const instrumentSerif = loadInstrumentSerif('normal', {weights: ['400'], subsets: ['latin']});
const newsreader = loadNewsreader('normal', {weights: ['500', '600', '700'], subsets: ['latin']});
const spaceMono = loadSpaceMono('normal', {weights: ['400', '700'], subsets: ['latin']});
const workSans = loadWorkSans('normal', {weights: ['400', '500', '600'], subsets: ['latin']});

export interface StyleFonts {
  /** Display/title face — big headlines, stats, hooks. */
  display: string;
  /** Body/subordinate lines, plates, attributions. */
  body: string;
  /** Labels, kickers, dossier stamps — mono where the style calls for it. */
  label: string;
  /** Accent/quote face (may equal body). */
  accent: string;
}

/**
 * Per-style type system:
 *  crime       — Anton condensed punch + Plex Mono dossier labels
 *  history     — Newsreader editorial serif + Space Mono archival stamps
 *  modern      — Archivo grotesque (900 display) + Inter body
 *  minimalist  — Work Sans light/normal everywhere, mono-free
 *  standard    — Archivo display + Inter (approachable editorial)
 */
const FONTS: Record<GlobalStyleId, StyleFonts> = {
  crime: {
    display: anton.fontFamily,
    body: inter.fontFamily,
    label: plexMono.fontFamily,
    accent: newsreader.fontFamily,
  },
  history: {
    display: newsreader.fontFamily,
    body: newsreader.fontFamily,
    label: spaceMono.fontFamily,
    accent: instrumentSerif.fontFamily,
  },
  // ledger — Anton condensed caps + Plex Mono ledger stamps (VidIQ audit:
  // "2-3 huge outlined caps words" + accountability dossier feel).
  ledger: {
    display: anton.fontFamily,
    body: inter.fontFamily,
    label: plexMono.fontFamily,
    accent: newsreader.fontFamily,
  },
  modern: {
    display: archivo.fontFamily,
    body: inter.fontFamily,
    label: inter.fontFamily,
    accent: archivo.fontFamily,
  },
  minimalist: {
    display: workSans.fontFamily,
    body: workSans.fontFamily,
    label: workSans.fontFamily,
    accent: workSans.fontFamily,
  },
  standard: {
    display: archivo.fontFamily,
    body: inter.fontFamily,
    label: inter.fontFamily,
    accent: inter.fontFamily,
  },
};

export function fontsFor(globalStyle: string | null | undefined): StyleFonts {
  return FONTS[normalizeStyleId(globalStyle)];
}
