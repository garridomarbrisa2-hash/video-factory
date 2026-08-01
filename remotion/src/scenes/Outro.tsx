import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {SceneShell, type KenBurnsDir} from '../components/SceneShell';
import {BodyText, Rule, OpacityCut} from '../components/AeType';
import {MaskLineReveal, TrackingTitle} from '../components/effects/typography';
import {getGlobalStyle, normalizeStyleId} from '../components/styleSystem';
import {DURATION, dur, motionVocab} from '../components/tokens';
import {choreoBeats, type SceneBeats} from '../components/beats';
import type {MediaSlot} from '../components/effects/mediaSlots';

interface OutroSceneProps {
  cta_text: string;
  /** Key phrase in cta_text to accent. */
  emphasis?: string;
  bg_image?: string | null;
  bg_video?: string | null;
  accent_color?: string;
  text_color?: string;
  subtext?: string;
  global_style?: string;
  scene_seed?: number;
  midground?: MediaSlot[];
  foreground?: MediaSlot[];
  overlay?: MediaSlot;
  /** Hybrid pipeline: render ONLY the text/animation layer, transparent bg. */
  transparent?: boolean;
  /** Director beat overrides — `title`,`rule`,`subtext` (seconds). */
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
 * Editorial outro — bookends the intro:
 *   t=instant    CTA title enters (kinetic reveal)
 *   t=+stagger   accent rule draws
 *   t=+beat      subtext lands (tracking settle)
 */
export const OutroScene: React.FC<OutroSceneProps> = ({
  cta_text,
  emphasis,
  bg_image,
  bg_video,
  accent_color,
  text_color,
  subtext = 'Subscribe for more',
  global_style = 'standard',
  scene_seed = 0,
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
  const accentWords = emphasis ? [emphasis] : [];

  const tTitleDef = dur(DURATION.instant, vocab.tempo);
  const t = choreoBeats(
    {
      title: tTitleDef,
      rule: tTitleDef + dur(DURATION.slow, vocab.tempo),
      subtext: tTitleDef + dur(DURATION.slow, vocab.tempo) + dur(DURATION.fast, vocab.tempo),
    },
    beats,
    tempo,
    fps,
  );
  const tTitle = t.title;
  const tRule = t.rule;
  const tSub = t.subtext;

  return (
    <SceneShell bg_image={bg_image} bg_video={bg_video} focus="center" ken_burns="in" photo_move={photo_move} energy={energy} drift={drift} grade_override={grade_override} accent_color={accent} global_style={global_style} scene_seed={scene_seed} midground={midground} foreground={foreground} overlay={overlay} transparent={transparent}>
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'flex-start', padding: '0 10%'}}>
        <div style={{display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 20, maxWidth: 900}}>
          <MaskLineReveal
            text={cta_text}
            color={textCol}
            accent={accent}
            accentWords={accentWords}
            fontSize={62}
            align="left"
            startFrame={tTitle}
            global_style={global_style}
          />
          <OpacityCut startFrame={tRule} frames={3}>
            <Rule color={accent} width={56} height={3} />
          </OpacityCut>
          {subtext ? (
            <TrackingTitle text={subtext} color="rgba(255,255,255,0.75)" fontSize={22} align="left" startFrame={tSub} fromEm={0.22} toEm={0.08} global_style={global_style} />
          ) : null}
        </div>
      </AbsoluteFill>
    </SceneShell>
  );
};
