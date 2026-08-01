import React from 'react';
import {useCurrentFrame} from 'remotion';
import {type EditStyle} from './editMotion';
import {getGlobalStyle, normalizeStyleId} from './styleSystem';
import {DURATION, PHRASE_STAGGER, STAGGER, dur, motionVocab} from './tokens';
import {clip, cutIn, fadeIn, maskWipe, underlineDraw} from './choreo';
import {fontsFor} from './effects/fonts';
import {textSkinFor, plateStyle, kickerStyle} from './effects/textSkin';

/** Base type style — font family is resolved per style at component level. */
export function typeStyleFor(global_style?: string): React.CSSProperties {
  return {
    fontFamily: fontsFor(global_style).body,
    textShadow: '0 2px 6px rgba(0,0,0,0.75)',
  };
}
/** @deprecated use typeStyleFor(style) — kept for scene files mid-migration. */
export const typeStyle = {
  fontFamily: 'Arial, Helvetica, sans-serif',
  textShadow: '0 2px 6px rgba(0,0,0,0.75)',
} as const;

/** Split text on **markers** → array of {text, accent} segments. */
function parseEmphasis(text: string): {text: string; accent: boolean}[] {
  return text.split(/\*\*(.+?)\*\*/g).map((p, i) => ({text: p, accent: i % 2 === 1}));
}

// ---------------------------------------------------------------------------
// OpacityCut — hard linear opacity (editorial micro-entrance)
// ---------------------------------------------------------------------------
export const OpacityCut: React.FC<{
  children: React.ReactNode;
  startFrame?: number;
  frames?: number;
}> = ({children, startFrame = 0, frames = 3}) => {
  const frame = useCurrentFrame();
  const opacity =
    frames <= 1 ? (frame >= startFrame ? 1 : 0) : cutIn(frame, startFrame, frames);
  return <div style={{opacity}}>{children}</div>;
};

// ---------------------------------------------------------------------------
// MaskWipe — AE linear wipe via clip-path
// ---------------------------------------------------------------------------
export const MaskWipe: React.FC<{
  children: React.ReactNode;
  startFrame?: number;
  frames?: number;
  direction?: 'left' | 'right' | 'up' | 'down';
  edit_style?: EditStyle;
  global_style?: string;
}> = ({children, startFrame = 0, frames, direction = 'left', global_style}) => {
  const frame = useCurrentFrame();
  const vocab = motionVocab(global_style);
  const n = frames ?? dur(DURATION.base, vocab.tempo);
  const p = maskWipe(frame, startFrame, n);
  const clipPath =
    direction === 'right' ? clip.rl(p) : direction === 'up' ? clip.up(p) : direction === 'down' ? clip.down(p) : clip.lr(p);
  return <div style={{clipPath, WebkitClipPath: clipPath}}>{children}</div>;
};

// ---------------------------------------------------------------------------
// EmphasisText — text with **keyword** accent spans (VidRush keyword highlight)
// ---------------------------------------------------------------------------
export const EmphasisText: React.FC<{
  text: string;
  accent: string;
  color?: string;
  fontSize?: number;
  fontWeight?: number | string;
  align?: 'left' | 'center' | 'right';
  maxWidth?: number | string;
  lineHeight?: number;
  uppercase?: boolean;
  italic?: boolean;
  fontFamily?: string;
  global_style?: string;
}> = ({
  text,
  accent,
  color = '#ffffff',
  fontSize = 48,
  fontWeight = 700,
  align = 'left',
  maxWidth = '100%',
  lineHeight = 1.2,
  uppercase = false,
  italic = false,
  fontFamily,
  global_style,
}) => (
  <div
    style={{
      fontFamily: fontFamily ?? fontsFor(global_style).body,
      textShadow: '0 2px 6px rgba(0,0,0,0.75)',
      fontSize,
      fontWeight,
      color,
      textAlign: align,
      maxWidth,
      lineHeight,
      textTransform: uppercase ? 'uppercase' : 'none',
      fontStyle: italic ? 'italic' : 'normal',
    }}
  >
    {parseEmphasis(text).map((seg, i) =>
      seg.accent ? (
        <span key={i} style={{color: accent}}>
          {seg.text}
        </span>
      ) : (
        <span key={i}>{seg.text}</span>
      ),
    )}
  </div>
);

// ---------------------------------------------------------------------------
// Title — style-driven entrance (mask / tracking / cut), optional exit
// ---------------------------------------------------------------------------
export const Title: React.FC<{
  text: string;
  accent: string;
  color?: string;
  fontSize?: number;
  fontWeight?: number | string;
  align?: 'left' | 'center' | 'right';
  maxWidth?: number | string;
  lineHeight?: number;
  uppercase?: boolean;
  startFrame?: number;
  global_style?: string;
}> = ({
  text,
  accent,
  color = '#ffffff',
  fontSize = 64,
  fontWeight = 700,
  align = 'left',
  maxWidth = '100%',
  lineHeight = 1.15,
  uppercase = false,
  startFrame = 0,
  global_style,
}) => {
  const frame = useCurrentFrame();
  const vocab = motionVocab(global_style);
  const fonts = fontsFor(global_style);
  const n = dur(DURATION.slow, vocab.tempo);

  const inner = (
    <EmphasisText
      text={text}
      accent={accent}
      color={color}
      fontSize={fontSize}
      fontWeight={fontWeight}
      align={align}
      maxWidth={maxWidth}
      lineHeight={lineHeight}
      uppercase={uppercase}
      fontFamily={fonts.display}
      global_style={global_style}
    />
  );

  // One clean entrance, then the title sits still. The xfade handles the cut.
  if (vocab.titleMode === 'cut') {
    return <div style={{opacity: cutIn(frame, startFrame, dur(DURATION.instant, vocab.tempo))}}>{inner}</div>;
  }
  const p = maskWipe(frame, startFrame, n);
  return <div style={{clipPath: clip.lr(p), WebkitClipPath: clip.lr(p)}}>{inner}</div>;
};

// ---------------------------------------------------------------------------
// KeywordLine — text fades in once, then a single calm underline draws.
// No sliding highlight boxes, no exit animation (the xfade handles the cut).
// ---------------------------------------------------------------------------
export const KeywordLine: React.FC<{
  text: string;
  accent: string;
  color?: string;
  fontSize?: number;
  fontWeight?: number | string;
  align?: 'left' | 'center' | 'right';
  startFrame?: number;
  global_style?: string;
}> = ({text, accent, color = '#ffffff', fontSize = 40, fontWeight = 700, align = 'left', startFrame = 0, global_style}) => {
  const frame = useCurrentFrame();
  const vocab = motionVocab(global_style);
  const enterFrames = dur(DURATION.base, vocab.tempo);
  const textOp = fadeIn(frame, startFrame, enterFrames);
  // One subtle underline draws after the text lands (standard/history/crime only).
  const showUnderline = vocab.accentMode === 'underline';
  const accentP = showUnderline
    ? underlineDraw(frame, startFrame + enterFrames + 2, dur(DURATION.slow, vocab.tempo))
    : 0;

  return (
    <div style={{textAlign: align}}>
      <div style={{position: 'relative', display: 'inline-block'}}>
        <div style={{opacity: textOp}}>
          <EmphasisText
            text={text}
            accent={accent}
            color={color}
            fontSize={fontSize}
            fontWeight={fontWeight}
            align={align}
            lineHeight={1.25}
          />
        </div>
        {showUnderline ? (
          <div
            style={{
              position: 'absolute',
              left: 0,
              bottom: -6,
              height: 2,
              width: `${accentP}%`,
              backgroundColor: accent,
              opacity: 0.7,
            }}
          />
        ) : null}
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// BodyText — a subordinate line that lands after the title (staggered beat)
// ---------------------------------------------------------------------------
export const BodyText: React.FC<{
  text: string;
  accent?: string;
  color?: string;
  fontSize?: number;
  align?: 'left' | 'center' | 'right';
  startFrame?: number;
  global_style?: string;
}> = ({text, accent = '#ffffff', color = 'rgba(255,255,255,0.86)', fontSize = 24, align = 'left', startFrame = 0, global_style}) => {
  const frame = useCurrentFrame();
  const vocab = motionVocab(global_style);
  const op = cutIn(frame, startFrame, dur(DURATION.instant, vocab.tempo));
  return (
    <div style={{opacity: op}}>
      <EmphasisText text={text} accent={accent} color={color} fontSize={fontSize} fontWeight={400} align={align} lineHeight={1.4} />
    </div>
  );
};

// ---------------------------------------------------------------------------
// LowerThirdPlate — PER-STYLE text grammar (textSkin), not one shared black box.
// The plate/edge/kicker treatment comes from effects/textSkin.ts so each style
// reads as its own editorial hand (crime dossier, history archival plate,
// modern chip, minimalist bare, standard soft). Slides in, stages children.
// ---------------------------------------------------------------------------
export const LowerThirdPlate: React.FC<{
  children: React.ReactNode;
  startFrame?: number;
  accent_color?: string;
  maxWidth?: number | string;
  edit_style?: EditStyle;
  global_style?: string;
}> = ({children, startFrame = 0, accent_color, maxWidth = '62%', global_style}) => {
  const frame = useCurrentFrame();
  const style = getGlobalStyle(normalizeStyleId(global_style));
  const vocab = motionVocab(global_style);
  const accent = accent_color ?? style.visual.palette.accent;
  const skin = textSkinFor(global_style);
  const n = dur(DURATION.base, vocab.tempo);
  const p = maskWipe(frame, startFrame, n);

  return (
    <div
      style={{
        clipPath: clip.lr(p),
        WebkitClipPath: clip.lr(p),
        ...plateStyle(skin, accent, maxWidth),
      }}
    >
      {children}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Label — small kicker above a title (accent, tracked caps, style mono face)
// ---------------------------------------------------------------------------
export const Label: React.FC<{
  text: string;
  accent: string;
  startFrame?: number;
  global_style?: string;
}> = ({text, accent, startFrame = 0, global_style}) => {
  const frame = useCurrentFrame();
  const vocab = motionVocab(global_style);
  const skin = textSkinFor(global_style);
  const op = cutIn(frame, startFrame, dur(DURATION.instant, vocab.tempo));
  return (
    <div style={{opacity: op, ...kickerStyle(skin, accent, global_style)}}>
      {text}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Rule — static accent rule (no scaleX grow)
// ---------------------------------------------------------------------------
export const Rule: React.FC<{color: string; width?: number | string; height?: number}> = ({
  color,
  width = 40,
  height = 2,
}) => <div style={{width, height, backgroundColor: color, flexShrink: 0}} />;

// ---------------------------------------------------------------------------
// Legacy aliases (back-compat)
// ---------------------------------------------------------------------------
export const TitleLine: React.FC<{
  text: string;
  fontSize?: number;
  fontWeight?: number | string;
  color?: string;
  align?: 'left' | 'center' | 'right';
  maxWidth?: number | string;
  lineHeight?: number;
  uppercase?: boolean;
}> = ({text, fontSize = 48, fontWeight = 700, color = '#ffffff', align = 'left', maxWidth = '100%', lineHeight = 1.2, uppercase = false}) => (
  <div style={{...typeStyle, fontSize, fontWeight, color, textAlign: align, maxWidth, lineHeight, textTransform: uppercase ? 'uppercase' : 'none'}}>
    {text}
  </div>
);

export const StatReveal: React.FC<{
  children: React.ReactNode;
  startFrame?: number;
  edit_style?: EditStyle;
  global_style?: string;
}> = ({children, startFrame = 0}) => <OpacityCut startFrame={startFrame} frames={3}>{children}</OpacityCut>;

export const KineticWords: React.FC<{
  text: string;
  startFrame?: number;
  fontSize?: number;
  fontWeight?: number | string;
  color?: string;
  align?: 'left' | 'center' | 'right';
  maxWidth?: number | string;
  lineHeight?: number;
  letterSpacing?: number;
  uppercase?: boolean;
  edit_style?: EditStyle;
}> = ({text, startFrame = 0, fontSize = 48, fontWeight = 700, color = '#fff', align = 'center', maxWidth = '90%', lineHeight = 1.2, uppercase = false, edit_style}) => (
  <MaskWipe startFrame={startFrame} global_style={edit_style}>
    <TitleLine text={text} fontSize={fontSize} fontWeight={fontWeight} color={color} align={align} maxWidth={maxWidth} lineHeight={lineHeight} uppercase={uppercase} />
  </MaskWipe>
);

export const FadeUp: React.FC<{
  children: React.ReactNode;
  startFrame?: number;
  duration?: number;
  fromY?: number;
  edit_style?: EditStyle;
}> = ({children, startFrame = 0, duration = 4}) => <OpacityCut startFrame={startFrame} frames={duration}>{children}</OpacityCut>;

export const AccentBar: React.FC<{color: string; startFrame?: number; width?: number | string; height?: number}> = ({color, width = 40, height = 2}) => (
  <Rule color={color} width={width} height={height} />
);

export const BlockText = KineticWords;
export const Emphasis = EmphasisText;
export {STAGGER, PHRASE_STAGGER};
