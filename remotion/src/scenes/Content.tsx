import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {SceneShell} from '../components/SceneShell';
import {LowerThirdPlate, BodyText, Label} from '../components/AeType';
import {MaskLineReveal, WordPop} from '../components/effects/typography';
import type {FocusPoint, KenBurnsDir} from '../components/SceneShell';
import {getGlobalStyle, normalizeStyleId} from '../components/styleSystem';
import {DURATION, dur, motionVocab} from '../components/tokens';
import {choreoBeats, type SceneBeats} from '../components/beats';
import {resolvePlacement, distributeAssets, type PlacementIntent} from '../components/layout';
import type {MediaSlot} from '../components/effects/mediaSlots';

interface ContentSceneProps {
  /** Main line — omit entirely for a pure B-roll scene (no text). */
  text?: string;
  /** Key phrase inside text to accent. */
  emphasis?: string;
  /** Subordinate line that lands on a later beat. */
  subtext?: string | null;
  bg_image?: string | null;
  bg_video?: string | null;
  accent_color?: string;
  text_color?: string;
  focus?: FocusPoint;
  ken_burns?: KenBurnsDir;
  /** Director's explicit camera move (P3) — overrides the scene-type default. */
  photo_move?: KenBurnsDir;
  /** Director's pacing energy (P3) — derives the move when no explicit one set. */
  energy?: 'low' | 'mid' | 'high';
  /** Director's handheld-drift intent (Phase 8): 'off'|'low'|'style'|px number. Default off (still). */
  drift?: 'off' | 'low' | 'style' | number;
  label?: string;
  /**
   * Layout:
   *  'plate'   — lower-third plate with label + text + subtext (default)
   *  'keyword' — centered kinetic overlay, no plate
   *  'bare'    — pure B-roll, no text (text/subtext ignored)
   *  'collage' — layered assets (midground cutouts + foreground cards), text optional
   */
  layout?: 'plate' | 'keyword' | 'bare' | 'collage';
  /** Placement intent — where the text/content anchors. Overrides layout default. */
  placement?: PlacementIntent;
  global_style?: string;
  scene_seed?: number;
  /** Impact shake (0 = off). Director opts in per scene. */
  shake?: number;
  shake_at?: number;
  /** Role-based asset slots (cutouts / evidence cards / overlay texture). */
  midground?: MediaSlot[];
  foreground?: MediaSlot[];
  overlay?: MediaSlot;
  /** Hybrid pipeline: render ONLY the text/animation layer, transparent bg. */
  transparent?: boolean;
  /** Director beat overrides — `plate`,`text`,`accent`,`subtext` (seconds). */
  beats?: SceneBeats;
  /** Director rhythm multiplier. */
  tempo?: number;
  /** VO→visual sync (P1): per-word onset times (scene-relative seconds). */
  word_times?: Array<[string, number]>;
  /** Director opt-in signature move (P5): glitch_at / archival. */
  signature?: {glitch_at?: number; archival?: number};
  /** Per-scene grade intent (P7): era/mood signpost mapped onto the style palette. */
  grade_override?: string;
}

/**
 * Content scene — flexible layers driven by the script.
 * Beats (plate layout):
 *   t=instant       plate wipes in with label
 *   t=+stagger      main line lands (kinetic entrance)
 *   t=+2phase       accent underline/highlight draws
 *   t=+beat         subtext lands
 * A scene with layout='bare' renders only the graded, living B-roll —
 * the right choice when the VO carries a beat with no on-screen text.
 */
export const ContentScene: React.FC<ContentSceneProps> = ({
  text,
  emphasis,
  subtext,
  bg_image,
  bg_video,
  accent_color,
  text_color,
  focus = 'center',
  ken_burns = 'in',
  photo_move,
  energy,
  drift,
  label,
  layout = 'plate',
  placement,
  global_style = 'standard',
  scene_seed = 0,
  shake = 0,
  shake_at = 0,
  midground,
  foreground,
  overlay,
  transparent = false,
  beats,
  tempo,
  word_times,
  signature,
  grade_override,
}) => {
  const {fps} = useVideoConfig();
  const style = getGlobalStyle(normalizeStyleId(global_style));
  const vocab = motionVocab(global_style);
  const accent = accent_color ?? style.visual.palette.accent;
  const textCol = text_color ?? style.visual.palette.text;
  const accentWords = emphasis ? [emphasis] : [];

  // Beat defaults (token-computed, style-tempo-scaled); director's `beats`
  // (seconds) + `tempo` override any of them — components/beats.ts.
  const t = choreoBeats(
    {
      plate: dur(DURATION.instant, vocab.tempo),
      text: dur(DURATION.instant, vocab.tempo) + dur(DURATION.fast, vocab.tempo),
      accent: dur(DURATION.instant, vocab.tempo) + dur(DURATION.fast, vocab.tempo),
      subtext: dur(DURATION.instant, vocab.tempo) + dur(DURATION.fast, vocab.tempo) + dur(DURATION.base, vocab.tempo) + 2,
    },
    beats,
    tempo,
    fps,
  );
  const t0 = t.plate;
  const tText = t.text;
  const tSub = t.subtext;

  // Placement intent: explicit prop wins; otherwise derive from layout.
  const intent: PlacementIntent =
    placement ?? (layout === 'keyword' ? 'hero' : layout === 'bare' ? 'float' : layout === 'collage' ? 'sidebar' : 'editorial');
  const place = resolvePlacement(intent);

  // Compute asset positions so they never collide with the text band. The
  // placement's `assetY` keeps cards out of the lower-third text (editorial) and
  // `distributeAssets` clamps every card fully on-frame.
  const fgSlots = foreground && foreground.length > 0
    ? distributeAssets(foreground.length, place.freeThirds, 0.36, place.assetY).map((p, i) => ({...foreground[i], ...p}))
    : foreground;

  const shellProps = {bg_image, bg_video, focus, ken_burns, photo_move, energy, drift, accent_color: accent, global_style, scene_seed, shake, shake_at, word_times, emphasis, signature, grade_override, midground, foreground: fgSlots, overlay, transparent};

  // Pure B-roll — no text layers at all
  if (layout === 'bare' || !text) {
    return <SceneShell {...shellProps} />;
  }

  // Collage — assets carry the scene; text is a quiet caption over the board.
  if (layout === 'collage') {
    return (
      <SceneShell {...shellProps}>
        <AbsoluteFill style={place.container as React.CSSProperties}>
          <LowerThirdPlate startFrame={t0} accent_color={accent} maxWidth="92%" global_style={global_style}>
            {label ? (
              <div style={{marginBottom: 8}}>
                <Label text={label} accent={accent} startFrame={tText} global_style={global_style} />
              </div>
            ) : null}
            <MaskLineReveal
              text={text}
              color={textCol}
              accent={accent}
              accentWords={accentWords}
              fontSize={34}
              align={place.textAlign}
              startFrame={tText}
              global_style={global_style}
            />
            {subtext ? (
              <div style={{marginTop: 10}}>
                <BodyText text={subtext} accent={accent} fontSize={21} align={place.textAlign} startFrame={tSub} global_style={global_style} />
              </div>
            ) : null}
          </LowerThirdPlate>
        </AbsoluteFill>
      </SceneShell>
    );
  }

  if (layout === 'keyword') {
    return (
      <SceneShell {...shellProps}>
        <AbsoluteFill style={place.container as React.CSSProperties}>
          <div style={{maxWidth: place.maxWidth}}>
            <WordPop
              text={text}
              color={textCol}
              accent={accent}
              accentWords={accentWords}
              fontSize={56}
              align={place.textAlign}
              startFrame={tText}
              word_times={word_times}
              global_style={global_style}
            />
            {subtext ? (
              <div style={{marginTop: 20}}>
                <BodyText text={subtext} accent={accent} fontSize={24} align={place.textAlign} startFrame={tSub} global_style={global_style} />
              </div>
            ) : null}
          </div>
        </AbsoluteFill>
      </SceneShell>
    );
  }

  // Default: lower-third plate at the resolved placement.
  return (
    <SceneShell {...shellProps}>
      <AbsoluteFill style={place.container as React.CSSProperties}>
        <LowerThirdPlate startFrame={t0} accent_color={accent} maxWidth="100%" global_style={global_style}>
          {label ? (
            <div style={{marginBottom: 10}}>
              <Label text={label} accent={accent} startFrame={tText} global_style={global_style} />
            </div>
          ) : null}
          <MaskLineReveal
            text={text}
            color={textCol}
            accent={accent}
            accentWords={accentWords}
            fontSize={40}
            align={place.textAlign}
            startFrame={tText}
            global_style={global_style}
          />
          {subtext ? (
            <div style={{marginTop: 12}}>
              <BodyText text={subtext} accent={accent} fontSize={23} align={place.textAlign} startFrame={tSub} global_style={global_style} />
            </div>
          ) : null}
        </LowerThirdPlate>
      </AbsoluteFill>
    </SceneShell>
  );
};
