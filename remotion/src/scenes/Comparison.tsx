import React from 'react';
import {
  AbsoluteFill,
  Img,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {OpacityCut, TitleLine, typeStyle} from '../components/AeType';
import {clamp, linear} from '../components/editMotion';
import {gradeLookFor} from '../components/effects/grade';
import {GrainOverlay} from '../components/effects/Grain';
import {getGlobalStyle, normalizeStyleId} from '../components/styleSystem';
import {DURATION, dur, motionVocab} from '../components/tokens';
import {choreoBeats, type SceneBeats} from '../components/beats';

interface ComparisonSceneProps {
  left_text: string;
  right_text: string;
  left_image: string;
  right_image: string;
  accent_color?: string;
  text_color?: string;
  vs_label?: string;
  bg_image?: string | null;
  global_style?: string;
  scene_seed?: number;
  /** Director beat overrides — `left`,`right`,`vs` (seconds). */
  beats?: SceneBeats;
  /** Director rhythm multiplier. */
  tempo?: number;
}

/**
 * Editorial split-screen — no translateX slide (UI tell).
 * Both halves are static; labels opacity-cut in on beat, accent divider,
 * small center tag. Per-style grade + grain so the split matches the film.
 */
export const ComparisonScene: React.FC<ComparisonSceneProps> = ({
  left_text,
  right_text,
  left_image,
  right_image,
  accent_color,
  text_color,
  vs_label = 'VS',
  global_style = 'standard',
  scene_seed = 0,
  beats,
  tempo,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const style = getGlobalStyle(normalizeStyleId(global_style));
  const vocab = motionVocab(global_style);
  const look = gradeLookFor(global_style);
  const accent = accent_color ?? style.visual.palette.accent;
  const textCol = text_color ?? style.visual.palette.text;
  const grain = style.visual.grade.grain;

  const t = choreoBeats(
    {
      left: dur(DURATION.fast, vocab.tempo),
      right: dur(DURATION.fast, vocab.tempo) + 2,
      vs: dur(DURATION.base, vocab.tempo),
    },
    beats,
    tempo,
    fps,
  );
  const vsOp = interpolate(frame, [t.vs, t.vs + 3], [0, 1], {...clamp, easing: linear});

  const half: React.CSSProperties = {
    flex: 1,
    height: '100%',
    position: 'relative',
    overflow: 'hidden',
  };
  const img: React.CSSProperties = {
    width: '100%',
    height: '100%',
    objectFit: 'cover',
    filter: look.filter,
  };
  const labelBox: React.CSSProperties = {
    position: 'absolute',
    bottom: '10%',
    left: '8%',
    right: '8%',
    backgroundColor: 'rgba(0,0,0,0.82)',
    borderLeft: `3px solid ${accent}`,
    padding: '12px 18px',
  };

  return (
    <AbsoluteFill style={{backgroundColor: '#000', overflow: 'hidden'}}>
      <div style={{display: 'flex', width: '100%', height: '100%'}}>
        <div style={half}>
          <Img src={staticFile(left_image)} style={img} />
          <AbsoluteFill
            style={{
              background: 'linear-gradient(180deg, rgba(0,0,0,0.15) 0%, rgba(0,0,0,0.75) 100%)',
            }}
          />
          <OpacityCut startFrame={t.left} frames={3}>
            <div style={labelBox}>
              <TitleLine text={left_text} fontSize={32} fontWeight={700} color={textCol} align="left" uppercase />
            </div>
          </OpacityCut>
        </div>
        <div style={{width: 3, backgroundColor: accent, flexShrink: 0, zIndex: 2}} />
        <div style={half}>
          <Img src={staticFile(right_image)} style={img} />
          <AbsoluteFill
            style={{
              background: 'linear-gradient(180deg, rgba(0,0,0,0.15) 0%, rgba(0,0,0,0.75) 100%)',
            }}
          />
          <OpacityCut startFrame={t.right} frames={3}>
            <div style={labelBox}>
              <TitleLine text={right_text} fontSize={32} fontWeight={700} color={textCol} align="left" uppercase />
            </div>
          </OpacityCut>
        </div>
      </div>
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', pointerEvents: 'none'}}>
        <div
          style={{
            ...typeStyle,
            fontSize: 18,
            fontWeight: 700,
            color: '#fff',
            opacity: vsOp,
            backgroundColor: 'rgba(0,0,0,0.85)',
            border: `1px solid ${accent}`,
            padding: '6px 12px',
          }}
        >
          {vs_label}
        </div>
      </AbsoluteFill>
      <AbsoluteFill
        style={{
          background: 'radial-gradient(ellipse at center, transparent 50%, rgba(0,0,0,0.45) 100%)',
          pointerEvents: 'none',
        }}
      />
      <GrainOverlay opacity={grain * 2} seed={scene_seed} />
    </AbsoluteFill>
  );
};
