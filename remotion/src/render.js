/**
 * Batch Remotion renderer — render each scene as short clip, then xfade join in FFmpeg.
 *
 * Why: CPU bursty (short clips), not sustained 60s Chrome run. GPU NVENC encodes each clip + final.
 *
 * Usage:
 *   node render.js --batch <manifest.json>
 *   node render.js <composition_id> <output_path> [props_file.json]
 */

const {bundle} = require('@remotion/bundler');
const {renderMedia, selectComposition, openBrowser} = require('@remotion/renderer');
const path = require('path');
const fs = require('fs');
const {spawnSync} = require('child_process');

const FFMPEG_BINARIES = process.env.FFMPEG_BINARIES || 'C:/ProgramData/chocolatey/bin';

function getFFmpeg() {
  const direct = 'ffmpeg';
  if (FFMPEG_BINARIES && fs.existsSync(path.join(FFMPEG_BINARIES, 'ffmpeg.exe'))) {
    return path.join(FFMPEG_BINARIES, 'ffmpeg.exe');
  }
  return direct;
}

let browserRef = null;
let bundleRef = null;

async function ensureBundle() {
  if (bundleRef) return bundleRef;
  console.log('Bundling Remotion project...');
  bundleRef = await bundle({
    entryPoint: path.resolve(__dirname, 'index.ts'),
    onProgress: (p) => { if (p === 100) console.log('Bundle ready'); },
  });
  return bundleRef;
}

async function ensureBrowser() {
  if (browserRef) return browserRef;
  browserRef = await openBrowser('chrome', {
    headless: true,
    args: ['--enable-gpu', '--ignore-gpu-blocklist'],
  });
  return browserRef;
}

async function cleanup() {
  if (browserRef) {
    try { await browserRef.close({}); } catch (e) {}
    browserRef = null;
  }
}
const COMPOSITION_FOR_TYPE = {
  intro: 'intro',
  content: 'content',
  stat: 'stat',
  quote: 'quote',
  list: 'list-reveal',
  comparison: 'comparison',
  person: 'person-card',
  document: 'document',
  map: 'map',
  'crime-board': 'crime-board',
  outro: 'outro',
};

// Style system (JS mirror of pipeline/intelligence/select_style.py).
const LEGACY_ALIASES = {
  documentary: 'history',
  storytelling: 'standard',
  listicle: 'standard',
  explainer: 'minimalist',
  commentary: 'modern',
};
const STYLES_DIR = path.resolve(__dirname, '../../pipeline/intelligence/styles');

function loadGlobalStyle(id) {
  const key = (id || 'standard').trim().toLowerCase();
  const canonical = LEGACY_ALIASES[key] || key;
  const file = path.join(STYLES_DIR, `${canonical}.json`);
  if (!fs.existsSync(file)) {
    console.log(`[style] unknown "${id}" — falling back to standard`);
    return JSON.parse(fs.readFileSync(path.join(STYLES_DIR, 'standard.json'), 'utf-8'));
  }
  const style = JSON.parse(fs.readFileSync(file, 'utf-8'));
  style.style_id = canonical;
  return style;
}

function runFFmpeg(args) {
  const bin = getFFmpeg();
  console.log(`  ffmpeg ${args.filter(a => !a.startsWith('-i') && a !== '-y' && !a.startsWith('-filter_complex')).slice(0, 4).join(' ')}`);
  const res = spawnSync(bin, args, {encoding: 'utf-8', stdio: ['ignore', 'ignore', 'inherit']});
  if (res.status !== 0) {
    throw new Error(`FFmpeg exit ${res.status}`);
  }
}

async function renderSceneClip(scene, idx, serveUrl, outDir, accent, text, globalStyle, onComposition) {
  const compositionId = COMPOSITION_FOR_TYPE[scene.type];
  if (!compositionId) throw new Error(`Unknown scene type: ${scene.type}`);

  const props = {
    ...scene.props,
    accent_color: scene.props.accent_color || accent,
    text_color: scene.props.text_color || text,
    global_style: scene.props.global_style || globalStyle.style_id,
    // Per-scene seed so grain/camera-noise differs scene to scene (deterministic).
    scene_seed: scene.props.scene_seed ?? idx,
    // Editorial choices flow through from the timeline (director's judgment).
    ...(scene.layout ? {layout: scene.layout} : {}),
    ...(scene.placement ? {placement: scene.placement} : {}),
    // Camera intent grammar (Phase 8, P3): director's energy/explicit move.
    ...(scene.energy || scene.props.energy ? {energy: scene.energy || scene.props.energy} : {}),
    ...(scene.photo_move || scene.props.photo_move ? {photo_move: scene.photo_move || scene.props.photo_move} : {}),
    ...(scene.still_motion || scene.props.still_motion ? {still_motion: scene.still_motion || scene.props.still_motion} : {}),
    ...(scene.shake != null ? {shake: scene.shake} : {}),
    ...(scene.shake_at != null ? {shake_at: scene.shake_at} : {}),
    ...(scene.shake_dir ? {shake_dir: scene.shake_dir} : {}),
    ...(scene.signature || scene.props.signature ? {signature: scene.signature || scene.props.signature} : {}),
    ...(scene.grade_override || scene.props.grade_override ? {grade_override: scene.grade_override || scene.props.grade_override} : {}),
    // Handheld drift (Phase 8): OPT-IN — off unless the director sets it.
    ...(scene.drift != null || scene.props.drift != null ? {drift: scene.drift ?? scene.props.drift} : {}),
    // Beat-choreography contract (Phase 8, P0): director may re-time any named
    // beat (seconds) and scale scene rhythm; scenes fall back to style defaults.
    ...(scene.beats || scene.props.beats ? {beats: scene.beats || scene.props.beats} : {}),
    ...(scene.tempo != null || scene.props.tempo != null ? {tempo: scene.tempo ?? scene.props.tempo} : {}),
    // VO→visual sync (Phase 8, P1): per-word onset times (scene-relative sec).
    ...(scene.word_times || scene.props.word_times ? {word_times: scene.word_times || scene.props.word_times} : {}),
  };
  const duration = scene.duration;
  const outPath = path.join(outDir, `clip_${String(idx).padStart(2, '0')}_${scene.type}.mp4`);

  console.log(`[${idx + 1}] ${scene.type} (${duration}s) → ${path.basename(outPath)}`);
  if (process.env.RENDER_DEBUG) {
    console.log(`  [debug] props.energy=${props.energy} props.photo_move=${props.photo_move} props.ken_burns=${props.ken_burns}`);
  }

  const composition = await selectComposition({
    serveUrl,
    id: compositionId,
    inputProps: props,
  });

  // Duration is content-driven (script / footage / VO), never a hardcoded comp
  // default. The timeline's scene.duration is authoritative — override the comp.
  const durationInFrames = Math.max(1, Math.round(duration * composition.fps));
  if (onComposition) onComposition(durationInFrames);
  const finalComposition = {...composition, durationInFrames};

  await renderMedia({
    composition: finalComposition,
    serveUrl,
    outputLocation: outPath,
    inputProps: props,
    codec: 'h264',
    // Match renderSingle: NVENC rejects CRF and produced black batch clips.
    crf: 18,
    pixelFormat: 'yuv420p',
    muted: true,
    enforceAudioTrack: false,
    chromiumOptions: {gl: 'angle'},
    puppeteerInstance: await ensureBrowser(),
    onProgress: (progress) => {
      const pct = Math.round(progress * 100);
      if (pct % 25 === 0) process.stdout.write(`  ${pct}%\r`);
    },
  });

  process.stdout.write('  100%   \n');
  return outPath;
}

// --- Hybrid pipeline helpers (Phase 7b) -------------------------------------

const PUBLIC_DIR = path.resolve(__dirname, '../public');
const PIPELINE_ROOT = path.resolve(__dirname, '../..');

/** Locate the baked near-plane for a still (parallax), by naming convention. */
function nearPlaneFor(bgImage) {
  if (!bgImage || /\.(mp4|webm|mov)$/i.test(bgImage)) return null;
  const near = bgImage.replace(/\.[^.]+$/, '_near.png');
  return fs.existsSync(path.join(PUBLIC_DIR, near))
    ? path.join(PUBLIC_DIR, near)
    : null;
}

/** Build the animated photo base via FFmpeg (GPU) — spawned Python module. */
function buildPhotoBase(bgImage, out, duration, move, parallax) {
  const imgPath = path.isAbsolute(bgImage) ? bgImage : path.join(PUBLIC_DIR, bgImage);
  // out must be absolute — the spawned python/ffmpeg run with cwd=PIPELINE_ROOT,
  // so a relative path resolves against the wrong directory.
  const outAbs = path.resolve(out);
  const near = nearPlaneFor(bgImage);
  const args = [
    '-m', 'pipeline.video.photo_base',
    imgPath, outAbs, String(duration),
    move || 'in',
    near || 'none',
    parallax === false ? '0' : '1',
  ];
  const res = spawnSync('python', args, {cwd: PIPELINE_ROOT, encoding: 'utf-8'});
  if (res.status !== 0) {
    const detail = (res.stderr || res.stdout || res.error?.message || 'unknown').toString();
    throw new Error(`photo_base failed for ${bgImage} (exit ${res.status}):\n${detail.slice(-1500)}`);
  }
  return outAbs;
}

/** Composite a transparent Remotion overlay over the photo base via FFmpeg. */
function compositeOverlay(baseMp4, overlayMov, out) {
  const args = [
    '-y',
    '-i', baseMp4,
    '-i', overlayMov,
    '-filter_complex', '[0:v][1:v]overlay=0:0:shortest=1[v]',
    '-map', '[v]',
    '-c:v', 'h264_nvenc', '-preset', 'p6', '-tune', 'hq',
    '-b:v', '12M', '-pix_fmt', 'yuv420p', '-r', '30',
    out,
  ];
  runFFmpeg(args);
  return out;
}

/**
 * Hybrid scene render — the fast path.
 *   1. FFmpeg builds the photo base (GPU): eased ken-burns + parallax + grade.
 *   2. Remotion renders ONLY the text/animation as a transparent ProRes 4444 clip.
 *   3. FFmpeg composites overlay over base.
 * Remotion never rasterizes the 1080p photo — that's what makes it fast.
 */
async function renderSceneHybrid(scene, idx, serveUrl, outDir, accent, text, globalStyle) {
  const compositionId = COMPOSITION_FOR_TYPE[scene.type];
  if (!compositionId) throw new Error(`Unknown scene type: ${scene.type}`);
  const duration = scene.duration;
  const pad = String(idx).padStart(2, '0');

  const basePath = path.resolve(outDir, `base_${pad}_${scene.type}.mp4`);
  const overlayPath = path.resolve(outDir, `overlay_${pad}_${scene.type}.mov`);
  const outPath = path.resolve(outDir, `clip_${pad}_${scene.type}.mp4`);

  // 1. Photo base (FFmpeg/GPU) — director's photo_move + parallax.
  console.log(`[${idx + 1}] ${scene.type} (${duration}s) base → FFmpeg`);
  buildPhotoBase(
    scene.props.bg_image,
    basePath,
    duration,
    scene.photo_move || scene.props.photo_move || 'in',
    scene.parallax ?? scene.props.parallax ?? true,
  );

  // 2. Transparent text/animation overlay (Remotion, ProRes 4444 alpha).
  const props = {
    ...scene.props,
    accent_color: scene.props.accent_color || accent,
    text_color: scene.props.text_color || text,
    global_style: scene.props.global_style || globalStyle.style_id,
    scene_seed: scene.props.scene_seed ?? idx,
    // Transparent overlay pass — render ONLY the text/animation layer; FFmpeg
    // composites it over the GPU photo base. Scenes forward this to SceneShell.
    transparent: true,
    bg_image: null,
    bg_video: null,
    ...(scene.layout ? {layout: scene.layout} : {}),
    ...(scene.placement ? {placement: scene.placement} : {}),
    ...(scene.shake != null ? {shake: scene.shake} : {}),
    ...(scene.shake_at != null ? {shake_at: scene.shake_at} : {}),
    ...(scene.shake_dir ? {shake_dir: scene.shake_dir} : {}),
    ...(scene.signature || scene.props.signature ? {signature: scene.signature || scene.props.signature} : {}),
    ...(scene.grade_override || scene.props.grade_override ? {grade_override: scene.grade_override || scene.props.grade_override} : {}),
    // Beat-choreography contract (Phase 8, P0) — hybrid overlay pass too.
    ...(scene.beats || scene.props.beats ? {beats: scene.beats || scene.props.beats} : {}),
    ...(scene.tempo != null || scene.props.tempo != null ? {tempo: scene.tempo ?? scene.props.tempo} : {}),
    // VO→visual sync (Phase 8, P1).
    ...(scene.word_times || scene.props.word_times ? {word_times: scene.word_times || scene.props.word_times} : {}),
  };
  const composition = await selectComposition({serveUrl, id: compositionId, inputProps: props});
  const durationInFrames = Math.max(1, Math.round(duration * composition.fps));
  const finalComposition = {...composition, durationInFrames};
  await renderMedia({
    composition: finalComposition,
    serveUrl,
    outputLocation: overlayPath,
    inputProps: props,
    codec: 'prores',
    proResProfile: '4444',
    imageFormat: 'png',
    pixelFormat: 'yuva444p10le',
    chromiumOptions: {gl: 'angle'},
    puppeteerInstance: await ensureBrowser(),
  });

  // 3. Composite overlay over base (FFmpeg/GPU).
  compositeOverlay(basePath, overlayPath, outPath);
  return outPath;
}

/**
 * Render ONLY the authored foreground text/graphics layer of a scene as a
  * transparent ProRes 4444 clip (Option A). Used to lay on-style typography over an
 * FFmpeg-edited footage clip. Mirrors the overlay pass in renderSceneHybrid but
 * takes an explicit output path and does not build a photo base.
 */
async function renderOverlayClip(scene, idx, serveUrl, overlayPath, accent, text, globalStyle, onComposition) {
  const compositionId = COMPOSITION_FOR_TYPE[scene.type];
  if (!compositionId) throw new Error(`Unknown scene type: ${scene.type}`);
  const props = {
    ...scene.props,
    accent_color: scene.props.accent_color || accent,
    text_color: scene.props.text_color || text,
    global_style: scene.props.global_style || globalStyle.style_id,
    scene_seed: scene.props.scene_seed ?? idx,
    // Transparent overlay pass — render ONLY the foreground text/animation layer.
    transparent: true,
    bg_image: null,
    bg_video: null,
    ...(scene.layout ? {layout: scene.layout} : {}),
    ...(scene.placement ? {placement: scene.placement} : {}),
    ...(scene.shake != null ? {shake: scene.shake} : {}),
    ...(scene.shake_at != null ? {shake_at: scene.shake_at} : {}),
    ...(scene.shake_dir ? {shake_dir: scene.shake_dir} : {}),
    ...(scene.signature || scene.props.signature ? {signature: scene.signature || scene.props.signature} : {}),
    ...(scene.grade_override || scene.props.grade_override ? {grade_override: scene.grade_override || scene.props.grade_override} : {}),
    ...(scene.beats || scene.props.beats ? {beats: scene.beats || scene.props.beats} : {}),
    ...(scene.tempo != null || scene.props.tempo != null ? {tempo: scene.tempo ?? scene.props.tempo} : {}),
    ...(scene.word_times || scene.props.word_times ? {word_times: scene.word_times || scene.props.word_times} : {}),
  };
  const composition = await selectComposition({serveUrl, id: compositionId, inputProps: props});
  const durationInFrames = Math.max(1, Math.round(scene.duration * composition.fps));
  if (onComposition) onComposition(durationInFrames);
  const finalComposition = {...composition, durationInFrames};
  await renderMedia({
    composition: finalComposition,
    serveUrl,
    outputLocation: overlayPath,
    inputProps: props,
    codec: 'prores',
    proResProfile: '4444',
    imageFormat: 'png',
    pixelFormat: 'yuva444p10le',
    chromiumOptions: {gl: 'angle'},
    puppeteerInstance: await ensureBrowser(),
  });
  return overlayPath;
}

/**
 * Resolve a per-cut director intent to a concrete xfade type + duration.
 * The director owns WHERE (act breaks); the style owns HOW (values/frames).
 *   hard     → null (no xfade — an instant cut; the join is offset-aligned)
 *   style    → the style's default xfade at the style duration
 *   dissolve → soften into the next beat (style duration)
 *   dip      → fadeblack era change regardless of style (style duration)
 *   whip     → act-break energy snap: hblur (closest xfade to a motion-blur
 *              whip) at a short fadefast-like duration (~8f), not the slow default
 * `transitionSec` is the style's default seconds; `styleXfade` its default type.
 */
function resolveCutTransition(intent, styleXfade, transitionSec) {
  const WHIP_SEC = 8 / 30; // ~0.27s — a whip is a snap, not the slow default
  switch ((intent || 'style').toLowerCase()) {
    case 'hard':
      return null; // instant cut — no xfade segment
    case 'dissolve':
      return {type: 'dissolve', sec: transitionSec};
    case 'dip':
      return {type: 'fadeblack', sec: transitionSec};
    case 'whip':
      return {type: 'hblur', sec: WHIP_SEC};
    case 'style':
    default:
      return {type: styleXfade, sec: transitionSec};
  }
}

async function concatWithXfade(clips, outputPath, transitionSec = 0.6, xfadeType = 'fade', cutIntents = null) {
  // Two-pass: first probe durations, then build filter_complex with xfade chain.
  const {execSync} = require('child_process');
  const durations = clips.map(c => {
    const out = execSync(`ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "${c}"`, {encoding: 'utf-8'});
    return parseFloat(out.trim());
  });

  if (clips.length === 1) {
    fs.copyFileSync(clips[0], outputPath);
    return;
  }

  // Per-cut intents (Phase 8, P2). cutIntents[i] is the director's transition_out
  // for the cut from clip i → clip i+1. Absent/null → the style default.
  const intents = Array.isArray(cutIntents) && cutIntents.length
    ? cutIntents
    : new Array(clips.length - 1).fill('style');
  if (intents.every((intent) => ['hard', 'cut', 'hard_cut'].includes((intent || '').toLowerCase()))) {
    const concatFile = path.join(path.dirname(outputPath), `_concat_${process.pid}.txt`);
    fs.writeFileSync(
      concatFile,
      clips.map((clip) => `file '${path.resolve(clip).replace(/'/g, "'\\''")}'`).join('\n') + '\n',
    );
    try {
      runFFmpeg(['-y', '-f', 'concat', '-safe', '0', '-i', concatFile, '-c', 'copy', '-movflags', '+faststart', outputPath]);
      console.log('All hard cuts → concat stream copy (no decode or encode)');
      return;
    } catch (error) {
      console.log(`Hard-cut stream copy unavailable → filter/NVENC fallback (${error.message})`);
    } finally {
      fs.rmSync(concatFile, {force: true});
    }
  }
  const nonDefault = intents.filter(t => t && t !== 'style');
  console.log(
    `Concatenating ${clips.length} clips | style xfade "${xfadeType}" ${transitionSec.toFixed(2)}s` +
    (nonDefault.length ? ` | per-cut intents: ${intents.join(',')}` : ' (uniform style cuts)')
  );
  if (process.env.RENDER_DEBUG) {
    console.log('  [debug] probed durations:', durations.map(d => d.toFixed(3)).join(', '));
    console.log('  [debug] clips:', clips.map(c => path.basename(c)).join(', '));
  }

  // Normalize every input to a shared CFR timebase BEFORE the xfade chain.
  // xfade requires identical fps/timebase on both inputs; mixing transition
  // durations (a 0.27s whip next to a 0.4s fadeblack) makes xfade infer a wrong
  // rate and time-compress the output (~2× speed). fps=30 + settb pins all inputs.
  let filter = '';
  clips.forEach((c, i) => {
    filter += `[${i}:v]fps=30,settb=AVTB,format=yuv420p[in${i}];`;
  });

  // Build the per-cut chain. Hard cuts are TRUE concat (zero overlap — the
  // program clock counts the full scene duration); animated cuts use xfade and
  // overlap `sec`. Offset bookkeeping: `cumulative` is the end time (sec) of the
  // running output. Each xfade overlaps `sec`, so offset = cumulative - sec and
  // the output ends at offset + duration[next]. This arithmetic is mirrored by
  // expected_program_sec()/stage_retime_to_vo() in pipeline/orchestrator.py —
  // keep them in sync so narration lands on the assembled picture.
  let prevLabel = '[in0]';
  let cumulative = durations[0];
  let lastLabel = 'in0';
  let nodeIdx = 0;
  let segIdx = 0;

  for (let i = 1; i < clips.length; i++) {
    const intent = intents[i - 1];
    const cut = resolveCutTransition(intent, xfadeType, transitionSec);
    if (cut === null) {
      // True hard cut: concat, no overlap. Concat demuxer-equivalent in the
      // filter graph — join prev + next at exact timestamps (setpts resets each
      // input to the running timeline so the join is sample-accurate).
      const outLabel = i === clips.length - 1 ? 'vout' : `cx${segIdx}`;
      filter += `${prevLabel}[in${i}]concat=n=2:v=1:a=0[${outLabel}];`;
      prevLabel = `[${outLabel}]`;
      cumulative = cumulative + durations[i];
      lastLabel = outLabel;
      segIdx++;
      continue;
    }
    const type = cut.type;
    const sec = cut.sec;
    const offset = cumulative - sec;
    const outLabel = i === clips.length - 1 ? 'vout' : `vx${nodeIdx}`;
    filter += `${prevLabel}[in${i}]xfade=transition=${type}:duration=${sec.toFixed(4)}:offset=${offset.toFixed(3)}[${outLabel}];`;
    prevLabel = `[${outLabel}]`;
    cumulative = offset + durations[i];
    lastLabel = outLabel;
    nodeIdx++;
  }

  // Remove trailing semicolon
  filter = filter.slice(0, -1);

  // Encode on GPU (NVENC). Decode stays on CPU because xfade is a CPU filter —
  // forcing CUDA decode fails with "Function not implemented" when the filter
  // graph needs frames in system memory. CPU decode of short 1080p clips is cheap.
  const args = ['-y'];
  clips.forEach(c => args.push('-i', c));
  args.push(
    '-filter_complex', filter,
    '-map', `[${lastLabel}]`,
    '-c:v', 'h264_nvenc',
    '-preset', 'p6',
    '-tune', 'hq',
    '-b:v', '12M',
    '-maxrate', '16M',
    '-bufsize', '24M',
    '-pix_fmt', 'yuv420p',
    '-r', '30',
    '-movflags', '+faststart',
    outputPath,
  );

  runFFmpeg(args);
}

async function renderBatch(manifestPath, opts = {}) {
  const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf-8'));
  const globalStyle = loadGlobalStyle(manifest.global_style || manifest.edit_style);
  // Style palette is the default; manifest-level colors still override.
  const accent = manifest.accent_color || globalStyle.visual.palette.accent;
  const text = manifest.text_color || globalStyle.visual.palette.text;
  const outputPath = manifest.output;
  // Transition: style JSON owns type + frames (30fps). Manifest may override seconds.
  const styleTransition = globalStyle.motion.transition;
  const transitionSec = manifest.transition_sec ?? styleTransition.frames / 30;
  const xfadeType = manifest.xfade || styleTransition.xfade;
  // Cool-down pause between scene renders (CPU thermal relief). Override via
  // manifest.scene_pause_sec or --scene-pause CLI flag; default 2s.
  const scenePauseSec = Number(opts.scenePauseSec ?? manifest.scene_pause_sec ?? 2);

  const totalDuration = manifest.scenes.reduce((s, sc) => s + sc.duration, 0);
  console.log(`Batch render: ${manifest.scenes.length} scenes | ${totalDuration}s | style=${globalStyle.style_id} | xfade=${xfadeType} ${transitionSec.toFixed(2)}s | pause=${scenePauseSec}s/scene`);

  const serveUrl = await ensureBundle();
  const outDir = path.dirname(outputPath);
  if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, {recursive: true});
  const tmpDir = path.join(outDir, '_clips_tmp');
  if (fs.existsSync(tmpDir)) fs.rmSync(tmpDir, {recursive: true});
  fs.mkdirSync(tmpDir, {recursive: true});

  // Full-Remotion is the default path (Phase 7 revert: hybrid "degraded to poor
  // editing"). The hybrid FFmpeg-base + Remotion-overlay pipeline is kept behind
  // an explicit opt-in: set "hybrid": true in the manifest to enable it.
  const hybrid = manifest.hybrid === true;
  const renderOne = hybrid ? renderSceneHybrid : renderSceneClip;

  // Path A footage-type router: scenes carry render_route from the orchestrator.
  //   'remotion' → full theme render (image / plate scenes).
  //   'ffmpeg'   → footage clip already edited by FFmpeg (trim/grade); splice it
  //                in directly. When it also carries authored text, render a
  //                transparent Remotion overlay and composite it over the footage
  //                (Option A) — FFmpeg never draws the text itself.
  const hasFootage = manifest.scenes.some(sc => sc.render_route === 'ffmpeg');
  const concurrency = Math.max(1, Number(opts.concurrency ?? manifest.concurrency ?? (hybrid ? 4 : 3)));
  console.log(
    `Rendering ${manifest.scenes.length} scenes | mode=${hybrid ? 'hybrid' : hasFootage ? 'routed(remotion+ffmpeg)' : 'remotion-only'} | concurrency=${concurrency}...`
  );

  const clips = new Array(manifest.scenes.length);
  let nextIndex = 0;
  let rendered = 0;
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  async function worker() {
    while (nextIndex < manifest.scenes.length) {
      const i = nextIndex++;
      const sc = manifest.scenes[i];
      if (!hybrid && sc.render_route === 'ffmpeg' && sc.footage_path) {
        // Footage scene: use the FFmpeg-edited clip. Composite a Remotion alpha
        // overlay only when the scene carries authored foreground text/graphics.
        if (sc.needs_overlay) {
          const pad = String(i).padStart(2, '0');
          const overlayPath = path.resolve(tmpDir, `overlay_${pad}_${sc.type}.mov`);
          const outPath = path.resolve(tmpDir, `clip_${pad}_${sc.type}.mp4`);
          console.log(`[${i + 1}] ${sc.type} (footage+overlay) → FFmpeg base + Remotion text`);
          await renderOverlayClip(sc, i, serveUrl, overlayPath, accent, text, globalStyle);
          compositeOverlay(sc.footage_path, overlayPath, outPath);
          clips[i] = outPath;
        } else {
          console.log(`[${i + 1}] ${sc.type} (footage) → FFmpeg clip`);
          clips[i] = sc.footage_path;
        }
      } else {
        clips[i] = await renderOne(sc, i, serveUrl, tmpDir, accent, text, globalStyle);
      }
      rendered++;
      // Cool-down pause between scene renders — lets CPU/GPU thermals recover
      // before the next short Chrome burst. Skipped after the last scene.
      if (scenePauseSec > 0 && rendered < manifest.scenes.length) {
        process.stdout.write(`  …pause ${scenePauseSec}s (thermal cooldown)\n`);
        await sleep(scenePauseSec * 1000);
      }
    }
  }
  await Promise.all(Array.from({length: Math.min(concurrency, manifest.scenes.length)}, worker));

  // Per-cut transition intents (Phase 8, P2): scene i's transition_out governs the
  // cut from scene i → scene i+1. The last scene has no outgoing cut.
  const cutIntents = manifest.scenes.map(sc => sc.transition_out || (sc.props && sc.props.transition_out) || null);
  await concatWithXfade(clips, outputPath, transitionSec, xfadeType, cutIntents);

  // Cleanup tmp (kept when RENDER_DEBUG is set, for inspecting scene clips)
  if (!process.env.RENDER_DEBUG) {
    fs.rmSync(tmpDir, {recursive: true, force: true});
  }

  console.log(`\nFinal → ${outputPath}`);
}

async function renderClipsOnly(manifestPath, clipsDir, opts = {}) {
  const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf-8'));
  const globalStyle = loadGlobalStyle(manifest.global_style || manifest.edit_style);
  const accent = manifest.accent_color || globalStyle.visual.palette.accent;
  const text = manifest.text_color || globalStyle.visual.palette.text;
  const scenePauseSec = Number(opts.scenePauseSec ?? manifest.scene_pause_sec ?? 2);
  const concurrency = Math.max(1, Number(opts.concurrency ?? manifest.concurrency ?? 3));
  const outDir = path.resolve(clipsDir);
  fs.mkdirSync(outDir, {recursive: true});

  const jobs = manifest.scenes.flatMap((scene, index) => {
    if (scene.render_route !== 'ffmpeg') return [{scene, index, kind: 'scene'}];
    return scene.needs_overlay ? [{scene, index, kind: 'overlay'}] : [];
  });
  console.log(`Clips-only render: ${jobs.length}/${manifest.scenes.length} scenes | concurrency=${concurrency}`);

  const serveUrl = jobs.length ? await ensureBundle() : null;
  const metadata = new Array(jobs.length);
  let nextJob = 0;
  let rendered = 0;
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  async function worker() {
    while (nextJob < jobs.length) {
      const jobIndex = nextJob++;
      const {scene, index, kind} = jobs[jobIndex];
      const pad = String(index).padStart(2, '0');
      const filename = kind === 'overlay'
        ? `overlay_${pad}_${scene.type}.mov`
        : `clip_${pad}_${scene.type}.mp4`;
      const outputPath = path.join(outDir, filename);
      let expectedFrames;
      const recordFrames = (frames) => { expectedFrames = frames; };
      if (kind === 'overlay') {
        await renderOverlayClip(scene, index, serveUrl, outputPath, accent, text, globalStyle, recordFrames);
      } else {
        await renderSceneClip(scene, index, serveUrl, outDir, accent, text, globalStyle, recordFrames);
      }
      metadata[jobIndex] = {
        scene_index: index,
        scene_id: scene.id ?? scene.scene_id ?? index,
        kind,
        filename,
        duration: scene.duration,
        expected_frames: expectedFrames,
      };
      rendered++;
      if (scenePauseSec > 0 && rendered < jobs.length) await sleep(scenePauseSec * 1000);
    }
  }
  await Promise.all(Array.from({length: Math.min(concurrency, jobs.length)}, worker));
  fs.writeFileSync(path.join(outDir, 'clips.json'), `${JSON.stringify(metadata, null, 2)}\n`);
  console.log(`Clips metadata → ${path.join(outDir, 'clips.json')}`);
}

async function assembleDownloadedClips(manifestPath, clipsDir) {
  const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf-8'));
  const globalStyle = loadGlobalStyle(manifest.global_style || manifest.edit_style);
  const styleTransition = globalStyle.motion.transition;
  const transitionSec = manifest.transition_sec ?? styleTransition.frames / 30;
  const xfadeType = manifest.xfade || styleTransition.xfade;
  const sourceDir = path.resolve(clipsDir);
  const outputPath = path.resolve(manifest.output);
  const workDir = path.join(path.dirname(outputPath), '_cloud_assembly_tmp');
  fs.rmSync(workDir, {recursive: true, force: true});
  fs.mkdirSync(workDir, {recursive: true});
  const clips = [];

  for (let i = 0; i < manifest.scenes.length; i++) {
    const scene = manifest.scenes[i];
    const pad = String(i).padStart(2, '0');
    if (scene.render_route !== 'ffmpeg') {
      const clip = path.join(sourceDir, `clip_${pad}_${scene.type}.mp4`);
      if (!fs.existsSync(clip)) throw new Error(`Downloaded scene clip missing: ${clip}`);
      clips.push(clip);
    } else if (scene.needs_overlay) {
      if (!scene.footage_path || !fs.existsSync(scene.footage_path)) {
        throw new Error(`Local footage missing for scene ${i}: ${scene.footage_path}`);
      }
      const overlay = path.join(sourceDir, `overlay_${pad}_${scene.type}.mov`);
      if (!fs.existsSync(overlay)) throw new Error(`Downloaded overlay missing: ${overlay}`);
      const composited = path.join(workDir, `clip_${pad}_${scene.type}.mp4`);
      compositeOverlay(scene.footage_path, overlay, composited);
      clips.push(composited);
    } else {
      if (!scene.footage_path || !fs.existsSync(scene.footage_path)) {
        throw new Error(`Local footage missing for scene ${i}: ${scene.footage_path}`);
      }
      clips.push(scene.footage_path);
    }
  }
  const cutIntents = manifest.scenes.slice(0, -1).map(
    (scene) => scene.transition_out || (scene.props && scene.props.transition_out) || null
  );
  await concatWithXfade(clips, outputPath, transitionSec, xfadeType, cutIntents);
  if (!process.env.RENDER_DEBUG) fs.rmSync(workDir, {recursive: true, force: true});
  console.log(`\nLocal assembly → ${outputPath}`);
}

async function renderSingle(compositionId, outputPath, propsFile) {
  let props = {};
  if (propsFile && fs.existsSync(propsFile)) {
    props = JSON.parse(fs.readFileSync(propsFile, 'utf-8'));
  }
  const serveUrl = await ensureBundle();
  const composition = await selectComposition({serveUrl, id: compositionId, inputProps: props});
  await renderMedia({
    composition, serveUrl, outputLocation: outputPath, inputProps: props,
    codec: 'h264', crf: 18, pixelFormat: 'yuv420p',
    muted: true, chromiumOptions: {gl: 'angle'},
    puppeteerInstance: await ensureBrowser(),
  });
  console.log(`Done → ${outputPath}`);
}

async function main() {
  const args = process.argv.slice(2);
  let assembleDir;
  const assembleIdx = args.indexOf('--assemble-only');
  if (assembleIdx !== -1) {
    assembleDir = args[assembleIdx + 1];
    args.splice(assembleIdx, 2);
  }
  const clipsOnlyIdx = args.indexOf('--clips-only');
  const clipsOnly = clipsOnlyIdx !== -1;
  if (clipsOnly) args.splice(clipsOnlyIdx, 1);
  let clipsDir;
  const clipsDirIdx = args.indexOf('--clips-dir');
  if (clipsDirIdx !== -1) {
    clipsDir = args[clipsDirIdx + 1];
    args.splice(clipsDirIdx, 2);
  }
  // Parse --scene-pause <sec> flag (thermal cooldown between scene renders).
  let scenePauseSec;
  const pauseIdx = args.indexOf('--scene-pause');
  if (pauseIdx !== -1) {
    scenePauseSec = parseFloat(args[pauseIdx + 1]);
    args.splice(pauseIdx, 2);
  }
  // Parse --concurrency <n> flag (parallel scene renders).
  let concurrency;
  const concIdx = args.indexOf('--concurrency');
  if (concIdx !== -1) {
    concurrency = parseInt(args[concIdx + 1], 10);
    args.splice(concIdx, 2);
  }
  try {
    if (args[0] === '--batch') {
      if (assembleDir) {
        await assembleDownloadedClips(args[1], assembleDir);
      } else if (clipsOnly) {
        if (!clipsDir) throw new Error('--clips-dir is required with --clips-only');
        await renderClipsOnly(args[1], clipsDir, {scenePauseSec, concurrency});
      } else {
        await renderBatch(args[1], {scenePauseSec, concurrency});
      }
    } else if (args[0] === '--bundle') {
      await ensureBundle();
      console.log('Bundle cached.');
    } else if (args[0]) {
      await renderSingle(args[0], args[1], args[2]);
    } else {
      console.log('Usage:');
      console.log('  node render.js --batch <manifest.json> [--clips-only --clips-dir <dir> | --assemble-only <clips-dir>] [--concurrency 3] [--scene-pause 2]');
      console.log('  node render.js <composition_id> <output_path> [props_file.json]');
    }
  } finally {
    await cleanup();
  }
}

main()
  .then(async () => {
    await cleanup();
    // Force-exit: puppeteer/Chrome and the bundler's watchers can hold the Node
    // event loop open after the work is done, so the process would otherwise
    // hang after printing "Final →". A short delay lets stdout flush first.
    setTimeout(() => process.exit(0), 100);
  })
  .catch((err) => {
    console.error('Render failed:', err.message);
    console.error(err.stack);
    cleanup().then(() => process.exit(1));
  });
