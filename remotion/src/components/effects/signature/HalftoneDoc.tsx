/**
 * HalftoneDoc — a print-halftone dot screen over a document (§12). The crime/
 * history "newspaper clipping" beat: the document reads as scanned print, not a
 * clean photo. Pure CSS radial-gradient dot pattern, multiply-blended + slight
 * desaturate. Opt-in (grade_override=halftone on a document scene).
 */
import React from 'react';

export const HalftoneDoc: React.FC<{
  /** Dot pitch (px). Smaller = finer print. */
  pitch?: number;
  /** Overlay strength 0..1. */
  strength?: number;
  children?: React.ReactNode;
}> = ({pitch = 5, strength = 0.5, children}) => {
  return (
    <div style={{position: 'relative', display: 'inline-block', filter: 'grayscale(0.5) contrast(1.08) sepia(0.18)'}}>
      {children}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          pointerEvents: 'none',
          backgroundImage: `radial-gradient(circle, rgba(0,0,0,${0.55 * strength}) ${(pitch / 3).toFixed(1)}px, transparent ${(pitch / 2.4).toFixed(1)}px)`,
          backgroundSize: `${pitch}px ${pitch}px`,
          mixBlendMode: 'multiply',
          opacity: strength,
        }}
      />
    </div>
  );
};
