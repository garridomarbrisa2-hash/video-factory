/**
 * Director beat-choreography contract (Phase 8, P0).
 *
 * The problem: every scene used to compute its own beat timing from fixed
 * tokens (`tText = t0 + dur(DURATION.fast)`) — the director could pick a scene
 * type but could never move a single beat. That's the #1 gap vs a professional
 * edit (docs/plans/PHASE_8_DIRECTOR_AUTHORITY.md §B1).
 *
 * The contract: each scene names its beats (e.g. Content: plate/text/accent/subtext)
 * and ships token-computed DEFAULTS so existing timelines render identically. The
 * director may override ANY beat by name — in SECONDS from scene start (the
 * orchestrator/timeline already think in seconds; frames stay a component detail).
 *
 * Ownership stays clean:
 *   director → WHICH beat, WHEN (seconds), how fast (`tempo`), hold the last beat.
 *   style    → the VALUES (easing curves, entrance durations, tempo base).
 *   scene    → the DEFAULTS + how beats compose (what rises, what draws).
 *
 * A beat value of SECONDS keeps the director's intent in editorial units; the
 * scene converts to frames via the live fps. Style `tempo` scales the defaults
 * only — never the director's explicit beats (their timing is absolute intent).
 */

/** A scene's named beat map: beat name → seconds from scene start. */
export type SceneBeats = Record<string, number>;

/**
 * Resolve a beat time to a frame.
 *   beats?.[name]  → director's explicit time in seconds (wins, fps-converted)
 *   defaultFrames  → the scene's token-computed default (already style-tempo-scaled)
 * Returns the default when the director didn't set the beat.
 */
export function beat(
  beats: SceneBeats | undefined,
  name: string,
  defaultFrames: number,
  fps: number,
): number {
  const s = beats?.[name];
  if (s == null || Number.isNaN(s)) return defaultFrames;
  return Math.max(0, Math.round(s * fps));
}

/**
 * Resolve a whole beat map at once. `defaults` is beat-name → token default
 * (in frames, already tempo-scaled). Returns beat-name → frames, with any
 * director overrides (seconds) applied. Keeps scene code terse:
 *   const t = resolveBeats(beats, {plate: t0, text: tText, subtext: tSub}, fps);
 *   ... startFrame={t.text}
 */
export function resolveBeats(
  beats: SceneBeats | undefined,
  defaults: Record<string, number>,
  fps: number,
): Record<string, number> {
  const out: Record<string, number> = {};
  for (const k of Object.keys(defaults)) {
    out[k] = beat(beats, k, defaults[k], fps);
  }
  return out;
}

/**
 * Scene-level rhythm multiplier (director intent). Scales the token DEFAULTS so
 * the whole scene breathes faster/slower without the director timing each beat.
 * Explicit `beats` still win over the scaled default.
 *   tempo > 1 → slower/heavier (crime); < 1 → tighter (modern bump).
 * Clamped to a sane editorial range so a typo can't freeze a scene.
 */
export function applyTempo(defaultFrames: number, tempo: number | undefined): number {
  if (tempo == null || Number.isNaN(tempo)) return defaultFrames;
  const t = Math.min(2.5, Math.max(0.4, tempo));
  return Math.max(1, Math.round(defaultFrames * t));
}

/** Scale every default in a map by the director's `tempo`. */
export function tempoDefaults(
  defaults: Record<string, number>,
  tempo: number | undefined,
): Record<string, number> {
  const out: Record<string, number> = {};
  for (const k of Object.keys(defaults)) out[k] = applyTempo(defaults[k], tempo);
  return out;
}

/**
 * Convenience: the full chain for a scene. Build token defaults, scale by the
 * director's `tempo`, then apply explicit `beats` overrides.
 *   const t = choreoBeats({plate: t0, text: tText, subtext: tSub}, beats, tempo, fps);
 */
export function choreoBeats(
  tokenDefaults: Record<string, number>,
  beats: SceneBeats | undefined,
  tempo: number | undefined,
  fps: number,
): Record<string, number> {
  return resolveBeats(beats, tempoDefaults(tokenDefaults, tempo), fps);
}
