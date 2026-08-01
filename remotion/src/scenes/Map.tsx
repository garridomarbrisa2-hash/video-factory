import React from 'react';
import {AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {evolvePath, getLength, getPointAtLength} from '@remotion/paths';
import {SceneShell} from '../components/SceneShell';
import {Label, BodyText} from '../components/AeType';
import {getGlobalStyle, normalizeStyleId} from '../components/styleSystem';
import {AE_SETTLE, DURATION, dur, motionVocab} from '../components/tokens';
import {choreoBeats, type SceneBeats} from '../components/beats';
import {cutIn} from '../components/choreo';

const clamp = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};

interface MapSceneProps {
  /** Hi-res map image (≥2× output res so the zoom stays sharp). */
  map_image: string;
  /** Journey endpoints in % of the map image. */
  from_point: {x: number; y: number};
  to_point: {x: number; y: number};
  /** Focal point the camera dives toward (defaults to to_point). */
  focus_point?: {x: number; y: number};
  /** Labels for the endpoints ("Los Angeles" → "Area 51"). */
  from_label?: string;
  to_label?: string;
  /** Optional caption line. */
  caption?: string;
  bg_image?: string | null;
  accent_color?: string;
  text_color?: string;
  global_style?: string;
  scene_seed?: number;
  transparent?: boolean;
  /** Director beat overrides — `labels`,`route`,`dive` (seconds). */
  beats?: SceneBeats;
  /** Director rhythm multiplier. */
  tempo?: number;
  /** Per-scene grade intent (P7): era/mood signpost mapped onto the style palette. */
  grade_override?: string;
}

/**
 * Map zoom + route draw — the documentary journey beat (§16):
 *   t=0          wide map, endpoint labels cut in
 *   t=+beat      route draws itself from → to (stroke-dashoffset)
 *   t=+2beat     camera dives toward the destination
 * The style owns the grade/easing; the director owns the geography.
 */
export const MapScene: React.FC<MapSceneProps> = ({
  map_image,
  from_point,
  to_point,
  focus_point,
  from_label,
  to_label,
  caption,
  bg_image,
  accent_color,
  text_color,
  global_style = 'standard',
  scene_seed = 0,
  transparent = false,
  beats,
  tempo,
  grade_override,
}) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const style = getGlobalStyle(normalizeStyleId(global_style));
  const vocab = motionVocab(global_style);
  const accent = accent_color ?? style.visual.palette.accent;
  const textCol = text_color ?? style.visual.palette.text;

  const focus = focus_point ?? to_point;

  const routeFrames = dur(DURATION.slower, vocab.tempo);
  const t = choreoBeats(
    {
      labels: 0,
      route: dur(DURATION.fast, vocab.tempo),
      dive: dur(DURATION.fast, vocab.tempo) + Math.round(routeFrames * 0.6),
    },
    beats,
    tempo,
    fps,
  );
  const tLabels = t.labels;
  const tRoute = t.route;
  const tDive = t.dive;

  // Route draw-on progress + camera dive progress.
  const routeP = interpolate(frame, [tRoute, tRoute + routeFrames], [0, 1], {...clamp, easing: AE_SETTLE});
  const diveP = interpolate(frame, [tDive, durationInFrames], [0, 1], {...clamp, easing: AE_SETTLE});

  // Camera: dive toward the focal point (scale 1 → ~2.2, transform-origin at focus).
  const diveScale = 1 + diveP * 1.2;
  const diveX = diveP * (50 - focus.x) * 1.1;
  const diveY = diveP * (50 - focus.y) * 1.1;

  // Route path in a 100×100 viewBox matching the % coordinates.
  // Gentle arc: control point lifted perpendicular from the midpoint.
  const mx = (from_point.x + to_point.x) / 2;
  const my = (from_point.y + to_point.y) / 2;
  const dx = to_point.x - from_point.x;
  const dy = to_point.y - from_point.y;
  const lift = Math.min(18, Math.hypot(dx, dy) * 0.25);
  const cx = mx - dy * 0.3;
  const cy = my - Math.abs(dx) * 0.15 - lift * 0.4;
  const routeD = `M ${from_point.x} ${from_point.y} Q ${cx} ${cy}, ${to_point.x} ${to_point.y}`;

  const {strokeDasharray, strokeDashoffset} = evolvePath(routeP, routeD);
  const routeLen = getLength(routeD);
  const tip = getPointAtLength(routeD, routeLen * routeP);

  return (
    <SceneShell bg_image={bg_image ?? 'texture_dark.png'} accent_color={accent} global_style={global_style} scene_seed={scene_seed} transparent={transparent} ken_burns="none" darken={0.45} grade_override={grade_override}>
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', overflow: 'hidden'}}>
        {/* Map layer — dives toward focus */}
        <div
          style={{
            position: 'relative',
            width: '100%',
            height: '100%',
            transform: `scale(${diveScale}) translate(${diveX}%, ${diveY}%)`,
            transformOrigin: `${focus.x}% ${focus.y}%`,
          }}
        >
          <Img src={staticFile(map_image)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />

          {/* Route overlay — scales with the map */}
          <svg viewBox="0 0 100 100" preserveAspectRatio="none" style={{position: 'absolute', inset: 0, width: '100%', height: '100%', overflow: 'visible'}}>
            <path
              d={routeD}
              fill="none"
              stroke={accent}
              strokeWidth={0.6}
              strokeLinecap="round"
              strokeDasharray={strokeDasharray}
              strokeDashoffset={strokeDashoffset}
              vectorEffect="non-scaling-stroke"
            />
            {/* Pulsing tip marker */}
            <circle cx={tip.x} cy={tip.y} r={0.9} fill={accent} />
            {/* Endpoint dots */}
            <circle cx={from_point.x} cy={from_point.y} r={0.7} fill="#fff" opacity={0.9} />
            <circle cx={to_point.x} cy={to_point.y} r={0.9} fill={accent} />
          </svg>

          {/* Endpoint labels */}
          {from_label ? (
            <div style={{position: 'absolute', left: `${from_point.x}%`, top: `${from_point.y}%`, transform: 'translate(-50%, 140%)', opacity: cutIn(frame, tLabels, 4)}}>
              <span style={{fontSize: 15, fontWeight: 600, color: '#fff', letterSpacing: '0.08em', textTransform: 'uppercase', textShadow: '0 1px 4px rgba(0,0,0,0.9)', whiteSpace: 'nowrap'}}>
                {from_label}
              </span>
            </div>
          ) : null}
          {to_label ? (
            <div style={{position: 'absolute', left: `${to_point.x}%`, top: `${to_point.y}%`, transform: 'translate(-50%, 140%)', opacity: cutIn(frame, tRoute + 4, 4)}}>
              <span style={{fontSize: 15, fontWeight: 600, color: accent, letterSpacing: '0.08em', textTransform: 'uppercase', textShadow: '0 1px 4px rgba(0,0,0,0.9)', whiteSpace: 'nowrap'}}>
                {to_label}
              </span>
            </div>
          ) : null}
        </div>

        {/* Caption */}
        {caption ? (
          <AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'flex-start', padding: '0 8% 8%'}}>
            <BodyText text={caption} accent={accent} fontSize={24} align="left" startFrame={tDive} global_style={global_style} />
          </AbsoluteFill>
        ) : null}
      </AbsoluteFill>
    </SceneShell>
  );
};
