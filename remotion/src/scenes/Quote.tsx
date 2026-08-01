import React from 'react';
import {AbsoluteFill} from 'remotion';
import {SceneShell, type KenBurnsDir} from '../components/SceneShell';
import {BodyText, Rule, OpacityCut} from '../components/AeType';
import {MaskLineReveal} from '../components/effects/typography';
import {fontsFor} from '../components/effects/fonts';
import {getGlobalStyle, normalizeStyleId} from '../components/styleSystem';
import {DURATION, dur, motionVocab} from '../components/tokens';
import {choreoBeats, type SceneBeats} from '../components/beats';
import {cutIn} from '../components/choreo';
import {useCurrentFrame, useVideoConfig} from 'remotion';
import type {MediaSlot} from '../components/effects/mediaSlots';

interface QuoteSceneProps {
  quote_text: string;
  attribution?: string;
  /** Source/context line under the attribution. */
  source?: string;
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
  /** Director beat overrides — `mark`,`quote`,`attribution` (seconds). */
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
 * Editorial pull-quote — staged beats:
 *   t=0          oversized accent quote mark cuts in (style accent serif)
 *   t=instant    quote text rises line-by-line (kinetic mask reveal)
 *   t=+2phase    rule + attribution lands
 */
export const QuoteScene: React.FC<QuoteSceneProps> = ({
  quote_text,
  attribution,
  source,
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

  const t = choreoBeats(
    {
      mark: 0,
      quote: dur(DURATION.instant, vocab.tempo),
      attribution: dur(DURATION.instant, vocab.tempo) + dur(DURATION.slow, vocab.tempo) + 2,
    },
    beats,
    tempo,
    fps,
  );
  const tMark = t.mark;
  const tQuote = t.quote;
  const tAttr = t.attribution;

  return (
    <SceneShell bg_image={bg_image} bg_video={bg_video} focus="center" ken_burns="in" photo_move={photo_move} energy={energy} drift={drift} grade_override={grade_override} accent_color={accent} global_style={global_style} scene_seed={scene_seed} midground={midground} foreground={foreground} overlay={overlay} transparent={transparent}>
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'flex-start', padding: '0 14% 0 12%'}}>
        <div style={{display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 22, maxWidth: 1000}}>
          <div
            style={{
              opacity: cutIn(frame, tMark, dur(DURATION.instant, vocab.tempo)),
              fontFamily: fonts.accent,
              fontSize: 120,
              fontWeight: 700,
              color: accent,
              lineHeight: 0.6,
              textShadow: '0 2px 8px rgba(0,0,0,0.6)',
            }}
          >
            “
          </div>
          <MaskLineReveal
            text={quote_text}
            color={textCol}
            fontSize={40}
            fontWeight={500}
            fontFamily={fonts.accent}
            align="left"
            startFrame={tQuote}
            frames={dur(DURATION.slow, vocab.tempo)}
            global_style={global_style}
          />
          {attribution ? (
            <OpacityCut startFrame={tAttr} frames={3}>
              <div style={{display: 'flex', alignItems: 'center', gap: 14}}>
                <Rule color={accent} width={36} height={2} />
                <div style={{display: 'flex', flexDirection: 'column', gap: 3}}>
                  <span style={{fontFamily: fonts.body, fontSize: 21, fontWeight: 600, color: 'rgba(255,255,255,0.92)'}}>{attribution}</span>
                  {source ? (
                    <span style={{fontFamily: fonts.label, fontSize: 15, fontWeight: 400, color: 'rgba(255,255,255,0.6)', letterSpacing: '0.06em'}}>{source}</span>
                  ) : null}
                </div>
              </div>
            </OpacityCut>
          ) : null}
        </div>
      </AbsoluteFill>
    </SceneShell>
  );
};
