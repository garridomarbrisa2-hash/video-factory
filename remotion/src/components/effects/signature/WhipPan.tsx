/**
 * WhipPan — a directional-blur energy cut (§5). The modern genre's transition
 * between beats: the frame streaks sideways with motion blur and a new frame
 * snaps in. Used sparingly at energy bumps (never a default).
 *
 * Implemented as a self-contained move over `children`: a fast X translate with
 * a horizontal blur that peaks mid-whip. Blur ceiling from signatureCaps.whipPan.
 */
import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import {AE_SNAP} from '../../tokens';

const clamp = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};

export const WhipPan: React.FC<{
  /** Frame the whip starts. */
  at: number;
  /** Whip duration (frames). 6–10 reads as a snap. */
  frames?: number;
  /** Direction of travel. */
  dir?: 'left' | 'right';
  /** Peak blur px — capped by style signatureCaps.whipPan. */
  maxBlur?: number;
  children?: React.ReactNode;
}> = ({at, frames = 8, dir = 'left', maxBlur = 24, children}) => {
  const frame = useCurrentFrame();
  const local = frame - at;
  if (local < 0 || local > frames || maxBlur <= 0) return <>{children}</>;

  const p = interpolate(local, [0, frames], [0, 1], {...clamp, easing: AE_SNAP});
  // Travel: frame slides across and settles. Blur peaks in the middle of the move.
  const sign = dir === 'left' ? -1 : 1;
  const travel = sign * interpolate(p, [0, 1], [40, 0], clamp); // % from side → center
  const blur = Math.sin(Math.min(1, p) * Math.PI) * maxBlur;

  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        height: '100%',
        transform: `translateX(${travel}%)`,
        filter: blur > 0.3 ? `blur(${blur.toFixed(1)}px)` : undefined,
      }}
    >
      {children}
    </div>
  );
};
