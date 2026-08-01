const {bundle} = require('@remotion/bundler');
const {renderMedia, selectComposition, openBrowser} = require('@remotion/renderer');
const path = require('path');
const fs = require('fs');

(async () => {
  const outDir = 'D:/AI/Video Automation/FFMPEG MCP/output/_clips_tmp';
  fs.mkdirSync(outDir, {recursive: true});
  const outPath = path.join(outDir, 'test_intro.mp4');
  console.log('Output path:', outPath);
  console.log('Exists dir:', fs.existsSync(outDir));

  const serveUrl = await bundle({entryPoint: path.resolve('src/index.ts')});
  console.log('Bundle:', serveUrl);
  
  const b = await openBrowser('chrome', {headless: true, args: ['--enable-gpu']});
  const c = await selectComposition({
    serveUrl,
    id: 'intro',
    inputProps: {
      hook_text: 'Test',
      bg_image: '1.png',
      accent_color: '#ff6b35',
      text_color: '#fff',
      label: 'TEST'
    }
  });
  console.log('Composition frames:', c.durationInFrames, 'fps:', c.fps);

  await renderMedia({
    composition: c,
    serveUrl,
    outputLocation: outPath,
    inputProps: c.props,
    codec: 'h264',
    crf: 18,
    pixelFormat: 'yuv420p',
    muted: true,
    enforceAudioTrack: false,
    chromiumOptions: {gl: 'angle'},
    puppeteerInstance: b,
    onProgress: (p) => process.stdout.write(Math.round(p*100) + '% '),
  });
  console.log('\nFile exists:', fs.existsSync(outPath));
  if (fs.existsSync(outPath)) {
    console.log('Size:', fs.statSync(outPath).size);
  }
  await b.close();
})().catch(e => {
  console.error('FAIL:', e.message);
  console.error(e.stack);
  process.exit(1);
});
