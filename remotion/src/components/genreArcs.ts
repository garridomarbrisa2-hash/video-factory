/**
 * Genre story arcs — scene-progression grammar per script format.
 *
 * This is the STORY layer, separate from the VISUAL style. A `crime` style
 * (colors/fonts/grade) can carry a `documentary` arc (slow build → evidence →
 * reveal) OR a `news` arc (breaking → stat → implication). The style JSON's
 * `script.format` field picks the arc; the arc tells the director HOW to pace
 * scene types, energy, and when to go silent (bare).
 *
 * Philosophy (user-stated): assemble a collection of assets into a story that
 * fits the script, with genre-specific grammar.
 */

export type GenreArcId = 'documentary' | 'news' | 'essay' | 'listicle' | 'explainer';

export interface ArcBeat {
  /** Beat name (context, evidence, turn, reveal, reflection…). */
  beat: string;
  /** Scene types that serve this beat. */
  sceneTypes: string[];
  /** Recommended energy for this beat. */
  energy: 'low' | 'mid' | 'high';
  /** Whether this beat is a good candidate for a bare (no-text) scene. */
  allowBare: boolean;
  /** Rough share of the video this beat occupies (0..1). */
  share: number;
}

export interface GenreArc {
  id: GenreArcId;
  name: string;
  /** Ordered beats — the story's spine. */
  beats: ArcBeat[];
  /** Text density guidance: 0 = mostly bare, 1 = text on nearly every scene. */
  textDensity: number;
}

/** script.format values → arc. Falls back to essay. */
const FORMAT_TO_ARC: Record<string, GenreArcId> = {
  documentary: 'documentary',
  mystery_investigation: 'documentary',
  crisis_news: 'news',
  breaking: 'news',
  listicle: 'listicle',
  educational: 'explainer',
  explainer: 'explainer',
  storytelling: 'essay',
  essay: 'essay',
};

const ARCS: Record<GenreArcId, GenreArc> = {
  documentary: {
    id: 'documentary',
    name: 'Documentary',
    textDensity: 0.6,
    beats: [
      {beat: 'context', sceneTypes: ['intro', 'content'], energy: 'low', allowBare: true, share: 0.15},
      {beat: 'build', sceneTypes: ['content', 'person', 'map'], energy: 'mid', allowBare: true, share: 0.3},
      {beat: 'evidence', sceneTypes: ['document', 'content', 'comparison'], energy: 'mid', allowBare: false, share: 0.25},
      {beat: 'turn', sceneTypes: ['stat', 'content'], energy: 'high', allowBare: false, share: 0.12},
      {beat: 'reveal', sceneTypes: ['content', 'document'], energy: 'high', allowBare: false, share: 0.1},
      {beat: 'reflection', sceneTypes: ['quote', 'content', 'outro'], energy: 'low', allowBare: true, share: 0.08},
    ],
  },
  news: {
    id: 'news',
    name: 'News / Crisis',
    textDensity: 0.85,
    beats: [
      {beat: 'breaking', sceneTypes: ['intro'], energy: 'high', allowBare: false, share: 0.12},
      {beat: 'fact', sceneTypes: ['content', 'stat'], energy: 'mid', allowBare: false, share: 0.35},
      {beat: 'stakes', sceneTypes: ['comparison', 'content'], energy: 'mid', allowBare: false, share: 0.25},
      {beat: 'implication', sceneTypes: ['stat', 'content'], energy: 'high', allowBare: false, share: 0.18},
      {beat: 'outlook', sceneTypes: ['content', 'outro'], energy: 'low', allowBare: true, share: 0.1},
    ],
  },
  essay: {
    id: 'essay',
    name: 'Essay / Storytelling',
    textDensity: 0.7,
    beats: [
      {beat: 'hook', sceneTypes: ['intro'], energy: 'high', allowBare: false, share: 0.12},
      {beat: 'build', sceneTypes: ['content', 'person'], energy: 'mid', allowBare: true, share: 0.35},
      {beat: 'deepen', sceneTypes: ['quote', 'content', 'comparison'], energy: 'mid', allowBare: true, share: 0.28},
      {beat: 'payoff', sceneTypes: ['stat', 'content'], energy: 'high', allowBare: false, share: 0.15},
      {beat: 'takeaway', sceneTypes: ['content', 'outro'], energy: 'low', allowBare: true, share: 0.1},
    ],
  },
  listicle: {
    id: 'listicle',
    name: 'Listicle',
    textDensity: 0.9,
    beats: [
      {beat: 'tease', sceneTypes: ['intro'], energy: 'high', allowBare: false, share: 0.1},
      {beat: 'items', sceneTypes: ['content', 'list', 'stat'], energy: 'mid', allowBare: false, share: 0.72},
      {beat: 'top', sceneTypes: ['content', 'stat'], energy: 'high', allowBare: false, share: 0.1},
      {beat: 'recap', sceneTypes: ['list', 'outro'], energy: 'low', allowBare: false, share: 0.08},
    ],
  },
  explainer: {
    id: 'explainer',
    name: 'Explainer',
    textDensity: 0.8,
    beats: [
      {beat: 'promise', sceneTypes: ['intro'], energy: 'mid', allowBare: false, share: 0.12},
      {beat: 'steps', sceneTypes: ['content', 'list'], energy: 'mid', allowBare: false, share: 0.68},
      {beat: 'result', sceneTypes: ['stat', 'content'], energy: 'mid', allowBare: false, share: 0.12},
      {beat: 'recap', sceneTypes: ['content', 'outro'], energy: 'low', allowBare: false, share: 0.08},
    ],
  },
};

/** Resolve a script.format string to its arc (default essay). */
export function arcFor(format: string | null | undefined): GenreArc {
  const key = (format ?? '').trim().toLowerCase();
  const id = FORMAT_TO_ARC[key] ?? 'essay';
  return ARCS[id];
}

/** Get an arc directly by id. */
export function arcById(id: GenreArcId): GenreArc {
  return ARCS[id];
}

/**
 * Which beat does scene `index` (0-based) of `total` fall into?
 * Walks beats by cumulative share. Returns the beat + its guidance.
 */
export function beatForScene(arc: GenreArc, index: number, total: number): ArcBeat {
  if (total <= 1) return arc.beats[0];
  const pos = index / (total - 1);
  let acc = 0;
  for (const b of arc.beats) {
    acc += b.share;
    if (pos <= acc) return b;
  }
  return arc.beats[arc.beats.length - 1];
}
