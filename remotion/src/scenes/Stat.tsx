import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {SceneShell, type KenBurnsDir} from '../components/SceneShell';
import {Rule, BodyText, Label} from '../components/AeType';
import {DrawOnUnderline} from '../components/effects/drawOn';
import {punchZoom} from '../components/effects/camera';
import {fontsFor} from '../components/effects/fonts';
import {getGlobalStyle, normalizeStyleId} from '../components/styleSystem';
import {AE_SETTLE, DURATION, dur, motionVocab, signatureCaps} from '../components/tokens';
import {choreoBeats, type SceneBeats} from '../components/beats';
import {ChartDrawOn} from '../components/effects/signature/ChartDrawOn';
import {numberOnsetFrame} from '../components/effects/sync';
import {countUp, cutIn} from '../components/choreo';
import {interpolate} from 'remotion';
import type {MediaSlot} from '../components/effects/mediaSlots';

const clamp = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};

interface StatSceneProps {
  /** The number/value, e.g. "11.3" or "$5B". If numeric_value set, counts up. */
  stat_text: string;
  /** Numeric target for count-up (omit for a static value). */
  numeric_value?: number;
  /** Decimal places for count-up. */
  decimals?: number;
  /** Prefix/suffix around the number ("$", "%", "B"). */
  prefix?: string;
  suffix?: string;
  /** Unit label above the number ("VISITOR DECLINE", "CASES"). */
  unit?: string;
  context_text?: string;
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
  /** Director beat overrides — `unit`,`number`,`punch`,`context` (seconds). */
  beats?: SceneBeats;
  /** Director rhythm multiplier. */
  tempo?: number;
  /** VO→visual sync (P1): per-word onset times (scene-relative seconds). */
  word_times?: Array<[string, number]>;
  /** Director opt-in: a trend line that draws itself before the number (P5, §20).
   *  Modern/standard only (style-capped). The stat lands as the takeaway. */
  chart_points?: number[];
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
 * Editorial stat — count-up + punch accent + draw-on underline:
 *   t=0          unit label cuts in (style mono face)
 *   t=instant    number counts up on AE_SETTLE (lands exactly, no overshoot)
 *   t=+70%       whole-frame punch accent + draw-on underline
 *   t=+beat      context line lands
 * modern gets the punch; crime/history/standard stay heavy and still.
 */
export const StatScene: React.FC<StatSceneProps> = ({
  stat_text,
  numeric_value,
  decimals = 0,
  prefix = '',
  suffix = '',
  unit,
  context_text,
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
  word_times,
  chart_points,
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
  const caps = signatureCaps(global_style);
  // Opt-in trend line (§20) — draws first, the stat lands as its takeaway.
  const showChart = chart_points && chart_points.length >= 2 && caps.chart > 0;

  const t = choreoBeats(
    {
      unit: 0,
      number: dur(DURATION.instant, vocab.tempo),
      punch: dur(DURATION.instant, vocab.tempo) + Math.round(dur(DURATION.slow, vocab.tempo) * 0.7),
      context: dur(DURATION.instant, vocab.tempo) + Math.round(dur(DURATION.slow, vocab.tempo) * 0.7) + dur(DURATION.fast, vocab.tempo),
    },
    beats,
    tempo,
    fps,
  );
  const tUnit = t.unit;
  const tNum = t.number;
  const countFrames = dur(DURATION.slow, vocab.tempo);
  // VO→visual sync (P1): the punch + accent land on the spoken number when word
  // timings are available — the single biggest "pro" tell. Director `beats.punch`
  // still wins; this only refines the style default.
  const spokenNumber = numberOnsetFrame(word_times, fps);
  const tAccent = beats?.punch != null ? t.punch : (spokenNumber ?? t.punch);
  const tCtx = t.context;

  const isCounting = numeric_value != null;
  // AE_SETTLE (expo-out) — lands exactly on target; springs only via countUp when style allows.
  const value = isCounting
    ? vocab.springAllowed
      ? countUp(frame, fps, tNum, countFrames, 0, numeric_value, true)
      : interpolate(frame, [tNum, tNum + countFrames], [0, numeric_value], {...clamp, easing: AE_SETTLE})
    : 0;
  const display = isCounting
    ? `${prefix}${value.toLocaleString('en-US', {minimumFractionDigits: decimals, maximumFractionDigits: decimals})}${suffix}`
    : stat_text;
  const numOp = isCounting ? Math.min(1, (frame - tNum) / 4) : cutIn(frame, tNum, dur(DURATION.instant, vocab.tempo));

  // Whole-frame punch on the accent beat (modern only — vocab.punch 1.05).
  const punch = punchZoom(frame, fps, tAccent, vocab.punch);

  return (
    <SceneShell bg_image={bg_image} bg_video={bg_video} focus="center" ken_burns="in" photo_move={photo_move} energy={energy} drift={drift} grade_override={grade_override} accent_color={accent} global_style={global_style} scene_seed={scene_seed} midground={midground} foreground={foreground} overlay={overlay} transparent={transparent}>
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', padding: '0 10%', transform: `scale(${punch})`}}>
        <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14}}>
          {showChart ? (
            <div style={{marginBottom: 4, opacity: cutIn(frame, tUnit, dur(DURATION.fast, vocab.tempo))}}>
              <ChartDrawOn points={chart_points!} color={accent} startFrame={tUnit} frames={countFrames} width={620} height={240} />
            </div>
          ) : null}
          {unit ? <Label text={unit} accent={accent} startFrame={tUnit} global_style={global_style} /> : null}
          <div
            style={{
              fontFamily: fonts.display,
              opacity: numOp,
              fontSize: 148,
              fontWeight: 900,
              color: textCol,
              textAlign: 'center',
              lineHeight: 1,
              fontVariantNumeric: 'tabular-nums',
              textShadow: '0 4px 18px rgba(0,0,0,0.5)',
            }}
          >
            {display}
          </div>
          {vocab.accentMode === 'highlight' || vocab.accentMode === 'underline' ? (
            <DrawOnUnderline width={120} color={accent} startFrame={tAccent} frames={dur(DURATION.fast, vocab.tempo)} strokeWidth={4} />
          ) : (
            <div style={{opacity: cutIn(frame, tAccent, dur(DURATION.instant, vocab.tempo))}}>
              <Rule color={accent} width={56} height={3} />
            </div>
          )}
          {context_text ? (
            <BodyText text={context_text} accent={accent} fontSize={27} align="center" startFrame={tCtx} global_style={global_style} />
          ) : null}
        </div>
      </AbsoluteFill>
    </SceneShell>
  );
};
