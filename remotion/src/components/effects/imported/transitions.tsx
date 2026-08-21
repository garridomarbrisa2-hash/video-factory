/**
 * Ported intra-scene transition/reveal effects (Video Factory × HyperFrames
 * integration). These wrap a scene's content layer for its entrance — they
 * are NOT cross-clip transitions (those stay FFmpeg xfade, see
 * concatWithXfade in remotion/src/render.js — out of scope here per the
 * "one renderer" constraint). See titles.tsx header for the porting note.
 */
import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import {LINEAR} from '../../tokens';

const clamp = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};

export interface WipeTransitionProps {
  startFrame?: number;
  frames?: number;
  direction?: 'left' | 'right' | 'up' | 'down';
  children: React.ReactNode;
}

const WIPE_CLIP: Record<string, (p: number) => string> = {
  left: (p) => `inset(0 ${100 - p}% 0 0)`,
  right: (p) => `inset(0 0 0 ${100 - p}%)`,
  up: (p) => `inset(${100 - p}% 0 0 0)`,
  down: (p) => `inset(0 0 ${100 - p}% 0)`,
};

/** hyperframes_source: directional-wipe — content reveals behind a hard
 *  directional edge (a panel push, not a soft fade). */
export const DirectionalWipe: React.FC<WipeTransitionProps> = ({
  startFrame = 0,
  frames = 14,
  direction = 'left',
  children,
}) => {
  const frame = useCurrentFrame();
  const p = interpolate(frame, [startFrame, startFrame + frames], [0, 100], {...clamp, easing: LINEAR});
  return <div style={{clipPath: WIPE_CLIP[direction](p), display: 'inline-block'}}>{children}</div>;
};

export interface ZoomThroughProps {
  startFrame?: number;
  frames?: number;
  children: React.ReactNode;
}

/** hyperframes_source: zoom-through-transition — the content zooms out from
 *  an oversized focal point and settles at 1x, reading as a push through the
 *  frame into the scene. */
export const ZoomThroughTransition: React.FC<ZoomThroughProps> = ({startFrame = 0, frames = 18, children}) => {
  const frame = useCurrentFrame();
  const p = interpolate(frame, [startFrame, startFrame + frames], [0, 1], clamp);
  const scale = interpolate(p, [0, 1], [2.4, 1], clamp);
  const opacity = interpolate(p, [0, 0.4, 1], [0, 0.6, 1], clamp);
  return (
    <div style={{transform: `scale(${scale})`, opacity, transformOrigin: 'center center'}}>{children}</div>
  );
};

export interface BeforeAfterWipeProps {
  before: React.ReactNode;
  after: React.ReactNode;
  beforeLabel?: string;
  afterLabel?: string;
  accent?: string;
  startFrame?: number;
  frames?: number;
  /** Rest position of the divider as a % from the left once the wipe settles. */
  restSplit?: number;
}

/** hyperframes_source: before-after-wipe — a persistent divider wipes the
 *  "after" panel over the "before" panel and rests at a configurable split. */
export const BeforeAfterWipe: React.FC<BeforeAfterWipeProps> = ({
  before,
  after,
  beforeLabel,
  afterLabel,
  accent = '#fff',
  startFrame = 0,
  frames = 20,
  restSplit = 50,
}) => {
  const frame = useCurrentFrame();
  const p = interpolate(frame, [startFrame, startFrame + frames], [0, restSplit], {...clamp, easing: LINEAR});

  return (
    <div style={{position: 'relative', width: '100%', height: '100%', overflow: 'hidden'}}>
      <div style={{position: 'absolute', inset: 0}}>{before}</div>
      <div style={{position: 'absolute', inset: 0, clipPath: `inset(0 0 0 ${p}%)`}}>{after}</div>
      <div style={{position: 'absolute', top: 0, bottom: 0, left: `${p}%`, width: 3, background: accent, transform: 'translateX(-50%)'}} />
      {beforeLabel ? (
        <div style={{position: 'absolute', top: 24, left: 24, color: '#fff', fontSize: 15, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase'}}>
          {beforeLabel}
        </div>
      ) : null}
      {afterLabel ? (
        <div style={{position: 'absolute', top: 24, right: 24, color: '#fff', fontSize: 15, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase'}}>
          {afterLabel}
        </div>
      ) : null}
    </div>
  );
};
