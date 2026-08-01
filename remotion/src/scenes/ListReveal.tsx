import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {SceneShell, type KenBurnsDir} from '../components/SceneShell';
import {OpacityCut, Label} from '../components/AeType';
import {AE_EASE, DURATION, dur, motionVocab} from '../components/tokens';
import {choreoBeats, type SceneBeats} from '../components/beats';
import {fontsFor} from '../components/effects/fonts';
import {getGlobalStyle, normalizeStyleId} from '../components/styleSystem';
import type {MediaSlot} from '../components/effects/mediaSlots';

const clamp = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};

interface ListRevealSceneProps {
  title: string;
  items: string[];
  bg_image?: string | null;
  bg_video?: string | null;
  accent_color?: string;
  text_color?: string;
  global_style?: string;
  scene_seed?: number;
  midground?: MediaSlot[];
  foreground?: MediaSlot[];
  overlay?: MediaSlot;
  /** Hybrid pipeline: render ONLY the text/animation layer, transparent bg. */
  transparent?: boolean;
  /** Director beat overrides — `title`,`first_item` (seconds). Items cascade from there. */
  beats?: SceneBeats;
  /** Director rhythm multiplier (scales item stagger). */
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
 * Sequential list — items rise one at a time on AE_EASE (not flat cuts).
 * Each item: number in style mono, text rises from a mask slot.
 */
export const ListRevealScene: React.FC<ListRevealSceneProps> = ({
  title,
  items,
  bg_image,
  bg_video,
  accent_color,
  text_color,
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
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const style = getGlobalStyle(normalizeStyleId(global_style));
  const vocab = motionVocab(global_style);
  const fonts = fontsFor(global_style);
  const accent = accent_color ?? style.visual.palette.accent;
  const textCol = text_color ?? style.visual.palette.text;

  const t = choreoBeats({title: 0, first_item: dur(DURATION.fast, vocab.tempo)}, beats, tempo, fps);
  const itemStagger = Math.max(4, Math.round(12 * (tempo ?? 1)));

  return (
    <SceneShell bg_image={bg_image} bg_video={bg_video} focus="left" ken_burns="right" photo_move={photo_move} energy={energy} drift={drift} grade_override={grade_override} accent_color={accent} global_style={global_style} scene_seed={scene_seed} midground={midground} foreground={foreground} overlay={overlay} transparent={transparent}>
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'flex-start', padding: '0 8%'}}>
        <div
          style={{
            backgroundColor: 'rgba(0,0,0,0.82)',
            borderLeft: `3px solid ${accent}`,
            padding: '28px 36px',
            maxWidth: '58%',
          }}
        >
          <OpacityCut startFrame={t.title} frames={3}>
            <div style={{marginBottom: 16}}>
              <Label text={title} accent={accent} startFrame={t.title} global_style={global_style} />
            </div>
          </OpacityCut>
          <div style={{display: 'flex', flexDirection: 'column', gap: 12}}>
            {items.map((item, i) => {
              const ti = t.first_item + i * itemStagger;
              const p = interpolate(frame, [ti, ti + 10], [0, 1], {...clamp, easing: AE_EASE});
              return (
                <div key={i} style={{display: 'flex', gap: 16, alignItems: 'baseline', overflow: 'hidden'}}>
                  <span style={{fontFamily: fonts.label, fontSize: 20, fontWeight: 600, color: accent, minWidth: 32, opacity: p}}>
                    {String(i + 1).padStart(2, '0')}
                  </span>
                  <div
                    style={{
                      fontFamily: fonts.body,
                      fontSize: 30,
                      fontWeight: 600,
                      color: textCol,
                      lineHeight: 1.3,
                      transform: `translateY(${(1 - p) * 100}%)`,
                      opacity: Math.min(1, p * 2),
                    }}
                  >
                    {item}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </AbsoluteFill>
    </SceneShell>
  );
};
