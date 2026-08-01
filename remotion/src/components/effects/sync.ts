/**
 * VO→visual sync helpers (Phase 8, P1).
 *
 * `word_times` is [[word, t_seconds], ...] relative to scene start, produced by
 * the orchestrator (native provider timings, or prosody-estimated). These map a
 * spoken word to a frame so text, punch, and shake land on the actual syllables.
 */

/** Normalize a word for matching (lowercase, strip punctuation). */
function norm(w: string): string {
  return w.toLowerCase().replace(/[^a-z0-9]/g, '');
}

/**
 * Onset frame of the FIRST word of `phrase` within `word_times`.
 * `fps` converts the stored seconds to frames. Returns null when not found —
 * callers then keep their token default beat.
 */
export function phraseOnsetFrame(
  wordTimes: Array<[string, number]> | undefined,
  phrase: string | null | undefined,
  fps: number,
): number | null {
  if (!wordTimes || !phrase) return null;
  const first = norm(phrase.trim().split(/\s+/)[0] ?? '');
  if (!first) return null;
  for (const [w, t] of wordTimes) {
    if (norm(String(w)) === first) return Math.max(0, Math.round(t * fps));
  }
  return null;
}

/**
 * Onset frame of the first NUMERIC token in `word_times` (for stat scenes —
 * the punch lands when the number is spoken). Matches digits, %, $, decimals.
 */
export function numberOnsetFrame(
  wordTimes: Array<[string, number]> | undefined,
  fps: number,
): number | null {
  if (!wordTimes) return null;
  for (const [w, t] of wordTimes) {
    if (/\d/.test(String(w))) return Math.max(0, Math.round(t * fps));
  }
  return null;
}
