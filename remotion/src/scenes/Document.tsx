import React from 'react';
import {AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {SceneShell} from '../components/SceneShell';
import {Label} from '../components/AeType';
import {fontsFor} from '../components/effects/fonts';
import {getGlobalStyle, normalizeStyleId} from '../components/styleSystem';
import {AE_EASE, AE_SETTLE, DURATION, dur, motionVocab} from '../components/tokens';
import {choreoBeats, type SceneBeats} from '../components/beats';
import {cutIn} from '../components/choreo';
import {HalftoneDoc} from '../components/effects/signature/HalftoneDoc';
import {signatureCaps} from '../components/tokens';

const clamp = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};

interface HighlightBox {
  /** All in % of the document image. */
  x: number;
  y: number;
  w: number;
  h: number;
}

interface DocumentSceneProps {
  /** The document image (newspaper, letter, court filing). */
  document_image: string;
  /** The line/region to highlight, in % of the image. */
  highlight_box: HighlightBox;
  /** Focal point to punch into (defaults to highlight center). */
  punch_to?: {x: number; y: number};
  /** Optional kicker label ("EXHIBIT A", "COURT FILING"). */
  label?: string;
  /** Caption that lands under the document after the punch. */
  caption?: string;
  bg_image?: string | null;
  accent_color?: string;
  text_color?: string;
  global_style?: string;
  scene_seed?: number;
  transparent?: boolean;
  /** Director beat overrides — `doc`,`highlight`,`punch`,`caption` (seconds). */
  beats?: SceneBeats;
  /** Director rhythm multiplier. */
  tempo?: number;
  /** Per-scene grade intent (P7/P5). 'halftone' renders the doc as print (§12). */
  grade_override?: string;
}

/**
 * Document reveal — single focal hierarchy (the highlighted line IS the anchor).
 *
 *   t=0          document settles into frame, anchored center-right
 *   t=+beat      marker highlight sweeps the key line
 *   t=+2beat     camera punches INTO the highlight center → brings it to frame center
 *   t=+3beat     caption lands directly under the document, centered on the same axis
 *
 * The old version had the doc mid-frame + a detached bottom-left caption (two
 * competing anchors). Here everything aligns to one vertical axis through the
 * punch destination — the eye follows a single path.
 */
export const DocumentScene: React.FC<DocumentSceneProps> = ({
  document_image,
  highlight_box,
  punch_to,
  label,
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
  const {fps} = useVideoConfig();
  const style = getGlobalStyle(normalizeStyleId(global_style));
  const vocab = motionVocab(global_style);
  const fonts = fontsFor(global_style);
  const accent = accent_color ?? style.visual.palette.accent;
  const textCol = text_color ?? style.visual.palette.text;
  const caps = signatureCaps(global_style);
  const halftone = grade_override === 'halftone' && caps.halftone > 0;

  // The focal point IS the highlight center unless overridden.
  const focal = punch_to ?? {x: highlight_box.x + highlight_box.w / 2, y: highlight_box.y + highlight_box.h / 2};

  const dHighlight = dur(DURATION.slow, vocab.tempo);
  const t = choreoBeats(
    {
      doc: 0,
      highlight: dur(DURATION.base, vocab.tempo),
      punch: dur(DURATION.base, vocab.tempo) + dHighlight + dur(DURATION.fast, vocab.tempo),
      caption: dur(DURATION.base, vocab.tempo) + dHighlight + dur(DURATION.fast, vocab.tempo) + dur(DURATION.base, vocab.tempo),
    },
    beats,
    tempo,
    fps,
  );
  const tDoc = t.doc;
  const tHighlight = t.highlight;
  const highlightFrames = dHighlight;
  const tPunch = t.punch;
  const tCaption = t.caption;

  const docEnter = interpolate(frame, [tDoc, tDoc + dur(DURATION.base, vocab.tempo)], [0, 1], {...clamp, easing: AE_EASE});
  const highlightP = interpolate(frame, [tHighlight, tHighlight + highlightFrames], [0, 1], clamp);
  const punchP = interpolate(frame, [tPunch, tPunch + dur(DURATION.slow, vocab.tempo)], [0, 1], {...clamp, easing: AE_SETTLE});

  // Punch brings the focal point to frame center (50%, 45%).
  const punchScale = 1 + punchP * 0.8;
  const targetX = 50;
  const targetY = 45;
  const punchX = punchP * (targetX - focal.x) * 0.9;
  const punchY = punchP * (targetY - focal.y) * 0.9;

  return (
    <SceneShell bg_image={bg_image ?? 'texture_dark.png'} accent_color={accent} global_style={global_style} scene_seed={scene_seed} transparent={transparent} ken_burns="none" darken={0.5} grade_override={grade_override}>
      {/* Document column — single centered axis; caption sits under the doc. */}
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
        <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 0}}>
          {/* Document card */}
          <div
            style={{
              position: 'relative',
              transform: `scale(${0.9 * docEnter + punchScale - 0.9}) translate(${punchX}%, ${punchY}%) rotate(${(1 - docEnter) * -1.5}deg)`,
              opacity: docEnter,
              boxShadow: '0 30px 80px rgba(0,0,0,0.7)',
              width: 'min(52%, 900px)',
            }}
          >
            {halftone ? (
              <HalftoneDoc strength={0.5}>
                <Img src={staticFile(document_image)} style={{display: 'block', width: '100%'}} />
              </HalftoneDoc>
            ) : (
              <Img src={staticFile(document_image)} style={{display: 'block', width: '100%'}} />
            )}
            {/* Marker highlight sweep — multiply blend reads as highlighter ink */}
            <div
              style={{
                position: 'absolute',
                left: `${highlight_box.x}%`,
                top: `${highlight_box.y}%`,
                width: `${highlight_box.w * highlightP}%`,
                height: `${highlight_box.h}%`,
                backgroundColor: accent,
                opacity: 0.38,
                mixBlendMode: 'multiply',
              }}
            />
          </div>

          {/* Caption — directly under the document, same axis, appears post-punch */}
          {caption ? (
            <div
              style={{
                marginTop: 40,
                maxWidth: 'min(52%, 900px)',
                opacity: cutIn(frame, tCaption, 4),
                transform: `translateY(${(1 - cutIn(frame, tCaption, 4)) * 12}px)`,
                textAlign: 'center',
              }}
            >
              <span style={{fontFamily: fonts.body, fontSize: 24, fontWeight: 500, color: textCol, lineHeight: 1.4, textShadow: '0 2px 8px rgba(0,0,0,0.8)'}}>
                {caption}
              </span>
            </div>
          ) : null}
        </div>
      </AbsoluteFill>

      {/* Kicker label — top-left text-safe zone */}
      {label ? (
        <div style={{position: 'absolute', top: 70, left: 96, opacity: cutIn(frame, tDoc, dur(DURATION.instant, vocab.tempo))}}>
          <Label text={label} accent={accent} startFrame={tDoc} global_style={global_style} />
        </div>
      ) : null}
    </SceneShell>
  );
};
