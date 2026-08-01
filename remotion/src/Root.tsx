import React from 'react';
import {Composition} from 'remotion';
import {FullVideo} from './FullVideo';
import {IntroScene} from './scenes/Intro';
import {ContentScene} from './scenes/Content';
import {StatScene} from './scenes/Stat';
import {QuoteScene} from './scenes/Quote';
import {ListRevealScene} from './scenes/ListReveal';
import {ComparisonScene} from './scenes/Comparison';
import {PersonCardScene} from './scenes/PersonCard';
import {OutroScene} from './scenes/Outro';
import {DocumentScene} from './scenes/Document';
import {MapScene} from './scenes/Map';
import {CrimeBoardScene} from './scenes/CrimeBoard';

const fps = 30;
const width = 1920;
const height = 1080;

// Composition IDs: only a-z0-9 and hyphens allowed
export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="full-video"
        component={FullVideo}
        durationInFrames={fps * 60}
        fps={fps}
        width={width}
        height={height}
        defaultProps={{
          scenes: [],
          accent_color: '#ff6b35',
          text_color: '#ffffff',
        }}
      />
      <Composition
        id="intro"
        component={IntroScene}
        durationInFrames={fps * 4}
        fps={fps}
        width={width}
        height={height}
        defaultProps={{
          hook_text: 'Stop Doing This Wrong',
          bg_image: '1.png',
          accent_color: '#ff6b35',
          text_color: '#ffffff',
          label: 'WATCH THIS',
        }}
      />
      <Composition
        id="content"
        component={ContentScene}
        durationInFrames={fps * 5}
        fps={fps}
        width={width}
        height={height}
        defaultProps={{
          text: 'Most people get this backwards',
          subtext: 'And it is costing them years of progress',
          bg_image: '2.png',
          accent_color: '#ff6b35',
          text_color: '#ffffff',
          label: 'INSIGHT',
        }}
      />
      <Composition
        id="stat"
        component={StatScene}
        durationInFrames={fps * 4}
        fps={fps}
        width={width}
        height={height}
        defaultProps={{
          stat_text: '93%',
          context_text: 'of people never finish what they start',
          bg_image: '3.png',
          accent_color: '#ff6b35',
          text_color: '#ffffff',
        }}
      />
      <Composition
        id="quote"
        component={QuoteScene}
        durationInFrames={fps * 5}
        fps={fps}
        width={width}
        height={height}
        defaultProps={{
          quote_text: 'Discipline is choosing between what you want now and what you want most.',
          attribution: 'Abraham Lincoln',
          bg_image: '4.png',
          accent_color: '#ff6b35',
          text_color: '#ffffff',
        }}
      />
      <Composition
        id="list-reveal"
        component={ListRevealScene}
        durationInFrames={fps * 6}
        fps={fps}
        width={width}
        height={height}
        defaultProps={{
          title: 'THE RULES',
          items: ['Start before ready', 'Ship daily', 'Refuse average', 'Compound small wins'],
          bg_image: '5.png',
          accent_color: '#ff6b35',
          text_color: '#ffffff',
        }}
      />
      <Composition
        id="comparison"
        component={ComparisonScene}
        durationInFrames={fps * 5}
        fps={fps}
        width={width}
        height={height}
        defaultProps={{
          left_text: 'Amateur',
          right_text: 'Pro',
          left_image: '2.png',
          right_image: '4.png',
          accent_color: '#ff6b35',
          text_color: '#ffffff',
          vs_label: 'VS',
        }}
      />
      <Composition
        id="person-card"
        component={PersonCardScene}
        durationInFrames={fps * 5}
        fps={fps}
        width={width}
        height={height}
        defaultProps={{
          name: 'Alex Rivera',
          title: 'Founder, Atlas Labs',
          quote: 'We wasted two years chasing shortcuts. Real growth started the day we stopped.',
          bg_image: '1.png',
          accent_color: '#ff6b35',
          text_color: '#ffffff',
        }}
      />
      <Composition
        id="document"
        component={DocumentScene}
        durationInFrames={fps * 6}
        fps={fps}
        width={width}
        height={height}
        defaultProps={{
          document_image: '1.png',
          highlight_box: {x: 20, y: 40, w: 60, h: 8},
          punch_to: {x: 50, y: 44},
          label: 'EXHIBIT A',
          caption: 'The receipt that changed everything.',
          bg_image: '2.png',
          accent_color: '#ff6b35',
          text_color: '#ffffff',
        }}
      />
      <Composition
        id="map"
        component={MapScene}
        durationInFrames={fps * 6}
        fps={fps}
        width={width}
        height={height}
        defaultProps={{
          map_image: '1.png',
          from_point: {x: 20, y: 60},          to_point: {x: 75, y: 35},
          from_label: 'Start',
          to_label: 'Destination',
          caption: 'Three thousand miles, one answer.',
          bg_image: '2.png',
          accent_color: '#ff6b35',
          text_color: '#ffffff',
        }}
      />
      <Composition
        id="outro"
        component={OutroScene}
        durationInFrames={fps * 4}
        fps={fps}
        width={width}
        height={height}
        defaultProps={{
          cta_text: 'Go Build Something',
          subtext: 'Subscribe for more',
          bg_image: 'thumbnail.png',
          accent_color: '#ff6b35',
          text_color: '#ffffff',
        }}
      />
      <Composition
        id="crime-board"
        component={CrimeBoardScene}
        durationInFrames={fps * 6}
        fps={fps}
        width={width}
        height={height}
        defaultProps={{
          board_items: [
            {src: '1.png'},
            {label: 'March 14, 1997'},
            {src: '2.png'},
            {label: 'The Accomplice'},
          ],
          bg_image: 'texture_dark.png',
          accent_color: '#c0392b',
          global_style: 'crime',
        }}
      />
    </>
  );
};
