# Skill: Script Writer (style-aware)

## Role
Turn a brief/topic into a retention-optimized YouTube script (hook + body + CTA) whose **pacing and rhythm obey the selected global style**.

## Input
- topic / brief
- target duration (minutes)
- **global_style** — from `pipeline/intelligence/select_style.py` (`--style` override wins)
- The matching style JSON in `pipeline/intelligence/styles/<id>.json`

## Style constraints (read from style JSON `script` block)

| Field | What you must do |
|-------|------------------|
| `talking_points_per_min` (0.5 — VidRush golden rule) | Compute point count: `duration_min × 0.5`. 6–8 min → 4–5 points, 10–12 min → 7–8 points, 30–40 min → 20–30 points. Never exceed. |
| `format` | Structure the body after it: `mystery_investigation` (mystery → investigation → details → truth), `documentary` (context → situation → perspectives → implications), `crisis_news` (breaking point → numbers → ground zero → causes → cost → next), `educational` (promise → steps → recap), `listicle` (countdown: item → key fact → why it matters). |
| `sentence_rhythm` | Match it exactly — e.g. crime = "measured, long pauses, em-dash breaks"; modern = "short, punchy sentences". |
| `hook_form` | Shape the hook this way — e.g. crime = "question or cold-open statement"; minimalist = "direct promise of what the viewer will learn"; **ledger = "specific-dollar-figure claim or personal stakes statement"** (per VidIQ audit: figures land in the first 10s, always concrete). |
| `tone_words` | These go on the script's `Tone:` line (orchestrator appends it via `brief_template.py` — keep wording consistent). |

## Output
- `script.md` with sections: HOOK, BODY, CTA
- word count matching target duration (~140 wpm)
- target must be **8–20 minutes**. Draft near the requested target, then run the
  VO-first measurement. If measured total VO is below 8:00 or above 20:00,
  rewrite the script before directing scenes. Never pad scene durations to hide a
  short script; measured narration itself must pass.
- **`global_style`** at the top of script.md and into timeline.json (canonical id only: `crime | history | ledger | modern | minimalist | standard`)
- Ends with `Style:` / `Tone:` lines (VidRush prompt format)

## Rules
- **Prompt = WHAT, theme = HOW (VidRush).** You control content, structure, and words only. **Never** write editing instructions — no transitions, animations, text overlays, fonts, colors, zooms. The style JSON owns all of that. (Output is linted by `lint_skill_output.py`; banned words = bug.)
- **Ledger packaging (when `global_style: ledger`).** Titles lead with a concrete figure ("$75 Million Broke America", "60% of Everything America Sold Was Picked By Hand"). Hooks name the number first, context second — never bury a dollar figure past sentence three. Sentences stay declarative; "controlled outrage" lives in specific counts, not adjectives. Banned: "it's important to note", "what's fascinating is", "let's dive in". The audit wins on accountability, not nostalgia.
- No AI-slop openers ("In today's video...")
- Hook in first 8 seconds
- Pattern interrupt every 20–30s
- Hook lines pass through **verbatim** — never paraphrased downstream
- Skills must not override the selected global style with a fixed house style
- Production gate: `sum(duration_sec)` from `synthesize_script_plan` must be
  `480 <= total_vo_sec <= 1200`. Expand with sourced facts, explanation, and
  consequences when short; cut repetition and secondary detail when long.
