import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {SceneShell, type KenBurnsDir} from '../components/SceneShell';
import {LowerThirdPlate, OpacityCut, Label} from '../components/AeType';
import {MaskLineReveal} from '../components/effects/typography';
import {fontsFor} from '../components/effects/fonts';
import {getGlobalStyle, normalizeStyleId} from '../components/styleSystem';
import {DURATION, dur, motionVocab} from '../components/tokens';
import {choreoBeats, type SceneBeats} from '../components/beats';
import type {MediaSlot} from '../components/effects/mediaSlots';

interface PersonCardSceneProps {
  name: string;
  title?: string;
  bg_image?: string | null;
  bg_video?: string | null;
  accent_color?: string;
  text_color?: string;
  quote?: string;
  global_style?: string;
  scene_seed?: number;
  midground?: MediaSlot[];
  foreground?: MediaSlot[];
  overlay?: MediaSlot;
  /** Hybrid pipeline: render ONLY the text/animation layer, transparent bg. */
  transparent?: boolean;
  /** Director beat overrides — `plate`,`name`,`title`,`quote` (seconds). */
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
 * Person intro — name rises in the style display face; role + quote follow.
 * For crime/history this reads as a dossier card (mono label face).
 */
export const PersonCardScene: React.FC<PersonCardSceneProps> = ({
  name,
  title,
  bg_image,
  bg_video,
  accent_color,
  text_color,
  quote,
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
  const fonts = fontsFor(global_style);
  const accent = accent_color ?? style.visual.palette.accent;
  const textCol = text_color ?? style.visual.palette.text;

  const t = choreoBeats(
    {
      plate: dur(DURATION.instant, vocab.tempo),
      name: dur(DURATION.fast, vocab.tempo),
      title: dur(DURATION.base, vocab.tempo),
      quote: dur(DURATION.slow, vocab.tempo),
    },
    beats,
    tempo,
    fps,
  );

  return (
    <SceneShell bg_image={bg_image} bg_video={bg_video} focus="right" ken_burns="left" photo_move={photo_move} energy={energy} drift={drift} grade_override={grade_override} accent_color={accent} global_style={global_style} scene_seed={scene_seed} midground={midground} foreground={foreground} overlay={overlay} transparent={transparent}>
      <AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'flex-start', padding: '0 6% 10%'}}>
        <LowerThirdPlate startFrame={t.plate} accent_color={accent} maxWidth="52%" global_style={global_style}>
          <MaskLineReveal text={name} color={textCol} fontSize={38} align="left" startFrame={t.name} global_style={global_style} />
          {title ? (
            <OpacityCut startFrame={t.title} frames={3}>
              <div style={{fontFamily: fonts.label, fontSize: 18, fontWeight: 600, color: accent, marginTop: 8, letterSpacing: '0.08em', textTransform: 'uppercase'}}>
                {title}
              </div>
            </OpacityCut>
          ) : null}
          {quote ? (
            <OpacityCut startFrame={t.quote} frames={3}>
              <div style={{fontFamily: fonts.accent, fontSize: 20, fontWeight: 400, color: 'rgba(255,255,255,0.85)', marginTop: 12, fontStyle: 'italic', lineHeight: 1.35}}>
                {`“${quote}”`}
              </div>
            </OpacityCut>
          ) : null}
        </LowerThirdPlate>
      </AbsoluteFill>
    </SceneShell>
  );
};
