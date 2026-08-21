/**
 * Ported foreground camera-move effects (Video Factory × HyperFrames
 * integration). These animate the CONTENT layer (children), independent of
 * SceneShell's background Ken Burns — a deliberate second camera plane for a
 * held detail/headline. See titles.tsx header for the porting note.
 */
import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import {HOUSE_EASE} from '../../tokens';

const clamp = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};

export interface CameraMoveProps {
  startFrame?: number;
  durationInFrames?: number;
  intensity?: 'standard' | 'strong';
  children: React.ReactNode;
}

/** hyperframes_source: push-in — one slow, continuous push toward the
 *  content, gently fading out at the very end of the window. */
export const PushInReveal: React.FC<CameraMoveProps> = ({
  startFrame = 0,
  durationInFrames = 90,
  intensity = 'standard',
  children,
}) => {
  const frame = useCurrentFrame();
  const local = frame - startFrame;
  const zoomTo = intensity === 'strong' ? 1.18 : 1.09;
  const p = interpolate(local, [0, durationInFrames], [0, 1], {...clamp, easing: HOUSE_EASE});
  const scale = 1 + (zoomTo - 1) * p;
  const exitOpacity = interpolate(local, [durationInFrames - 10, durationInFrames], [1, 0.85], clamp);

  return (
    <div style={{transform: `scale(${scale})`, opacity: exitOpacity, transformOrigin: 'center center'}}>
      {children}
    </div>
  );
};

/** hyperframes_source: pull-back-reveal — a tight detail holds, then one
 *  decelerating pull-back reveals the surrounding content. */
export const PullBackReveal: React.FC<CameraMoveProps> = ({
  startFrame = 0,
  durationInFrames = 60,
  intensity = 'standard',
  children,
}) => {
  const frame = useCurrentFrame();
  const local = frame - startFrame;
  const zoomFrom = intensity === 'strong' ? 1.45 : 1.22;
  const holdFrames = 10;
  const p = interpolate(local, [holdFrames, holdFrames + 34], [0, 1], {...clamp, easing: HOUSE_EASE});
  const scale = zoomFrom - (zoomFrom - 1) * p;

  return <div style={{transform: `scale(${scale})`, transformOrigin: 'center center'}}>{children}</div>;
};
