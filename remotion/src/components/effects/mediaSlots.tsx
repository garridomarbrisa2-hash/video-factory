/**
 * Media slot renderer — role-based multi-asset layering per scene.
 *
 * Roles (not pixel coordinates — the skills LLM picks roles, we own layout):
 *   background — base media, ken burns + camera life (existing SceneShell)
 *   midground  — cutout images drifting as parallax planes (PNG w/ alpha)
 *   foreground — framed polaroid cards with drop shadow + rotation
 *   overlay    — blend-mode texture/leak asset (screen/overlay)
 *
 * Depth convention: midground 0.4 / 0.7, foreground 1.0 → parallax dolly
 * against the background's own ken-burns move (docs/AE_TRENDS_CATALOG §13).
 */
import React from 'react';
import {Img, OffthreadVideo, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {cameraDrift} from './camera';

export interface MediaSlot {
  src: string;
  depth?: number; // 0..1 — midground drift scale
  rotate?: number; // foreground card tilt (deg)
  blend?: 'screen' | 'overlay' | 'soft-light'; // overlay role
  opacity?: number;
  x?: number; // % offset from center (foreground/midground)
  y?: number;
  scale?: number;
  startFrame?: number;
}

const clamp = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};

/** Cutout plane drifting at its own rate vs the background — 2.5D parallax. */
export const MidgroundSlot: React.FC<MediaSlot & {seed: string}> = ({src, depth = 0.5, x = 0, y = 0, scale = 1, opacity = 1, startFrame = 0, seed}) => {
  const frame = useCurrentFrame();
  const drift = cameraDrift(frame, `${seed}-mid`, 10 * depth, 0.08);
  const enter = interpolate(frame, [startFrame, startFrame + 10], [0, 1], clamp);

  return (
    <Img
      src={staticFile(src)}
      style={{
        position: 'absolute',
        left: `${50 + x}%`,
        top: `${50 + y}%`,
        transform: `translate(-50%, -50%) translate(${drift.x}px, ${drift.y}px) scale(${scale})`,
        opacity: opacity * enter,
        filter: 'drop-shadow(0 18px 42px rgba(0,0,0,0.55))',
      }}
    />
  );
};

/** Foreground polaroid card — white border, soft shadow, slight tilt, settle entrance. */
export const ForegroundCard: React.FC<MediaSlot & {seed: string}> = ({src, rotate = 2.5, x = 24, y = 0, scale = 0.42, startFrame = 0, seed}) => {
  const frame = useCurrentFrame();
  const drift = cameraDrift(frame, `${seed}-fg`, 3, 0.06);
  const enter = interpolate(frame, [startFrame, startFrame + 12], [0, 1], clamp);
  const settle = interpolate(frame, [startFrame, startFrame + 12], [1.06, 1], clamp);

  return (
    <div
      style={{
        position: 'absolute',
        left: `${50 + x}%`,
        top: `${50 + y}%`,
        transform: `translate(-50%, -50%) translate(${drift.x}px, ${drift.y}px) rotate(${rotate}deg) scale(${scale * settle})`,
        opacity: enter,
        backgroundColor: '#f4f1ea',
        padding: 14,
        paddingBottom: 44,
        boxShadow: '0 24px 60px rgba(0,0,0,0.6)',
      }}
    >
      <Img src={staticFile(src)} style={{display: 'block', width: 480, height: 540, objectFit: 'cover'}} />
    </div>
  );
};

/** Blend-mode texture/leak asset on top of everything (video or image). */
export const OverlaySlot: React.FC<MediaSlot> = ({src, blend = 'screen', opacity = 0.5, startFrame = 0}) => {
  const frame = useCurrentFrame();
  const enter = interpolate(frame, [startFrame, startFrame + 8], [0, 1], clamp);
  const isVideo = /\.(mp4|webm|mov)$/i.test(src);

  const style: React.CSSProperties = {
    position: 'absolute',
    inset: 0,
    width: '100%',
    height: '100%',
    objectFit: 'cover',
    mixBlendMode: blend,
    opacity: opacity * enter,
    pointerEvents: 'none',
  };

  return isVideo ? <OffthreadVideo src={staticFile(src)} muted style={style} /> : <Img src={staticFile(src)} style={style} />;
};
