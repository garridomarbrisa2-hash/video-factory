/**
 * Layout engine — the single placement authority for every scene.
 *
 * Why: scenes used to hardcode positions (bottom-left plates, x:24 cards,
 * dead-center cutouts) → collisions, no focal hierarchy, everything bottom-left.
 *
 * Model (1920×1080):
 *  - Rule-of-thirds grid: vertical lines at x=640/1280, horizontal at y=360/720.
 *  - Text-safe zone: 5% margins (96px / 54px) — nothing important outside.
 *  - ONE focal anchor per scene — all elements align to support it.
 *
 * Scenes declare an INTENT; the engine resolves to CSS. Scenes never compute
 * raw pixel positions themselves.
 */

export const FRAME_W = 1920;
export const FRAME_H = 1080;
export const SAFE = {x: 96, y: 54}; // 5% title-safe margins

/** Horizontal third anchor. */
export type ThirdX = 'left' | 'center' | 'right';
/** Vertical third anchor. */
export type ThirdY = 'top' | 'middle' | 'bottom';

export interface Anchor {
  x: ThirdX;
  y: ThirdY;
}

/** Placement intents — the director picks one, the engine owns the geometry. */
export type PlacementIntent =
  | 'hero' // dead-center focal (stat, hook keyword)
  | 'editorial' // lower-left third (standard plate/title read)
  | 'sidebar' // right third, leaves left for b-roll subject
  | 'float'; // no text — pure visual (bare scenes)

export interface Placement {
  /** CSS for the text/content container. */
  container: React.CSSProperties;
  /** text-align matching the anchor. */
  textAlign: 'left' | 'center' | 'right';
  /** Max width for text blocks (prevents full-frame walls of text). */
  maxWidth: number;
  /** The free thirds where assets may live without colliding with text. */
  freeThirds: ThirdX[];
  /** Vertical center the assets orbit (% from frame center). Assets cluster
   *  around this so they never drop into the text band below. */
  assetY: number;
}

const THIRD_CENTER: Record<ThirdX, number> = {left: 320, center: 960, right: 1600};

/** Resolve a content placement from intent. */
export function resolvePlacement(intent: PlacementIntent): Placement {
  switch (intent) {
    case 'hero':
      return {
        container: {
          position: 'absolute',
          inset: 0,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          padding: `${SAFE.y}px ${SAFE.x}px`,
        },
        textAlign: 'center',
        maxWidth: 1200,
        freeThirds: ['left', 'right'], // center is the focal anchor
        assetY: 0, // center — flank the hero text
      };
    case 'sidebar':
      return {
        container: {
          position: 'absolute',
          top: 0,
          bottom: 0,
          right: SAFE.x,
          width: 620,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'flex-start',
        },
        textAlign: 'left',
        maxWidth: 560,
        freeThirds: ['left', 'center'], // left/center free for b-roll/assets
        assetY: -4, // slightly high — clears the vertically-centered text
      };
    case 'editorial':
      return {
        container: {
          position: 'absolute',
          left: SAFE.x,
          right: SAFE.x,
          bottom: 100,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'flex-start',
        },
        textAlign: 'left',
        maxWidth: 1100,
        freeThirds: ['right'], // right third free for assets
        assetY: -22, // upper-center — the text plate owns the bottom band
      };
    case 'float':
    default:
      return {
        container: {position: 'absolute', inset: 0, pointerEvents: 'none'},
        textAlign: 'left',
        maxWidth: 0,
        freeThirds: ['left', 'center', 'right'], // everything free — no text
        assetY: 0, // dead-center — no text to avoid
      };
  }
}

/**
 * Distribute N asset slots across the free thirds so they never sit under text.
 * Returns x/y (% offset from center, matching MediaSlot's convention) per slot.
 *
 * Two guarantees the old version missed (the "text over editing" bug):
 *  1. Vertical: assets orbit `placement.assetY`, NOT the stagger table alone —
 *     so an editorial (bottom-text) scene keeps cards in the upper frame, and a
 *     card at y=+14 can no longer drop its bottom edge into the text plate.
 *  2. Bounds: every slot is clamped so a 480×540 card at `baseScale` stays fully
 *     inside the title-safe frame (no half-cropped polaroids bleeding off-edge).
 */
export function distributeAssets(
  count: number,
  freeThirds: ThirdX[],
  baseScale: number,
  assetY = 0,
): {x: number; y: number; scale: number; rotate: number}[] {
  if (count <= 0 || freeThirds.length === 0) return [];
  const slots: {x: number; y: number; scale: number; rotate: number}[] = [];
  // Vertical stagger AROUND the placement's asset center (tight — the center
  // does the work of clearing the text band, the stagger only adds depth).
  const yStagger = [-7, 7, 0, -12, 12];

  // Foreground card half-extents at baseScale → keep the whole card on-frame.
  const CARD_HALF_W_PCT = ((480 / 2) * baseScale) / FRAME_W * 100;
  const CARD_HALF_H_PCT = ((540 / 2) * baseScale) / FRAME_H * 100;
  const safeX = 50 - CARD_HALF_W_PCT - (SAFE.x / FRAME_W) * 100;
  const safeY = 50 - CARD_HALF_H_PCT - (SAFE.y / FRAME_H) * 100;

  for (let i = 0; i < count; i++) {
    const third = freeThirds[i % freeThirds.length];
    // x as % offset from frame center (MediaSlot convention: 50 + x %).
    const thirdCenterPct = (THIRD_CENTER[third] / FRAME_W) * 100 - 50;
    // Within the third, fan slots out so multiple assets in one third don't overlap.
    const fan = freeThirds.length === 1 ? (i - (count - 1) / 2) * 12 : (i % 2 === 0 ? -4 : 4);
    const scale = baseScale * (1 - i * 0.06); // later assets slightly smaller (depth)
    const x = thirdCenterPct + fan;
    const y = assetY + yStagger[i % yStagger.length];
    slots.push({
      x: Math.round(Math.max(-safeX, Math.min(safeX, x))),
      y: Math.round(Math.max(-safeY, Math.min(safeY, y))),
      scale,
      rotate: (i % 2 === 0 ? -1 : 1) * (2 + (i % 3)),
    });
  }
  return slots;
}

/** px position of a third anchor (for focal-point math like map/document). */
export function anchorPx(anchor: Anchor): {x: number; y: number} {
  const xMap = {left: FRAME_W / 6, center: FRAME_W / 2, right: (FRAME_W * 5) / 6};
  const yMap = {top: FRAME_H / 6, middle: FRAME_H / 2, bottom: (FRAME_H * 5) / 6};
  return {x: xMap[anchor.x], y: yMap[anchor.y]};
}
