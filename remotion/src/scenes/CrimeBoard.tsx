import React from 'react';
import {AbsoluteFill} from 'remotion';
import {SceneShell} from '../components/SceneShell';
import {CrimeBoard, type BoardItem} from '../components/effects/signature/CrimeBoard';
import {signatureCaps} from '../components/tokens';
import {getGlobalStyle, normalizeStyleId} from '../components/styleSystem';

interface CrimeBoardSceneProps {
  /** Evidence items: images (public/) or text labels (names/places/dates). */
  board_items: BoardItem[];
  bg_image?: string | null;
  accent_color?: string;
  global_style?: string;
  scene_seed?: number;
  transparent?: boolean;
  /** Per-scene grade intent (P7): era/mood signpost mapped onto the style palette. */
  grade_override?: string;
}

/**
 * Crime-board scene (§18) — the "connecting the dots" evidence wall. Opt-in:
 * the director picks this scene type for a connection/evidence beat. Item count
 * is capped by the style's signatureCaps.crimeBoard (0 = the style forbids it).
 */
export const CrimeBoardScene: React.FC<CrimeBoardSceneProps> = ({
  board_items,
  bg_image,
  accent_color,
  global_style = 'crime',
  scene_seed = 0,
  transparent = false,
  grade_override,
}) => {
  const style = getGlobalStyle(normalizeStyleId(global_style));
  const accent = accent_color ?? style.visual.palette.accent;
  const caps = signatureCaps(global_style);
  const items = (board_items ?? []).slice(0, Math.max(0, caps.crimeBoard));

  return (
    <SceneShell bg_image={bg_image ?? 'texture_dark.png'} accent_color={accent} global_style={global_style} scene_seed={scene_seed} transparent={transparent} ken_burns="none" darken={0.55} grade_override={grade_override}>
      <AbsoluteFill>
        {items.length > 0 ? <CrimeBoard items={items} accent={accent} global_style={global_style} seed={scene_seed} /> : null}
      </AbsoluteFill>
    </SceneShell>
  );
};
