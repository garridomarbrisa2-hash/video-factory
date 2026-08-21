/**
 * Automatic effect selection — the registry that closes the gap HyperFrames
 * integration was meant to fill: a genuine (scene type × energy × style) →
 * effect lookup, instead of each signature move being hand-wired into one
 * scene file. Selection is a PURE, deterministic function of scene metadata
 * (never random, never LLM) so a re-render is reproducible and so batch
 * mode — where every scene renders as an isolated Remotion process
 * (render.js renderSceneClip) — needs no shared/cross-process state to
 * avoid repeating an effect: `pickEffect` recomputes the previous 1-2
 * scenes' picks internally (see `pickEffect` below) instead of reading them
 * from anywhere.
 *
 * 15 of the entries below are ports of HyperFrames registry components
 * (github.com/heygen-com/hyperframes, Apache-2.0) — see
 * imported/*.tsx headers and pipeline/config/hyperframes_catalog.json for
 * provenance. The rest register EXISTING Video Factory effects so the
 * system is genuinely choosing from the full available pool, not just the
 * new ones.
 */
import type {ComponentType} from 'react';
import type {GlobalStyleId} from '../styleSystem';
import {MaskLineReveal, WordPop, TrackingTitle} from './typography';
import {TitleCardCalm, TitleCardLockup, LetterTrackingReveal} from './imported/titles';
import {PerWordRise, ScrambleReveal} from './imported/text';
import {CountUpNumber, NumberWheel} from './imported/numbers';
import {MarkerHighlight, InlineHighlight, ShimmerSweep} from './imported/highlights';
import {PushInReveal, PullBackReveal} from './imported/camera';
import {DirectionalWipe, ZoomThroughTransition, BeforeAfterWipe} from './imported/transitions';
import {InlineCountUp, ClassicSplitMarker} from './nativeAdapters';

export type EffectCategory = 'title' | 'text' | 'number' | 'highlight' | 'camera' | 'transition';
export type SceneEnergy = 'low' | 'mid' | 'high';

export interface EffectDef {
  /** Stable id — also the anti-repeat identity. */
  id: string;
  category: EffectCategory;
  /** hyperframes registry item name this was ported from, or 'native' for a pre-existing Video Factory effect. */
  source: string;
  Component: ComponentType<any>;
  /** Scene types this effect suits. Omit = fits any scene type in its category. */
  sceneTypes?: string[];
  /** Energies this effect suits. Omit = fits any energy. */
  energies?: SceneEnergy[];
  /** Styles this effect is especially at home in (scoring boost, not exclusive). */
  styles?: GlobalStyleId[];
}

export const EFFECT_CATALOG: EffectDef[] = [
  // --- title ---------------------------------------------------------------
  {id: 'mask-line-reveal', category: 'title', source: 'native', Component: MaskLineReveal},
  {id: 'titlecard-calm', category: 'title', source: 'titlecard-calm', Component: TitleCardCalm, energies: ['low', 'mid'], styles: ['minimalist', 'standard']},
  {id: 'titlecard-lockup', category: 'title', source: 'titlecard-lockup', Component: TitleCardLockup, sceneTypes: ['intro', 'outro'], styles: ['modern', 'standard']},
  {id: 'letter-tracking-reveal', category: 'title', source: 'tracking-in', Component: LetterTrackingReveal, styles: ['modern', 'crime']},

  // --- text ------------------------------------------------------------------
  {id: 'word-pop', category: 'text', source: 'native', Component: WordPop},
  {id: 'tracking-title', category: 'text', source: 'native', Component: TrackingTitle, styles: ['modern']},
  {id: 'per-word-rise', category: 'text', source: 'per-word-rise', Component: PerWordRise, energies: ['mid', 'high']},
  {id: 'scramble-reveal', category: 'text', source: 'scramble-reveal', Component: ScrambleReveal, styles: ['crime', 'modern'], energies: ['mid', 'high']},

  // --- number ------------------------------------------------------------------
  {id: 'inline-count-up', category: 'number', source: 'native', Component: InlineCountUp},
  {id: 'count-up-number', category: 'number', source: 'count-up', Component: CountUpNumber},
  {id: 'number-wheel', category: 'number', source: 'number-wheel', Component: NumberWheel, styles: ['modern', 'standard']},

  // --- highlight ---------------------------------------------------------------
  {id: 'marker-highlight', category: 'highlight', source: 'marker-highlight', Component: MarkerHighlight, styles: ['history', 'standard', 'minimalist']},
  {id: 'inline-highlight', category: 'highlight', source: 'inline-highlight', Component: InlineHighlight, styles: ['modern', 'standard']},
  {id: 'shimmer-sweep', category: 'highlight', source: 'shimmer-sweep', Component: ShimmerSweep, energies: ['high'], styles: ['modern']},

  // --- camera ------------------------------------------------------------------
  {id: 'push-in-reveal', category: 'camera', source: 'push-in', Component: PushInReveal, energies: ['mid', 'high']},
  {id: 'pull-back-reveal', category: 'camera', source: 'pull-back-reveal', Component: PullBackReveal, sceneTypes: ['stat', 'quote']},

  // --- transition (intra-scene content entrance — never cross-clip; see file header) ---
  // No sceneTypes restriction: these two are generic children-wrappers, safe
  // for any scene, and act as the universal fallback pool for 'transition'.
  {id: 'directional-wipe', category: 'transition', source: 'directional-wipe', Component: DirectionalWipe, styles: ['crime', 'modern']},
  {id: 'zoom-through', category: 'transition', source: 'zoom-through-transition', Component: ZoomThroughTransition, energies: ['high']},
  // These two take before/after (not children) — hard-restricted to comparison
  // scenes, which call pickEffect() directly and branch on .id rather than
  // rendering the Component through AutoWrapEffect. See poolFor()'s hard
  // sceneTypes partition, which keeps them out of every other scene's pool.
  {id: 'before-after-wipe', category: 'transition', source: 'before-after-wipe', Component: BeforeAfterWipe, sceneTypes: ['comparison']},
  {id: 'classic-comparison-split', category: 'transition', source: 'native', Component: ClassicSplitMarker, sceneTypes: ['comparison']},
];

export interface EffectContext {
  sceneType: string;
  energy?: SceneEnergy;
  style: GlobalStyleId;
  /** Scene index within the episode — the anti-repeat + rotation key. */
  sceneIndex: number;
}

/** Small deterministic string hash (FNV-1a) — no Math.random anywhere, so
 *  picks are reproducible across renders and across the isolated per-scene
 *  Remotion processes render.js spawns in batch mode. */
function hash(input: string): number {
  let h = 0x811c9dc5;
  for (let i = 0; i < input.length; i++) {
    h ^= input.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return h >>> 0;
}

function poolFor(category: EffectCategory, ctx: Pick<EffectContext, 'sceneType' | 'energy'>): EffectDef[] {
  const all = EFFECT_CATALOG.filter((e) => e.category === category);
  // sceneTypes is a HARD partition for categories whose components have
  // incompatible prop shapes across entries (e.g. 'transition': BeforeAfterWipe
  // takes before/after, not children) — never widen past it to the full
  // category, only ever to the scene-type-agnostic subset (see below).
  const bySceneType = all.filter((e) => !e.sceneTypes || e.sceneTypes.includes(ctx.sceneType));
  const narrowed = bySceneType.filter((e) => !e.energies || !ctx.energy || e.energies.includes(ctx.energy));
  if (narrowed.length) return narrowed;
  if (bySceneType.length) return bySceneType; // relax the energy filter first
  // Nothing declares this scene type — fall back to entries that don't
  // restrict sceneTypes at all (safe for any caller), never a mismatched one.
  const agnostic = all.filter((e) => !e.sceneTypes);
  return agnostic.length ? agnostic : all;
}

/** Pure pick — no anti-repeat awareness (used both directly and by
 *  `pickEffect` to recompute neighboring scenes' picks for exclusion). */
function pickEffectRaw(category: EffectCategory, ctx: EffectContext): EffectDef {
  const pool = poolFor(category, ctx);
  const seed = hash(`${category}:${ctx.sceneType}:${ctx.style}:${ctx.sceneIndex}`);
  // Style-match gets 3x weight so the pool leans toward on-brand choices
  // without ever fully excluding the rest (variety over rigidity).
  const weighted = pool.flatMap((e) => Array(e.styles?.includes(ctx.style) ? 3 : 1).fill(e));
  return weighted[seed % weighted.length];
}

/**
 * Choose the effect for one (category, scene). Deterministic and stateless:
 * to avoid repeating the same effect on back-to-back scenes, it recomputes
 * what the previous 1-2 scene indices would have picked (pure function
 * calls, not shared state — safe under render.js's per-scene isolated
 * renders and its concurrent scene worker pool) and excludes those ids from
 * this scene's pool before picking.
 */
export function pickEffect(category: EffectCategory, ctx: EffectContext): EffectDef {
  const exclude = new Set<string>();
  for (const back of [1, 2]) {
    const i = ctx.sceneIndex - back;
    if (i < 0) break;
    exclude.add(pickEffectRaw(category, {...ctx, sceneIndex: i}).id);
  }
  const pool = poolFor(category, ctx).filter((e) => !exclude.has(e.id));
  const candidates = pool.length ? pool : poolFor(category, ctx); // repetition beats an empty pool
  const seed = hash(`${category}:${ctx.sceneType}:${ctx.style}:${ctx.sceneIndex}:filtered`);
  const weighted = candidates.flatMap((e) => Array(e.styles?.includes(ctx.style) ? 3 : 1).fill(e));
  return weighted[seed % weighted.length];
}
