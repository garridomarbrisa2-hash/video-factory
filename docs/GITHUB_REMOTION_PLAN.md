# GitHub Remotion, Local FFmpeg Plan

**Status:** clip-only workflow implemented

Stage portable payload before dispatch:

```powershell
python -m pipeline.render.cloud output/<name>_silent_manifest.json
git add remotion/cloud-payload
git commit -m "Stage Remotion render payload"
git push
```

Dispatch `remotion/cloud-payload/manifest.json`. Payload contains sanitized
manifest and referenced Remotion assets only. Local footage paths, output path,
VO, caches, and secrets stay local. After artifact download and validation, run:

```powershell
node remotion/src/render.js --batch output/<name>_silent_manifest.json --assemble-only output/remotion-clips
```

## Boundary

### Local

- Brief parsing and style selection
- Script skills chain
- VO synthesis and timing
- ModelScope image generation
- Pexels/Pixabay search and downloads
- Timeline resolution and manifest creation
- FFmpeg footage trim/grade
- Final xfade, audio mix, loudnorm, and NVENC encode

### GitHub Actions

- Checkout repository
- Install Node dependencies in `remotion/`
- Install Remotion Chrome
- Render Remotion scene clips from uploaded or checked-in manifest
- Upload clips and render logs as workflow artifacts

Actions must not contain production API keys and must not perform final FFmpeg
assembly. Local FFmpeg remains required for footage routing, alpha-overlay
composition, audio, and NVENC.

## Workflow Interface

`.github/workflows/remotion-render.yml`

Manual `workflow_dispatch` inputs:

- `manifest`: repository-relative manifest path
- `output_dir`: artifact directory
- `concurrency`: browser render parallelism
- `scene_pause`: seconds between scene renders

Workflow steps:

1. Checkout `master`.
2. Setup Node 20 with npm cache rooted at `remotion/package-lock.json`.
3. Run `npm ci` in `remotion/`.
4. Run `npx remotion browser ensure`.
5. Run `node src/render.js --batch ...`.
6. Upload rendered clips, manifest, and logs with `actions/upload-artifact`.

Use Ubuntu paths. Do not depend on Windows `C:/ProgramData/chocolatey/bin`.
Renderer must use PATH lookup for FFmpeg or skip FFmpeg when rendering pure
Remotion clips.

## Local Bridge

Add `pipeline/render/github.py` only if direct automation is needed:

1. Validate manifest contains repository-visible assets or uploadable assets.
2. Trigger `workflow_dispatch` with GitHub CLI.
3. Poll run status with `gh run watch` or the GitHub API.
4. Download artifact into local `output/_clips_tmp/`.
5. Validate clip codec, alpha format where applicable, and duration.
6. Pass validated clips to existing local FFmpeg assembly.

First version may use manual `gh workflow run` and `gh run download`; avoid
adding bridge code until repeated manual runs prove it is needed.

## Repository Migration

1. Inspect target repository and confirm authenticated owner.
2. Add workflow and required Remotion portability fixes locally.
3. Run `npm ci`, bundle check, and one short render.
4. Review staged diff; exclude caches, `node_modules`, outputs, API keys, and
   unrelated worktree changes.
5. Require explicit `WIPE AND PUSH` confirmation.
6. Delete and recreate `srb991/video-factory`, or replace its default branch if
   deletion is unavailable.
7. Push clean project tree.
8. Trigger workflow and verify uploaded artifact.

Repository deletion is irreversible and must not happen during plan-only work.

## Validation

- YAML parses.
- `npm ci` succeeds on Ubuntu.
- `npx remotion browser ensure` succeeds.
- Short render produces non-empty MP4 clips.
- Artifact download preserves filenames.
- Local FFmpeg assembly still owns final output.
