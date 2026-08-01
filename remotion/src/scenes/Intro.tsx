import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {SceneShell, type KenBurnsDir} from '../components/SceneShell';
import {Label, BodyText, Rule, OpacityCut} from '../components/AeType';
import {MaskLineReveal} from '../components/effects/typography';
import {getGlobalStyle, normalizeStyleId} from '../components/styleSystem';
import {DURATION, PHRASE_STAGGER, dur, motionVocab} from '../components/tokens';
import {choreoBeats, type SceneBeats} from '../components/beats';
import {resolvePlacement, type PlacementIntent} from '../components/layout';
import type {MediaSlot} from '../components/effects/mediaSlots';

interface IntroSceneProps {
  hook_text: string;
  /** Key phrase inside hook_text to accent. */
  emphasis?: string;
  /** Optional sub-hook line that lands on a later beat. */
  sub_hook?: string;
  bg_image?: string | null;
  bg_video?: string | null;
  accent_color?: string;
  text_color?: string;
  label?: string;
  /** Layout: 'lower-third' (editorial) or 'keyword' (centered hero). */
  layout?: 'lower-third' | 'keyword';
  /** Placement intent — overrides layout's default anchor. */
  placement?: PlacementIntent;
  global_style?: string;
  scene_seed?: number;
  /** Impact shake (0 = off). Director opts in per scene. */
  shake?: number;
  shake_at?: number;
  /** Role-based asset slots. */
  midground?: MediaSlot[];
  foreground?: MediaSlot[];
  overlay?: MediaSlot;
  /** Hybrid pipeline: render ONLY the text/animation layer, transparent bg. */
  transparent?: boolean;
  /** Director beat overrides — `label`,`title`,`sub_hook`,`rule` (seconds). */
  beats?: SceneBeats;
  /** Director rhythm multiplier. */
  tempo?: number;
  /** Director's explicit camera move (P3) — overrides the scene-type default. */
  photo_move?: KenBurnsDir;
  /** Director's pacing energy (P3) — derives the move when no explicit one set. */
  energy?: 'low' | 'mid' | 'high';
  /** Director's handheld-drift intent (Phase 8): 'off'|'low'|'style'|px number. Default off (still). */
  drift?: 'off' | 'low' | 'style' | number;
  /** Per-scene grade intent (P7): era/mood signpost mapped onto the style palette. */
  grade_override?: string;
}

/**
 * Editorial intro — staged beats:
 *   t=0            label cuts in (style mono face)
 *   t=instant      hook title enters (kinetic mask-line reveal per style)
 *   t=+stagger     sub_hook lands (optional)
 *   t=+2phase      accent rule draws
 * Kinetic entrances replace the old flat mask wipe — lines rise per style font.
 */
export const IntroScene: React.FC<IntroSceneProps> = ({
  hook_text,
  emphasis,
  sub_hook,
  bg_image,
  bg_video,
  accent_color,
  text_color,
  label,
  layout = 'lower-third',
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
  photo_move,
  energy,
  drift,
  grade_override,
}) => {
  const {fps} = useVideoConfig();
  const style = getGlobalStyle(normalizeStyleId(global_style));
  const vocab = motionVocab(global_style);
  const accent = accent_color ?? style.visual.palette.accent;
  const textCol = text_color ?? style.visual.palette.text;

  const tTitleDef = dur(DURATION.instant, vocab.tempo);
  const t = choreoBeats(
    {
      label: 0,
      title: tTitleDef,
      sub_hook: tTitleDef + dur(DURATION.slow, vocab.tempo) + PHRASE_STAGGER,
      rule: tTitleDef + dur(DURATION.slow, vocab.tempo),
    },
    beats,
    tempo,
    fps,
  );
  const tLabel = t.label;
  const tTitle = t.title;
  const tSub = t.sub_hook;

  const accentWords = emphasis ? [emphasis] : [];
  // Placement: layout keyword → hero, lower-third → editorial, explicit placement wins.
  const intent: PlacementIntent = placement ?? (layout === 'keyword' ? 'hero' : 'editorial');
  const place = resolvePlacement(intent);

  return (
    <SceneShell
      bg_image={bg_image}
      bg_video={bg_video}
      accent_color={accent}
      global_style={global_style}
      scene_seed={scene_seed}
      shake={shake}
      shake_at={shake_at}
      ken_burns="in"
      photo_move={photo_move}
      energy={energy}
      drift={drift}
      grade_override={grade_override}
      midground={midground}
      foreground={foreground}
      overlay={overlay} transparent={transparent}
    >
      <AbsoluteFill style={place.container as React.CSSProperties}>
        <div style={{display: 'flex', flexDirection: 'column', alignItems: intent === 'hero' ? 'center' : 'flex-start', gap: 18, maxWidth: place.maxWidth}}>
          {label ? (
            <div style={{display: 'flex', alignItems: 'center', gap: 12}}>
              <Rule color={accent} width={32} height={3} />
              <Label text={label} accent={accent} startFrame={tLabel} global_style={global_style} />
            </div>
          ) : null}
          <MaskLineReveal
            text={hook_text}
            color={textCol}
            accent={accent}
            accentWords={accentWords}
            fontSize={intent === 'hero' ? 84 : 72}
            align={place.textAlign}
            startFrame={tTitle}
            maxCharsPerLine={intent === 'hero' ? 20 : 24}
            global_style={global_style}
          />
          {sub_hook ? (
            <BodyText text={sub_hook} accent={accent} fontSize={26} align={place.textAlign} startFrame={tSub} global_style={global_style} />
          ) : (
            <OpacityCut startFrame={t.rule} frames={3}>
              <Rule color={accent} width={64} height={3} />
            </OpacityCut>
          )}
        </div>
      </AbsoluteFill>
    </SceneShell>
  );
};
