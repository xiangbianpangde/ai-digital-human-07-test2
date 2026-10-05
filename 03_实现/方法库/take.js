/* Single-method probe. Inject with agent-browser eval --stdin.
 * No batch/full-film API; no direct write to original assets.
 */
window.methodTake = async function (recipe, endpoint, token) {
  if (window.__methodTake?.running) throw new Error('A take is already running');
  if (!location.href.startsWith('https://open.realsee.com/ke/rXel3aPEWkwD4JQn/qrz3DGWoeBMCwu3h2TOlxEYTR8Q0Xy65/')) throw new Error('Wrong property');
  const f = Object.values(window.__FIVE_DEBUG__?.instances || {}).find(x => x instanceof window.Five);
  if (!f) throw new Error('Five debug instance unavailable; use UI fallback');
  if (!recipe || !Number.isInteger(recipe.start?.pano) || !Array.isArray(recipe.steps) || recipe.steps.length > 8) throw new Error('Invalid single recipe');
  const finite = x => typeof x === 'number' && Number.isFinite(x);
  if (!f.observers[recipe.start.pano] || !finite(recipe.start.yaw) || !finite(recipe.start.fov) || recipe.start.fov < 75 || recipe.start.fov > 85) throw new Error('Invalid starting camera');
  if (!recipe.steps.length || recipe.steps.reduce((n,s)=>n+s.ms,0)>60000) throw new Error('Invalid single-method duration');
  let last = recipe.start.pano, yaw = recipe.start.yaw;
  for (const s of recipe.steps) {
    if (!['pan', 'fov', 'hold', 'move', 'model', 'pano'].includes(s.kind)) throw new Error('Unknown step');
    if (!finite(s.ms) || !(s.ms >= 300 && s.ms <= 15000)) throw new Error('Invalid duration');
    if (s.fov !== undefined && (!finite(s.fov) || s.fov < 75 || s.fov > 85)) throw new Error('FOV outside approved range');
    if (s.yaw !== undefined && !finite(s.yaw)) throw new Error('Invalid yaw');
    if (['move','pano'].includes(s.kind) && (!Number.isInteger(s.pano) || !f.observers[s.pano] || !finite(s.yaw))) throw new Error('Invalid target camera');
    if (s.kind === 'model' && (!finite(s.yaw) || !finite(s.pitch) || !s.offset || !['x','y','z'].every(k=>finite(s.offset[k])) || recipe.model_kind !== 'schematic_not_human_camera')) throw new Error('Explicit schematic model pose required');
    if (s.kind === 'pan' && (!finite(s.yaw) || 1.5*Math.abs(s.yaw-yaw)/(s.ms/1000)>.4)) throw new Error('Pan exceeds stable-camera speed');
    if (s.kind === 'fov' && !finite(s.fov)) throw new Error('FOV target required');
    if (s.transition !== undefined && (s.kind !== 'pano' || s.transition !== 'cut')) throw new Error('Invalid mode transition');
    if (s.yaw !== undefined) yaw = s.yaw;
    if (s.kind === 'move') {
      if (!f.observers[last]?.accessibleNodes.includes(s.pano)) throw new Error(`Non-adjacent ${last}->${s.pano}`);
      last = s.pano;
    }
    if (s.kind === 'pano') last = s.pano;
  }
  const t = window.__methodTake = { running: true, recipe, url: location.href, marks: [], samples: [], error: null };
  const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
  const deadline = (p, ms, label) => new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error(label + ' timeout')), ms);
    Promise.resolve(p).then(v => { clearTimeout(timer); resolve(v); }, e => { clearTimeout(timer); reject(e); });
  });
  const move = (pano, ms, yaw, fov) => new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('move timeout')), ms + 20000);
    f.moveToPano(pano, { effect: 'fly', duration: ms, longitude: yaw, latitude: 0, fov,
      moveEndCallback: () => { clearTimeout(timer); resolve(); },
      moveCancelCallback: () => { clearTimeout(timer); reject(new Error('move cancelled')); } });
  });
  let recorder, stream, raf, origin, stopped;
  const chunks = [];
  const snapshot = () => ({ mode: f.state.mode, pano: f.state.panoIndex,
    pose: f.getPose(), camera: f.camera.position.toArray() });
  const mark = name => t.marks.push({ name, ms: performance.now() - origin, ...snapshot() });
  try {
    // Use a real arrival callback to avoid stale tiles from setState-only reset.
    const init = recipe.start;
    if (f.state.mode !== 'Panorama') await deadline(f.changeMode('Panorama', { panoIndex: init.pano }, 600), 25000, 'mode');
    const away = f.state.panoIndex === init.pano ? f.observers[init.pano].accessibleNodes[0] : init.pano;
    await deadline(f.preloadPano(away), 25000, 'preload');
    await move(away, 600, init.yaw, init.fov);
    if (away !== init.pano) { await deadline(f.preloadPano(init.pano), 25000, 'preload'); await move(init.pano, 600, init.yaw, init.fov); }
    await deadline(f.ready({ tile: true }), 25000, 'tiles');
    await sleep(500);
    for (const s of recipe.steps) if (Number.isInteger(s.pano)) await deadline(f.preloadPano(s.pano), 25000, 'preload target');
    const goal = f.observers[init.pano].position;
    const actual = f.getPose().offset;
    if (f.state.panoIndex !== init.pano || Math.hypot(actual.x-goal.x, actual.y-goal.y, actual.z-goal.z) > .02) throw new Error('Reset mismatch');
    const canvas = f.renderer.domElement;
    stream = canvas.captureStream(30);
    const mimeType = ['video/webm;codecs=vp9', 'video/webm;codecs=vp8'].find(x => MediaRecorder.isTypeSupported(x));
    if (!mimeType) throw new Error('No supported recorder codec');
    recorder = new MediaRecorder(stream, { mimeType, videoBitsPerSecond: 6000000 });
    recorder.ondataavailable = e => { if (e.data.size) chunks.push(e.data); };
    recorder.onerror = e => { t.error = String(e.error); };
    stopped = new Promise(resolve => { recorder.onstop = resolve; });
    t.capture = { width: canvas.width, height: canvas.height, mimeType, requestedFps: 30, sdkNativeHeightException: true, metricClearance: 'unverified' };
    t.scene = { workCode: f.work.workCode, model: !!f.model,
      observers: f.observers.map(o => ({ pano: o.panoIndex, position: o.position, standingPosition: o.standingPosition, adjacent: o.accessibleNodes })),
      labels: f.plugins.modelRoomLabelPlugin?.roomLabels.map(x => ({ name: x.name, pano: x.panoIndex, position: x.position })) };
    origin = performance.now(); recorder.start(500); mark('start');
    let prev = 0;
    const sample = () => {
      if (performance.now() - prev > 100) { t.samples.push({ ms: performance.now()-origin, ...snapshot() }); prev = performance.now(); }
      f.needsRender = true; raf = requestAnimationFrame(sample);
    };
    sample();
    for (const [i, s] of recipe.steps.entries()) {
      mark(`step-${i}-${s.kind}-start`);
      if (s.kind === 'move') { await move(s.pano, s.ms, s.yaw, s.fov ?? f.state.fov); await deadline(f.ready({tile:true}), 25000, 'tiles'); }
      else if (s.kind === 'model') { await deadline(f.changeMode('Model', { longitude:s.yaw, latitude:s.pitch, offset:s.offset, fov:s.fov ?? 80 }, s.ms), s.ms+25000, 'model'); await sleep(s.ms+150); }
      else if (s.kind === 'pano') { await deadline(f.changeMode('Panorama', { panoIndex:s.pano, longitude:s.yaw, latitude:0, fov:s.fov ?? 80 }, s.transition === 'cut' ? 0 : s.ms), s.ms+25000, 'pano'); await sleep(s.ms+150); await deadline(f.ready({tile:true}),25000,'pano tiles'); }
      else if (s.kind === 'hold') await sleep(s.ms);
      else {
        // Explicit cubic easing, constant pano/offset; this is not a dolly.
        const a = f.getPose(); const start = performance.now();
        await new Promise(resolve => {
          const tick = () => {
            const u = Math.min(1, (performance.now()-start)/s.ms), e = u*u*(3-2*u);
            f.updateCamera({ longitude:a.longitude+((s.yaw ?? a.longitude)-a.longitude)*e,
              latitude:a.latitude, fov:a.fov+((s.fov ?? a.fov)-a.fov)*e }, 0);
            if (u < 1) requestAnimationFrame(tick); else resolve();
          }; tick();
        });
      }
      mark(`step-${i}-${s.kind}-end`);
      if (s.kind === 'move' || s.kind === 'pano') {
        if (f.state.panoIndex !== s.pano || f.state.mode !== 'Panorama') throw new Error('Target pano mismatch');
      }
      if (s.kind === 'model' && (f.state.mode !== 'Model' || Math.hypot(f.getPose().offset.x-s.offset.x,f.getPose().offset.y-s.offset.y,f.getPose().offset.z-s.offset.z)>.05)) throw new Error('Model pose mismatch');
      if (['pan','fov'].includes(s.kind) && (Math.abs(f.getPose().fov-(s.fov ?? f.getPose().fov))>.2 || Math.abs(Math.atan2(Math.sin(f.getPose().longitude-(s.yaw ?? f.getPose().longitude)),Math.cos(f.getPose().longitude-(s.yaw ?? f.getPose().longitude))))>.01)) throw new Error('Camera target mismatch');
    }
    mark('end');
  } catch (e) { t.error = String(e); }
  finally {
    cancelAnimationFrame(raf);
    if (recorder && recorder.state !== 'inactive') { recorder.stop(); await stopped; }
    stream?.getTracks().forEach(x => x.stop());
    t.running = false;
    t.durationMs = origin ? performance.now()-origin : 0;
    const blob = new Blob(chunks, { type:'video/webm' });
    t.bytes = blob.size;
    try {
      if (blob.size) { const r = await fetch(`${endpoint}/${token}/video`, {method:'POST',body:blob}); if(!r.ok) throw new Error('Video upload failed'); }
      const r = await fetch(`${endpoint}/${token}/telemetry`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(t)});
      if (!r.ok) throw new Error('Telemetry upload failed');
    } catch (e) { t.exportError = String(e); }
  }
  return { complete: !t.error && !t.exportError, error:t.error, exportError:t.exportError, bytes:t.bytes, durationMs:t.durationMs };
};
'one-method recorder loaded';
