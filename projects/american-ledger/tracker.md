# Tracker — american-ledger

| Ep | style | script | vo | scenes | assets | render |
|---|---|---|---|---|---|---|
| Ep1 | 🔨 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| Ep2 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Ep3 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| Ep4 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| Ep5 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| Ep6 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| Ep7 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |

Legend: ⬜=pending  🔨=in_progress  ✅=done  ⏭️=skipped  🟥=blocked
Stages: style → script → vo → scenes → assets → render

Notes:
- Prior Tracker file corrupted (encoding); rebuilt from scratch.
- 2026-08-01: Per VidIQ audit (`projects/american-ledger-vidiq.md`), full series
  rebuild on `ledger` per-project style. Ep1 materials (script/timeline from
  `history` style era) invalidated.
- 2026-08-01: Ep2 redone under new stage order (style→script→vo→scenes→assets→
  render). Script split into 60 short one-thought paragraphs so every VO beat
  stays under the 14s split cue. VO measured 498.96s (8.32 min), passes gate.
  Timeline: 60 scenes, `asset_mode: auto`, ledger caps verified (max 2
  consecutive hero, ≤2 stat per 5-scene window).
- 2026-08-01: Ep2 first local diagnostic render completed at
  `output/ep2_test.mp4` (493.67s, 731MB). Post-render audit found all-image
  routing and incorrect comparison props; that artifact is not publish-ready.
- 2026-08-01: Post-render audit repaired Ep2: nine real-footage routes, no
  non-artifact holds or repeated camera moves, dual-image comparison generation,
  document plates without generated writing, 48 kHz final audio, and GitHub
  Actions as the default Remotion render mode. Prior local test output remains a
  diagnostic artifact; next publish render uses GitHub Actions.
