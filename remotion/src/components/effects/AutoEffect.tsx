/**
 * Scene-facing entry point for automatic effect selection. Scenes call
 * <AutoEffect> (for text/title/number/highlight — props-driven) or
 * <AutoWrapEffect> (for camera/transition — children-driven) instead of
 * hardcoding one component; the registry (effectRegistry.ts) picks which
 * concrete effect renders, based on scene type + energy + style, with
 * built-in anti-repetition across neighboring scenes.
 */
import React from 'react';
import {normalizeStyleId} from '../styleSystem';
import {pickEffect, type EffectCategory, type SceneEnergy} from './effectRegistry';

interface AutoEffectBaseProps {
  category: EffectCategory;
  sceneType: string;
  energy?: SceneEnergy;
  global_style?: string;
  /** Anti-repeat + rotation key — pass the scene's scene_seed (its index in the episode). */
  scene_seed?: number;
}

/** Props-driven effects (title/text/number/highlight): pass whatever the
 *  chosen component needs (text, color, accent, startFrame, ...) via rest props. */
export const AutoEffect: React.FC<AutoEffectBaseProps & Record<string, unknown>> = ({
  category,
  sceneType,
  energy,
  global_style,
  scene_seed = 0,
  ...rest
}) => {
  const style = normalizeStyleId(global_style);
  const {Component} = pickEffect(category, {sceneType, energy, style, sceneIndex: scene_seed});
  return <Component global_style={global_style} {...rest} />;
};

/** Children-driven effects (camera/transition): wraps content instead of
 *  rendering text directly. */
export const AutoWrapEffect: React.FC<
  AutoEffectBaseProps & {children: React.ReactNode} & Record<string, unknown>
> = ({category, sceneType, energy, global_style, scene_seed = 0, children, ...rest}) => {
  const style = normalizeStyleId(global_style);
  const {Component} = pickEffect(category, {sceneType, energy, style, sceneIndex: scene_seed});
  return (
    <Component global_style={global_style} {...rest}>
      {children}
    </Component>
  );
};
