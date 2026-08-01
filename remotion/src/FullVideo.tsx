import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, Easing, Sequence, Series} from 'remotion';
import {TransitionSeries, linearTiming} from '@remotion/transitions';
import {fade} from '@remotion/transitions/fade';
import {slide} from '@remotion/transitions/slide';
import {IntroScene} from './scenes/Intro';
import {ContentScene} from './scenes/Content';
import {StatScene} from './scenes/Stat';
import {QuoteScene} from './scenes/Quote';
import {ListRevealScene} from './scenes/ListReveal';
import {ComparisonScene} from './scenes/Comparison';
import {PersonCardScene} from './scenes/PersonCard';
import {CrimeBoardScene} from './scenes/CrimeBoard';
import {OutroScene} from './scenes/Outro';
import {typeStyle} from './components/KineticText';

export interface FullVideoScene {
  type: 'intro' | 'content' | 'stat' | 'quote' | 'list' | 'comparison' | 'person' | 'crime-board' | 'outro';
  duration: number;
  props: Record<string, unknown>;
}

export interface FullVideoProps {
  scenes: FullVideoScene[];
  accent_color?: string;
  text_color?: string;
}

const fps = 30;

function renderScene(scene: FullVideoScene, accent: string, text: string) {
  const baseProps = {accent_color: accent, text_color: text};
  switch (scene.type) {
    case 'intro':
      return <IntroScene {...baseProps} {...(scene.props as any)} />;
    case 'content':
      return <ContentScene {...baseProps} {...(scene.props as any)} />;
    case 'stat':
      return <StatScene {...baseProps} {...(scene.props as any)} />;
    case 'quote':
      return <QuoteScene {...baseProps} {...(scene.props as any)} />;
    case 'list':
      return <ListRevealScene {...baseProps} {...(scene.props as any)} />;
    case 'comparison':
      return <ComparisonScene {...baseProps} {...(scene.props as any)} />;
    case 'person':
      return <PersonCardScene {...baseProps} {...(scene.props as any)} />;
    case 'crime-board':
      return <CrimeBoardScene {...baseProps} {...(scene.props as any)} />;
    case 'outro':
      return <OutroScene {...baseProps} {...(scene.props as any)} />;
    default:
      return null;
  }
}

export const FullVideo: React.FC<FullVideoProps> = ({
  scenes,
  accent_color = '#ff6b35',
  text_color = '#ffffff',
}) => {
  return (
    <AbsoluteFill style={{backgroundColor: '#000'}}>
      <TransitionSeries>
        {scenes.map((scene, i) => {
          const durationInFrames = Math.round(scene.duration * fps);
          const isLast = i === scenes.length - 1;
          const transitionDuration = 18;

          return (
            <React.Fragment key={i}>
              <TransitionSeries.Sequence durationInFrames={durationInFrames}>
                {renderScene(scene, accent_color, text_color)}
              </TransitionSeries.Sequence>
              {!isLast && (
                <TransitionSeries.Transition
                  presentation={i % 2 === 0 ? fade() : slide({from: 'right'})}
                  timing={linearTiming({durationInFrames: transitionDuration})}
                />
              )}
            </React.Fragment>
          );
        })}
      </TransitionSeries>
    </AbsoluteFill>
  );
};
