import React from 'react';
import {
  AbsoluteFill,
  Img,
  OffthreadVideo,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {getGlobalStyle, normalizeStyleId} from './styleSystem';
import {motionVocab, presenceVocab, type StillMotion} from './tokens';
import {kenBurns} from './choreo';
import {gradeLookFor, sculptGradeFor, resolveGrade, type GradeOverride} from './effects/grade';
import {GrainOverlay} from './effects/Grain';
import {cameraDrift, impactShake, overscanFor, easedCameraProgress, type ShakeDir} from './effects/camera';
import {CutLeak} from './effects/transitions';
import {ForegroundCard, MidgroundSlot, OverlaySlot, type MediaSlot} from './effects/mediaSlots';
import {DepthParallax, type DepthPlanes} from './effects/depthParallax';
import {LivingLight} from './effects/lightLife';
import {phraseOnsetFrame} from './effects/sync';
import {GlitchBeat} from './effects/signature/GlitchBeat';
import {ArchivalPulse} from './effects/signature/ArchivalPulse';
import {signatureCaps} from './tokens';

/** Director opt-in signature move for this scene (Phase 8, P5). Never a default. */
export interface SignatureIntent {
  /** RGB-split glitch at the twist (crime). Value = frame it fires on. */
  glitch_at?: number;
  /** Archival scratch/dust overlay (history). Value = intensity 0..1. */
  archival?: number;
}

export type FocusPoint =
  | 'center'
  | 'left'
  | 'right'
  | 'top'
  | 'bottom'
  | 'top-left'
  | 'top-right'
  | 'bottom-left'
  | 'bottom-right';

export type KenBurnsDir =
  | 'in'
  | 'out'
  | 'left'
  | 'right'
  | 'up'
  | 'down'
  | 'in-left'
  | 'in-right'
  | 'none';

export interface SceneShellProps {
  /** Still image in public/ (staticFile). Required if bg_video not set. */
  bg_image?: string | null;
  /** Video clip in public/ (staticFile). Preferred over bg_image when set. */
  bg_video?: string | null;
  /** Baked depth planes (far/mid/near) — enables true parallax. OPT-IN: pass
   *  explicitly to enable; absent = clean single-image (Phase 6 editorial look). */
  depth?: DepthPlanes | null;
  /** Use sculpted grade + focal depth (Phase 7). OPT-IN — default OFF so the
   *  clean Phase 6 grade (gradeLookFor) is the editorial baseline. */
  sculpt?: boolean;
  /**
   * Transparent-overlay mode (hybrid pipeline, Phase 7b). Renders ONLY the
   * animation/children layer (text, accents, counters) with NO background, so
   * FFmpeg composites it over the GPU-built photo base. The whole point of the
   * hybrid: Remotion keeps precise text animation; the photo moves in FFmpeg.
   */
  transparent?: boolean;
  focus?: FocusPoint;
  ken_burns?: KenBurnsDir;
  /** Director's explicit camera move for this beat (Phase 8, P3). Highest
   *  precedence — overrides the scene-type default and the energy derivation.
   *  Motivated by the beat: push-in for intimacy/turn, out for resolve/context,
   *  pan to follow action. */
  photo_move?: KenBurnsDir;
  /** Director's motion choice for a STILL background (bg_image). One smooth,
   *  deliberate move — never jittery drift/shake. See StillMotion in tokens.
   *  'push' (default) = eased Ken Burns in; 'pan' = eased slide; 'parallax' =
   *  near-plane differential; 'light' = living-light over a held frame;
   *  'hold' = locked (only for a document/map artifact). */
  still_motion?: StillMotion;
  /** Director's pacing energy for this scene (Phase 8, P3). When no explicit
   *  ken_burns/photo_move is set, the move is DERIVED from energy instead of the
   *  template seed-rotation: low=hold still, mid=gentle push-in, high=push-in
   *  (accent carries the energy). Seed rotation is the last-resort fallback. */
  energy?: 'low' | 'mid' | 'high';
  /** Override style ken_burns_zoom; defaults from global_style */
  zoom?: number;
  /** Director's handheld-drift intent (Phase 8). DEFAULT OFF — a still frame locks.
   *  The style's `drift` value becomes the CEILING, not the default:
   *    'off'   → no drift (locked frame; the default when omitted)
   *    'low'   → half the style's drift (a breath of life)
   *    'style' → the style's full archival float (opt-in where motivated)
   *  A number = explicit px amplitude (still capped by the style ceiling). */
  drift?: 'off' | 'low' | 'style' | number;
  /** Override style grade.darken; defaults from global_style */
  darken?: number;
  accent_color?: string;
  /** Global style id or legacy alias — drives grade + motion defaults */
  global_style?: string;
  /** Scene index — seeds camera noise so each scene drifts differently. */
  scene_seed?: number;
  /**
   * Impact shake — a decaying camera hit. OFF by default; the director opts
   * in per scene only for a genuine impact beat (explosion, reveal, drop).
   * NOT a style default — shake on every scene is a bug, not a look.
   */
  shake?: number;
  /** Frame the shake starts on (default 0 — the scene's opening beat). */
  shake_at?: number;
  /** Dominant direction of the impact kick (Phase 8, P4). 'x' = horizontal hit,
   *  'y' = vertical, 'diag' = both. Director intent; default 'x'. */
  shake_dir?: ShakeDir;
  /** VO→visual sync (P1): per-word onset times (scene-relative seconds). */
  word_times?: Array<[string, number]>;
  /** Key phrase — shake defaults to its spoken onset when word_times present. */
  emphasis?: string;
  /** Director opt-in signature move (Phase 8, P5). Style-capped, never a default. */
  signature?: SignatureIntent;
  /** Per-scene grade intent (Phase 8, P7): signpost era/mood for THIS scene only,
   *  mapped onto the style palette. archival=old footage, clean=present-day,
   *  noir=hard crime, sepia=warm history, halftone=print/document. */
  grade_override?: GradeOverride | string;
  /** Role-based asset slots (midground cutouts / foreground cards / overlay). */
  midground?: MediaSlot[];
  foreground?: MediaSlot[];
  overlay?: MediaSlot;
  children?: React.ReactNode;
}

const FOCUS: Record<FocusPoint, string> = {
  center: '50% 50%',
  left: '20% 50%',
  right: '80% 50%',
  top: '50% 25%',
  bottom: '50% 75%',
  'top-left': '25% 25%',
  'top-right': '75% 25%',
  'bottom-left': '25% 75%',
  'bottom-right': '75% 75%',
};

/**
 * Resolve the camera move for a scene (Phase 8, P3 — camera intent grammar).
 * Precedence (first defined wins):
 *   1. photo_move  — the director's explicit, beat-motivated move (strongest)
 *   2. energy      — the director's pacing intent, derived:
 *                    low=hold still, mid=gentle push-in, high=push-in
 *   3. ken_burns   — the scene-type structural default (e.g. PersonCard pans
 *                    toward the card; boards hold still)
 *   4. seed rotation — the template fallback (only when nothing above is set)
 *
 * Director intent (1–2) always beats the scene-type default and the dice roll.
 * Energy derivation keeps low beats still (a quiet quote doesn't drift) and
 * reserves movement for beats that earn it.
 */
function resolveCameraMove(
  photoMove: KenBurnsDir | undefined,
  energy: 'low' | 'mid' | 'high' | undefined,
  kenBurns: KenBurnsDir | undefined,
  seed: number,
): KenBurnsDir {
  if (photoMove) return photoMove;
  if (energy === 'low') return 'none';
  if (energy === 'mid' || energy === 'high') return 'in';
  if (kenBurns) return kenBurns;
  // Last resort: template rotation (deterministic per scene index).
  const KB_ROTATION: KenBurnsDir[] = ['in', 'right', 'out', 'left', 'up', 'down'];
  return KB_ROTATION[seed % KB_ROTATION.length];
}

/**
 * Handheld drift is OPT-IN (Phase 8). A still frame is a directed frame — the
 * archival float must be motivated, not taxed on every image. Default 'off';
 * the style's `drift` value is only the ceiling.
 */
function resolveDrift(
  intent: 'off' | 'low' | 'style' | number | undefined,
  styleDrift: number,
): number {
  if (intent == null || intent === 'off') return 0;
  if (intent === 'low') return styleDrift * 0.5;
  if (intent === 'style') return styleDrift;
  return Math.min(intent, styleDrift); // explicit px, capped
}

function kenBurnsTransform(
  dir: KenBurnsDir,
  progress: number,
  zoom: number,
): {scale: number; x: number; y: number} {
  const z = 1 + (zoom - 1) * progress;
  const zOut = zoom - (zoom - 1) * progress;
  const pan = 4 * progress;

  switch (dir) {
    case 'in':
      return {scale: z, x: 0, y: 0};
    case 'out':
      return {scale: zOut, x: 0, y: 0};
    case 'left':
      return {scale: zoom, x: -pan, y: 0};
    case 'right':
      return {scale: zoom, x: pan, y: 0};
    case 'up':
      return {scale: zoom, x: 0, y: -pan};
    case 'down':
      return {scale: zoom, x: 0, y: pan};
    case 'in-left':
      return {scale: z, x: -pan * 0.6, y: 0};
    case 'in-right':
      return {scale: z, x: pan * 0.6, y: 0};
    case 'none':
    default:
      return {scale: 1, x: 0, y: 0};
  }
}

/**
 * Scene shell — the layered base every scene sits on:
 *   L0 overlay/leak at cuts (blend-mode, masks the xfade)
 *   L1 background media (image/video) — ken burns + per-style grade + camera life
 *   L2 midground slots (parallax cutouts)
 *   L3 grade wash + darken gradient + vignette + animated grain
 *   L4 foreground slots (polaroid cards)
 *   L5 children (text/graphics — opt-in per scene)
 *
 * Per-style identity (crime grain+shake, history drift, modern punch, etc.)
 * comes from motionVocab + gradeLookFor — scenes never set easings directly.
 */
export const SceneShell: React.FC<SceneShellProps> = ({
  bg_image,
  bg_video,
  depth = null,
  sculpt = false,
  focus = 'center',
  ken_burns,
  photo_move,
  still_motion,
  energy,
  zoom,
  drift,
  darken,
  accent_color,
  global_style = 'standard',
  scene_seed = 0,
  shake = 0,
  shake_at,
  shake_dir = 'x',
  word_times,
  emphasis,
  signature,
  grade_override,
  midground = [],
  foreground = [],
  overlay,
  transparent = false,
  children,
}) => {
  const frame = useCurrentFrame();
  const {durationInFrames, fps} = useVideoConfig();
  const style = getGlobalStyle(normalizeStyleId(global_style));
  const vocab = motionVocab(global_style);
  const presence = presenceVocab(global_style);
  const grade = style.visual.grade;
  const palette = style.visual.palette;
  const look = gradeLookFor(global_style);
  const sculptLook = sculptGradeFor(global_style);
  const caps = signatureCaps(global_style);
  // Per-scene grade intent (P7): the director's era/mood override, mapped onto
  // the style palette. Resolves to the base look when no override is set.
  const resolvedGrade = resolveGrade(global_style, grade_override);

  const effDarken = darken ?? grade.darken;
  const accent = accent_color ?? palette.accent;

  // Depth parallax is OPT-IN (Phase 7). Only when the director/pipeline passes
  // explicit `depth` planes do we render the 2.5D multi-plane look. Default:
  // clean single-image + eased camera (the Phase 6 editorial baseline).
  const useParallax = !bg_video && depth != null;

  // --- L1: background media — eased camera + camera life ---
  // Camera intent grammar (P3): the director's photo_move/energy wins; the
  // template seed-rotation only fires when no intent was expressed at all.
  const kenBurnsDir = resolveCameraMove(photo_move, energy, ken_burns, scene_seed);

  // Eased progress for the single-image fallback (no more constant-velocity slide).
  const progress = easedCameraProgress(frame, durationInFrames, 0.42, 0.1);
  // --- Still-motion resolution (Issue: no frozen stills, no jittery drift) ---
  // A bg_image still must MOVE, smoothly and deliberately. still_motion is the
  // director's choice; absent it, a still defaults to a visible eased 'push'
  // (never the jittery cameraDrift the user rejected). Video keeps its own
  // subtle zoom. 'hold' is honored only as an explicit, justified choice.
  const isStill = !bg_video;
  const resolvedStillMotion: StillMotion | null = isStill ? still_motion ?? 'push' : null;

  // Map still-motion to a ken-burns direction. 'pan' picks a deterministic
  // lateral direction from the seed; 'parallax'/'light'/'hold' hold the bg
  // (their motion comes from the layer above, not the bg transform).
  let stillDir: KenBurnsDir = kenBurnsDir;
  if (isStill) {
    if (resolvedStillMotion === 'push') stillDir = photo_move ?? 'in';
    else if (resolvedStillMotion === 'pan') {
      const PAN_ROTATION: KenBurnsDir[] = ['right', 'left', 'up', 'down'];
      stillDir = photo_move && photo_move !== 'in' ? photo_move : PAN_ROTATION[scene_seed % PAN_ROTATION.length];
    } else {
      stillDir = 'none'; // parallax / light / hold — background holds still
    }
  }

  const effZoom = zoom ?? vocab.ken;
  // Stills pushing/panning use the visible stillKen so the move actually reads;
  // everything else (video, held bg) stays at the subtle ken.
  const movingBg = isStill && (resolvedStillMotion === 'push' || resolvedStillMotion === 'pan');
  const baseZoom = movingBg ? vocab.stillKen : effZoom;
  const effectiveZoom = bg_video ? Math.min(effZoom, 1.06) : baseZoom;
  const {scale, x, y} = kenBurnsTransform(stillDir, progress, effectiveZoom);

  const seed = `scene-${scene_seed}`;
  // Drift is opt-in: off unless the director asks for the archival float.
  const driftAmp = resolveDrift(drift, vocab.drift);
  const driftOffset = cameraDrift(frame, seed, driftAmp);
  // Impact shake — ONLY when the director opts in (shake > 0), capped by style ceiling.
  const effShake = Math.min(shake, vocab.max_shake);
  // VO→visual sync (P1): shake defaults to the emphasis word's spoken onset.
  // Director's explicit shake_at always wins.
  const shakeAtResolved =
    shake_at ?? phraseOnsetFrame(word_times, emphasis, fps) ?? 0;
  // P4: directional impact kick (not jelly). 10-frame decay — a hard hit that settles.
  const kick = impactShake(frame, seed, effShake, shakeAtResolved, Math.min(10, durationInFrames), shake_dir);
  const camX = driftOffset.x + kick.x;
  const camY = driftOffset.y + kick.y;
  const camR = driftOffset.r + kick.r;
  const overscan = overscanFor(driftAmp + effShake * 5);

  if (!bg_image && !bg_video && !transparent) {
    throw new Error('SceneShell requires bg_image or bg_video — no empty backgrounds');
  }

  // Transparent-overlay mode (hybrid pipeline): render ONLY the animation layer
  // (children). Triggered explicitly via `transparent`, OR implicitly when there
  // is no background media (render.js omits bg_image for the overlay pass, so
  // every scene composites over the FFmpeg photo base with zero scene changes).
  const isTransparent = transparent || (!bg_image && !bg_video);
  if (isTransparent) {
    return (
      <AbsoluteFill style={{backgroundColor: 'transparent', overflow: 'hidden'}}>{children}</AbsoluteFill>
    );
  }

  // Sculpted grade (Phase 7) for stills; legacy flat look stays for video.
  // A per-scene grade_override (P7) wins over both — it's the director's call.
  const mediaFilter = grade_override
    ? resolvedGrade.filter
    : bg_video || !sculpt
    ? look.filter
    : sculptLook.filter;

  const mediaStyle: React.CSSProperties = {
    width: '100%',
    height: '100%',
    objectFit: 'cover',
    objectPosition: FOCUS[focus],
    transform: `scale(${scale * overscan}) translate(calc(${x}% + ${camX + kick.smear}px), calc(${y}% + ${camY}px)) rotate(${camR}deg)`,
    filter: mediaFilter,
  };

  const vignetteOpacity =
    grade.vignette === 'strong' ? 0.7
    : grade.vignette === 'medium' ? 0.55
    : grade.vignette === 'subtle' ? 0.35
    : 0; // 'none'

  // Focal separation — soft edge blur so the subject plane pops (stills only).
  const focal = sculpt && !bg_video ? sculptLook.focal : null;

  return (
    <AbsoluteFill style={{backgroundColor: '#0a0a0a', overflow: 'hidden'}}>
      {/* L1: background — parallax planes for stills, single media otherwise */}
      <AbsoluteFill style={{overflow: 'hidden'}}>
        {bg_video ? (
          <OffthreadVideo src={staticFile(bg_video)} muted style={mediaStyle} />
        ) : useParallax ? (
          <DepthParallax
            planes={depth!}
            amounts={{
              zoom: presence.pZoom,
              pan: presence.pPan,
              separation: presence.pSeparation,
              rotate: presence.pRotate,
            }}
            seed={scene_seed}
            filter={mediaFilter}
          />
        ) : (
          <Img src={staticFile(bg_image!)} style={mediaStyle} />
        )}
      </AbsoluteFill>

      {/* L2: midground parallax cutouts (sit under the grade so they grade with the bg) */}
      {midground.map((slot, i) => (
        <MidgroundSlot key={i} {...slot} seed={`${seed}-m${i}`} />
      ))}

      {/* L3: sculpted grade — split-tone + focal depth + darken + vignette + grain */}
      {sculpt && !bg_video ? (
        <>
          {/* Shadow split-tone (lift blacks toward style tint) */}
          <AbsoluteFill
            style={{
              background: `linear-gradient(0deg, ${sculptLook.shadowTint.color} 0%, transparent 55%)`,
              mixBlendMode: 'screen',
              opacity: sculptLook.shadowTint.strength,
            }}
          />
          {/* Highlight split-tone (warm/cool the lights) */}
          <AbsoluteFill
            style={{
              background: `linear-gradient(180deg, ${sculptLook.highlightTint.color} 0%, transparent 50%)`,
              mixBlendMode: 'soft-light',
              opacity: sculptLook.highlightTint.strength,
            }}
          />
        </>
      ) : (grade_override ? resolvedGrade.wash : look.wash) ? (
        <AbsoluteFill style={{background: (grade_override ? resolvedGrade.wash! : look.wash!).background, mixBlendMode: (grade_override ? resolvedGrade.wash! : look.wash!).blend as any, opacity: (grade_override ? resolvedGrade.wash! : look.wash!).opacity}} />
      ) : null}
      {/* Focal separation — cheap radial edge-dim (NO backdrop-filter blur, which
          is the single most expensive thing Chrome composites). Reads as DOF. */}
      {focal && focal.edgeDesat > 0 ? (
        <AbsoluteFill
          style={{
            background: `radial-gradient(ellipse at center, transparent ${focal.centerKeep * 100}%, rgba(0,0,0,${0.22 + focal.edgeDesat}) 100%)`,
          }}
        />
      ) : null}
      <AbsoluteFill
        style={{
          background: `linear-gradient(180deg, rgba(0,0,0,${effDarken * 0.7}) 0%, rgba(0,0,0,${effDarken * 0.35}) 40%, rgba(0,0,0,${effDarken}) 100%)`,
        }}
      />
      {vignetteOpacity > 0 ? (
        <AbsoluteFill
          style={{
            background: `radial-gradient(ellipse at center, transparent 40%, rgba(0,0,0,${vignetteOpacity}) 100%)`,
          }}
        />
      ) : null}

      {/* L3b: living light — volumetric sweep + dust + beat flare (stills only).
          Fires when the director opts into the sculpted grade (sculpt) OR picks
          the 'light' still-motion — either way it's the smooth, non-jittery
          motion source for a held frame. */}
      {!bg_video && (sculpt || resolvedStillMotion === 'light') ? (
        <LivingLight
          sweep={presence.lightSweep}
          dust={presence.lightDust}
          flare={presence.lightFlare}
          warm={presence.lightWarm}
          seed={scene_seed}
          beatAt={shakeAtResolved}
        />
      ) : null}

      <GrainOverlay opacity={vocab.grain * resolvedGrade.grain} seed={scene_seed} />

      {/* L4: foreground cards (polaroid evidence) */}
      {foreground.map((slot, i) => (
        <ForegroundCard key={i} {...slot} seed={`${seed}-f${i}`} />
      ))}

      {/* L5: blend-mode overlay asset (dust/leak texture) */}
      {overlay ? <OverlaySlot {...overlay} /> : null}

      {/* L0/L6: cut-masking light leaks (head + tail), under the xfade */}
      {vocab.cutLeak ? (
        <>
          <CutLeak when="head" seed={scene_seed * 3 + 1} hueShift={global_style === 'crime' ? 340 : 0} />
          <CutLeak when="tail" seed={scene_seed * 3 + 2} hueShift={global_style === 'crime' ? 340 : 0} />
        </>
      ) : null}

      {/* P5/P7 archival pulse: fired by signature.archival OR grade_override='archival'
          (the director's era signpost). Style-capped either way. */}
      {signature?.archival || resolvedGrade.archival > 0 ? (
        <ArchivalPulse
          intensity={Math.min(
            Math.max(signature?.archival ?? 0, resolvedGrade.archival),
            caps.archival,
          )}
          seed={scene_seed}
        />
      ) : null}

      {/* Content layer — wrapped in the opt-in glitch beat when the director calls it */}
      {signature?.glitch_at != null && caps.glitch > 0 ? (
        <GlitchBeat at={signature.glitch_at} intensity={caps.glitch} seed={scene_seed}>
          {children}
        </GlitchBeat>
      ) : (
        children
      )}
    </AbsoluteFill>
  );
};
