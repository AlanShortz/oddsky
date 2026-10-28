// The living sky: a planetarium of 90,020 real stars (Hipparcos, brighter than Hp 9.3) with every
// Oddsky case at its true position, each one's brightness played back from its own measured light
// curve on a shared clock (2010–2026). Drag to look around, scroll or pinch to zoom, scrub time.
//
// Projection: stereographic, from inside the celestial sphere (north up, east to the left, as the sky
// looks). Background: a procedural Milky Way laid out in real galactic coordinates. No dependencies.

import { h, s } from './util.js';

const D2R = Math.PI / 180;
// J2000 equatorial → galactic rotation (rows)
const GAL = [-0.0548755604, -0.8734370902, -0.4838350155, 0.4941094279, -0.4448296300, 0.7469822445, -0.8676661490, -0.1980763734, 0.4559837762];

const vec = (ra, dec) => [Math.cos(dec * D2R) * Math.cos(ra * D2R), Math.cos(dec * D2R) * Math.sin(ra * D2R), Math.sin(dec * D2R)];
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];

function basis(ra, dec) {
  const a = ra * D2R, d = dec * D2R;
  const fwd = [Math.cos(d) * Math.cos(a), Math.cos(d) * Math.sin(a), Math.sin(d)];
  const up = [-Math.sin(d) * Math.cos(a), -Math.sin(d) * Math.sin(a), Math.cos(d)];
  const right = [Math.sin(a), -Math.cos(a), 0]; // west: east appears on the left from inside the sphere
  return { fwd, up, right };
}

const STAR_VS = `
attribute vec2 aPos; attribute float aMag; attribute float aBv;
uniform vec3 uR, uU, uF; uniform float uEdge, uAspect, uMagLim, uPx, uZoom;
varying vec3 vCol; varying float vA;
void main() {
  float a = aPos.x, d = aPos.y;
  vec3 v = vec3(cos(d) * cos(a), cos(d) * sin(a), sin(d));
  float z = dot(v, uF);
  if (z < -0.3) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); gl_PointSize = 0.0; return; }
  float k = 2.0 / (1.0 + z);
  vec2 p = vec2(dot(v, uR), dot(v, uU)) * k / uEdge;
  gl_Position = vec4(p.x, p.y * uAspect, 0.0, 1.0);
  float m = aMag;
  gl_PointSize = uPx * clamp(12.0 * pow(10.0, -0.15 * (m + 1.2)) * uZoom, 2.0, 16.0);
  vA = clamp(smoothstep(uMagLim + 1.2, uMagLim - 3.0, m), 0.0, 1.0) * 1.15;
  float t = clamp((aBv + 0.35) / 2.1, 0.0, 1.0);
  vec3 blue = vec3(0.68, 0.78, 1.0), white = vec3(1.0, 0.98, 0.95), yel = vec3(1.0, 0.86, 0.66), red = vec3(1.0, 0.66, 0.5);
  vCol = t < 0.25 ? mix(blue, white, t / 0.25) : t < 0.55 ? mix(white, yel, (t - 0.25) / 0.3) : mix(yel, red, (t - 0.55) / 0.45);
}`;
const STAR_FS = `
precision mediump float; varying vec3 vCol; varying float vA; uniform vec3 uTint;
void main() {
  vec2 c = gl_PointCoord - 0.5; float r2 = dot(c, c) * 4.0;
  float core = exp(-r2 * 7.0), halo = exp(-r2 * 2.2) * 0.35;
  float a = (core + halo) * vA;
  if (a < 0.01) discard;
  gl_FragColor = vec4(vCol * uTint * a, a);
}`;
const BG_VS = `attribute vec2 aXY; varying vec2 vXY; void main() { vXY = aXY; gl_Position = vec4(aXY, 0.0, 1.0); }`;
const BG_FS = `
precision highp float; varying vec2 vXY;
uniform vec3 uR, uU, uF; uniform float uEdge, uAspect, uFoot, uPxAng; uniform mat3 uGal; uniform vec3 uTint, uBg;
float hash(vec3 p) { p = fract(p * 0.3183099 + 0.1); p *= 17.0; return fract(p.x * p.y * p.z * (p.x + p.y + p.z)); }
float noise(vec3 x) { vec3 i = floor(x), f = fract(x); f = f * f * (3.0 - 2.0 * f);
  return mix(mix(mix(hash(i), hash(i + vec3(1,0,0)), f.x), mix(hash(i + vec3(0,1,0)), hash(i + vec3(1,1,0)), f.x), f.y),
             mix(mix(hash(i + vec3(0,0,1)), hash(i + vec3(1,0,1)), f.x), mix(hash(i + vec3(0,1,1)), hash(i + vec3(1,1,1)), f.x), f.y), f.z); }
float fbm(vec3 p) { float s = 0.0, a = 0.5; for (int i = 0; i < 5; i++) { s += a * noise(p); p *= 2.03; a *= 0.5; } return s; }
void main() {
  vec2 p = vec2(vXY.x, vXY.y / uAspect) * uEdge; float r2 = dot(p, p);
  float z = (4.0 - r2) / (4.0 + r2); vec2 xy = p * 4.0 / (4.0 + r2);
  vec3 dir = normalize(xy.x * uR + xy.y * uU + z * uF);
  vec3 g = uGal * dir; float b = asin(clamp(g.z, -1.0, 1.0)); float l = atan(g.y, g.x);
  float n = fbm(dir * 6.0), n2 = fbm(dir * 19.0 + 3.1);
  float band = exp(-pow(b / (0.13 + 0.05 * n), 2.0)) * (0.5 + 0.5 * cos(l)) * 0.9 + exp(-pow(b / 0.32, 2.0)) * 0.25;
  float rift = exp(-pow((b - 0.015 - 0.03 * n2) / 0.03, 2.0)) * smoothstep(1.4, 0.2, abs(l - 0.35)) * 0.7;
  float glow = max(0.0, band * (0.55 + 0.75 * n) * (1.0 - rift)) * (0.75 + 0.5 * n2);
  vec3 core = mix(vec3(0.42, 0.48, 0.75), vec3(0.95, 0.82, 0.68), clamp(cos(l) * exp(-abs(b) * 6.0), 0.0, 1.0));
  vec3 col = uBg + core * uTint * glow * 0.3;
  if (uFoot > 0.0) {
    float w = uPxAng * 1.3, edge = abs(abs(b) - 0.17453);
    float line = smoothstep(w, 0.0, edge) * step(0.5, fract(l * 30.0));
    float inside = step(0.17453, abs(b));
    col += vec3(0.48, 0.55, 1.0) * (line * 0.6 + inside * 0.025) * uFoot;
  }
  gl_FragColor = vec4(col, 1.0);
}`;

function program(gl, vs, fs) {
  const mk = (t, src) => { const sh = gl.createShader(t); gl.shaderSource(sh, src); gl.compileShader(sh); if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(sh)); return sh; };
  const p = gl.createProgram(); gl.attachShader(p, mk(gl.VERTEX_SHADER, vs)); gl.attachShader(p, mk(gl.FRAGMENT_SHADER, fs)); gl.linkProgram(p);
  if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p));
  const u = new Proxy({}, { get: (_, k) => gl.getUniformLocation(p, k) });
  return { p, u, a: (k) => gl.getAttribLocation(p, k) };
}

// galactic ↔ equatorial (GAL rotates equatorial vectors into galactic ones)
function toGal(ra, dec) {
  const v = vec(ra, dec), g = [0, 1, 2].map((r) => GAL[3 * r] * v[0] + GAL[3 * r + 1] * v[1] + GAL[3 * r + 2] * v[2]);
  return [((Math.atan2(g[1], g[0]) / D2R) + 360) % 360, Math.asin(Math.max(-1, Math.min(1, g[2]))) / D2R];
}
function fromGal(l, b) {
  const g = vec(l, b), v = [0, 1, 2].map((c) => GAL[c] * g[0] + GAL[3 + c] * g[1] + GAL[6 + c] * g[2]);
  return [((Math.atan2(v[1], v[0]) / D2R) + 360) % 360, Math.asin(Math.max(-1, Math.min(1, v[2]))) / D2R];
}

const ease = (x) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);

/** Brightness change (mag; + is fainter) of a case at decimal year T, from its binned series. */
export function dmAt(c, sky, T) {
  const x = (T - sky.t0) / sky.step, i = Math.floor(x), dm = c.dm;
  const at = (k) => (k >= 0 && k < dm.length ? dm[k] : null);
  const a = at(i), b = at(i + 1);
  if (a != null && b != null) return a + (b - a) * (x - i);
  if (a != null) return a;
  for (let k = 1; k < 6; k++) { const v = at(i - k) ?? at(i + 1 + k); if (v != null) return v; }
  return null;
}

/**
 * Create the sky. Returns { el, flyTo, setTime, play, pause, on, cases }.
 * opts: { stars: ArrayBuffer, sky: {t0, step, cases}, onPick(case) }
 */
export function createSky({ stars, sky, onPick, interactive = true }) {
  const el = h('div', { class: 'sky' });
  const canvas = h('canvas', { class: 'sky-canvas', 'aria-hidden': 'true' });
  const layer = h('div', { class: 'sky-markers' });
  el.append(canvas, layer);
  const gl = canvas.getContext('webgl', { antialias: false, premultipliedAlpha: true, alpha: false, preserveDrawingBuffer: true });
  if (!gl) { el.classList.add('no-webgl'); return { el, flyTo() {}, setTime() {}, play() {}, pause() {}, state: {}, cases: [] }; }

  // ---- stars ----
  const n = stars.byteLength / 6, dv = new DataView(stars);
  const pos = new Float32Array(n * 2), mag = new Float32Array(n), bv = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    pos[2 * i] = (dv.getUint16(6 * i, true) / 65535) * 2 * Math.PI;
    pos[2 * i + 1] = (dv.getInt16(6 * i + 2, true) / 32767) * Math.PI / 2;
    mag[i] = dv.getUint8(6 * i + 4) / 20 - 2;
    bv[i] = dv.getInt8(6 * i + 5) / 50;
  }
  const starP = program(gl, STAR_VS, STAR_FS), bgP = program(gl, BG_VS, BG_FS);
  const buf = (data) => { const b = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, b); gl.bufferData(gl.ARRAY_BUFFER, data, gl.STATIC_DRAW); return b; };
  const bPos = buf(pos), bMag = buf(mag), bBv = buf(bv), bQuad = buf(new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]));

  // ---- state ----
  const st = { ra: 290, dec: 25, fov: 110, T: 2014, playing: false, rate: 0.9, foot: 0, footTarget: 0, red: false };
  let anim = null, W = 1, H = 1, dpr = 1, last = 0, visible = true, lastUser = -1e9;
  const ptrs = new Map();
  const listeners = {};
  const emit = (k, v) => (listeners[k] ?? []).forEach((f) => f(v));

  // ---- markers ----
  const cases = sky.cases.map((c) => {
    const m = h('button', { type: 'button', class: `sky-mark ${c.control ? 'is-control' : ''}`, 'aria-label': `${c.id}: ${c.title}` },
      h('span', { class: 'sm-glow' }), h('span', { class: 'sm-dot' }), h('span', { class: 'sm-ring' }),
      h('span', { class: 'sm-label mono' }, h('b', null, c.id), ' ', c.target && !/^(Gaia|AllWISE)/.test(c.target) ? c.target : ''));
    m.addEventListener('click', (e) => { e.stopPropagation(); onPick?.(c); });
    layer.append(m);
    return { ...c, v: vec(c.ra, c.dec), m };
  });

  function project(v, b) {
    const z = dot(v, b.fwd); if (z < -0.2) return null;
    const k = 2 / (1 + z), edge = 2 * Math.tan((st.fov * D2R) / 4);
    const x = (dot(v, b.right) * k) / edge, y = ((dot(v, b.up) * k) / edge) * (W / H);
    return [((x + 1) / 2) * W, ((1 - y) / 2) * H, z];
  }

  function resize() {
    const r = el.getBoundingClientRect();
    dpr = Math.min(2, window.devicePixelRatio || 1);
    W = Math.max(1, r.width); H = Math.max(1, r.height);
    canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr);
  }
  new ResizeObserver(resize).observe(el);
  resize();

  function draw() {
    const b = basis(st.ra, st.dec);
    const edge = 2 * Math.tan((st.fov * D2R) / 4), aspect = W / H;
    gl.viewport(0, 0, canvas.width, canvas.height);
    const red = document.documentElement.dataset.theme === 'dark';
    const tint = red ? [1.0, 0.42, 0.35] : [1, 1, 1];
    // background
    gl.disable(gl.BLEND);
    gl.useProgram(bgP.p);
    gl.uniform3fv(bgP.u.uR, b.right); gl.uniform3fv(bgP.u.uU, b.up); gl.uniform3fv(bgP.u.uF, b.fwd);
    gl.uniform1f(bgP.u.uEdge, edge); gl.uniform1f(bgP.u.uAspect, aspect); gl.uniform1f(bgP.u.uFoot, st.foot);
    gl.uniform1f(bgP.u.uPxAng, (st.fov * D2R) / W);
    gl.uniformMatrix3fv(bgP.u.uGal, false, [GAL[0], GAL[3], GAL[6], GAL[1], GAL[4], GAL[7], GAL[2], GAL[5], GAL[8]]);
    gl.uniform3fv(bgP.u.uTint, tint); gl.uniform3fv(bgP.u.uBg, red ? [0.03, 0.005, 0.004] : [0.016, 0.02, 0.04]);
    gl.bindBuffer(gl.ARRAY_BUFFER, bQuad);
    const aXY = bgP.a('aXY'); gl.enableVertexAttribArray(aXY); gl.vertexAttribPointer(aXY, 2, gl.FLOAT, false, 0, 0);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    gl.disableVertexAttribArray(aXY);
    // stars
    gl.enable(gl.BLEND); gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
    gl.useProgram(starP.p);
    gl.uniform3fv(starP.u.uR, b.right); gl.uniform3fv(starP.u.uU, b.up); gl.uniform3fv(starP.u.uF, b.fwd);
    gl.uniform1f(starP.u.uEdge, edge); gl.uniform1f(starP.u.uAspect, aspect); gl.uniform1f(starP.u.uPx, dpr);
    const lim = 7.2 + 2.4 * Math.max(0, Math.min(1, (110 - st.fov) / 90));
    const k = st.exp0 == null ? 1 : Math.min(1, (performance.now() - st.exp0) / st.expDur);
    gl.uniform1f(starP.u.uMagLim, -1.5 + (lim + 1.5) * (1 - Math.pow(1 - k, 2.2)));
    gl.uniform1f(starP.u.uZoom, Math.pow(70 / st.fov, 0.3)); gl.uniform3fv(starP.u.uTint, tint);
    for (const [name, bb, size] of [['aPos', bPos, 2], ['aMag', bMag, 1], ['aBv', bBv, 1]]) {
      const loc = starP.a(name); gl.bindBuffer(gl.ARRAY_BUFFER, bb); gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, size, gl.FLOAT, false, 0, 0);
    }
    gl.drawArrays(gl.POINTS, 0, n);
    // markers
    for (const c of cases) {
      const p = project(c.v, b);
      if (!p || p[0] < -40 || p[0] > W + 40 || p[1] < -40 || p[1] > H + 40) { c.m.style.display = 'none'; continue; }
      const dm = dmAt(c, sky, st.T);
      const f = dm == null ? 1 : Math.min(3, Math.pow(10, -0.4 * dm));
      c.m.style.display = '';
      c.m.style.transform = `translate(${p[0].toFixed(1)}px, ${p[1].toFixed(1)}px)`;
      c.m.style.setProperty('--f', f.toFixed(3));
      c.m.classList.toggle('is-dim', dm != null && dm > 0.25);
      c.m.classList.toggle('is-bright', dm != null && dm < -0.25);
      c.m.classList.toggle('is-nodata', dm == null);
      c.m.dataset.light = dm == null ? 'no data' : Math.abs(dm) < 0.03 ? 'normal light' : `${(f * 100).toFixed(f < 0.1 ? 1 : 0)}% of normal light`;
    }
    layer.classList.toggle('show-labels', st.fov < 75);
  }

  function frame(now) {
    const dt = last ? Math.min(0.06, (now - last) / 1000) : 0; last = now;
    if (anim) {
      const k = Math.min(1, (now - anim.start) / anim.dur), e = ease(k);
      // great-circle interpolation of the view direction, plus a zoom out-and-in for long hops
      const a = anim.from, b = anim.to, om = Math.acos(Math.max(-1, Math.min(1, dot(a.v, b.v))));
      let v = a.v;
      if (om > 1e-4) { const s0 = Math.sin((1 - e) * om) / Math.sin(om), s1 = Math.sin(e * om) / Math.sin(om); v = [0, 1, 2].map((i) => a.v[i] * s0 + b.v[i] * s1); }
      st.ra = ((Math.atan2(v[1], v[0]) / D2R) + 360) % 360; st.dec = Math.asin(Math.max(-1, Math.min(1, v[2]))) / D2R;
      const hop = Math.min(1, om / 1.2) * 45;
      st.fov = a.fov + (b.fov - a.fov) * e + Math.sin(e * Math.PI) * hop;
      if (k >= 1) { const done = anim.done; anim = null; done?.(); }
    }
    if (st.drift && !anim && !ptrs.size && performance.now() - lastUser > 5000) {
      if (st.drift.resync) { const g = toGal(st.ra, st.dec); st.drift.l = g[0]; st.drift.b = g[1]; st.drift.resync = false; }
      st.drift.l = (st.drift.l + dt * st.drift.rate + 360) % 360;
      st.drift.b += (st.drift.b0 - st.drift.b) * Math.min(1, dt * 0.15);
      const e = fromGal(st.drift.l, st.drift.b); st.ra = e[0]; st.dec = e[1];
    }
    if (st.playing) {
      st.T += dt * st.rate;
      if (st.T > (st.T1 ?? 2026.9)) { if (st.loop) st.T = st.T0 ?? 2014; else { st.T = st.T1 ?? 2026.9; st.playing = false; emit('end'); } }
      emit('time', st.T);
    }
    st.foot += (st.footTarget - st.foot) * Math.min(1, dt * 4);
    if (visible) draw();
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
  new IntersectionObserver(([e]) => { visible = e.isIntersecting; }).observe(el);

  // ---- interaction ----
  if (interactive) {
    let pinch0 = null, vx = 0, vy = 0;
    canvas.addEventListener('pointerdown', (e) => { if (e.pointerType === 'mouse') canvas.setPointerCapture(e.pointerId); ptrs.set(e.pointerId, [e.clientX, e.clientY]); });
    canvas.addEventListener('pointerup', (e) => { ptrs.delete(e.pointerId); pinch0 = null; if (!ptrs.size) ptrs.moved = false; });
    canvas.addEventListener('pointercancel', (e) => { ptrs.delete(e.pointerId); pinch0 = null; if (!ptrs.size) ptrs.moved = false; });
    canvas.addEventListener('pointermove', (e) => {
      if (!ptrs.has(e.pointerId)) return;
      const prev = ptrs.get(e.pointerId); ptrs.set(e.pointerId, [e.clientX, e.clientY]);
      if (anim || !ptrs.moved) { anim = null; ptrs.moved = true; emit('user'); } // a real drag, not a tap or a page scroll
      lastUser = performance.now(); if (st.drift) st.drift.resync = true;
      if (ptrs.size === 2) {
        const [p, q] = [...ptrs.values()], d = Math.hypot(p[0] - q[0], p[1] - q[1]);
        if (pinch0) st.fov = Math.max(6, Math.min(160, st.fov * (pinch0 / d)));
        pinch0 = d; return;
      }
      const scale = st.fov / H;
      vx = (e.clientX - prev[0]) * scale; vy = e.pointerType === 'touch' ? 0 : (e.clientY - prev[1]) * scale; // on touch, vertical swipes belong to the page
      st.ra = (st.ra + vx / Math.max(0.2, Math.cos(st.dec * D2R)) + 360) % 360;
      st.dec = Math.max(-89, Math.min(89, st.dec + vy));
    });
    // Cooperative scrolling: a plain wheel scrolls the page, always. Pinch on a trackpad (which the
    // browser reports as ctrl+wheel) or ⌘/Ctrl+scroll zooms the sky; a plain scroll over it just says so.
    const mac = /Mac|iPhone|iPad/.test(navigator.platform);
    const nudge = h('p', { class: 'sky-nudge mono', role: 'status' }, `${mac ? '⌘' : 'Ctrl'} + scroll or pinch to zoom the sky`);
    el.append(nudge);
    let nudgeT;
    el.addEventListener('wheel', (e) => {
      if (!(e.ctrlKey || e.metaKey)) {
        nudge.classList.add('is-on'); clearTimeout(nudgeT); nudgeT = setTimeout(() => nudge.classList.remove('is-on'), 1400);
        return;
      }
      e.preventDefault(); anim = null; emit('user'); nudge.classList.remove('is-on'); lastUser = performance.now(); if (st.drift) st.drift.resync = true;
      st.fov = Math.max(6, Math.min(160, st.fov * Math.exp(Math.max(-60, Math.min(60, e.deltaY)) * 0.012)));
    }, { passive: false });
  }

  return {
    el, state: st, cases,
    on(k, f) { (listeners[k] ??= []).push(f); },
    flyTo(ra, dec, fov, dur = 2600) {
      return new Promise((res) => { anim = { start: performance.now(), dur, from: { v: vec(st.ra, st.dec), fov: st.fov }, to: { v: vec(ra, dec), fov }, done: res }; });
    },
    setTime(T) { st.T = T; emit('time', T); },
    play({ from, to, rate, loop = false } = {}) { if (from != null) st.T = from; st.T0 = from ?? st.T0; st.T1 = to ?? 2026.9; if (rate) st.rate = rate; st.loop = loop; st.playing = true; },
    pause() { st.playing = false; },
    footprint(on) { st.footTarget = on ? 1 : 0; },
    /** Develop the field like a photographic plate: brightest stars first, faintest last. */
    expose(ms = 4200) { st.exp0 = performance.now(); st.expDur = ms; },
    /** Pan slowly along the Milky Way (galactic longitude l, latitude b, degrees per second). */
    drift(l, b, rate) { st.drift = { l, b, b0: b, rate, resync: false }; },
    zoom(f) { anim = null; st.fov = Math.max(6, Math.min(160, st.fov * f)); },
  };
}

// ---- the timeline under the sky --------------------------------------------------------------------
export function timeline(sky, skyData, { onScrub }) {
  const T0 = 2010, T1 = 2026.9;
  const svg = s('svg', { class: 'tl-sky', viewBox: '0 0 1000 40', preserveAspectRatio: 'none' });
  const X = (t) => ((t - T0) / (T1 - T0)) * 1000;
  for (let y = 2010; y <= 2026; y++) {
    svg.append(s('line', { x1: X(y), x2: X(y), y1: 26, y2: y % 5 ? 30 : 34, class: 'tls-tick' }));
    if (y % 2 === 0) svg.append(s('text', { x: X(y) + 3, y: 38, class: 'tls-year' }, String(y)));
  }
  // rug: every ~18-day bin in which some case was ≥ 0.4 mag off its normal
  // rug: when each star went dark (≥ 0.4 mag fainter than usual), one mark per event; stars that are
  // off-normal most of the time (Miras, R CrB in a long decline, dwarf novae) are left out
  for (const c of skyData.cases) {
    if (c.control) continue;
    const have = c.dm.filter((v) => v != null), off = have.filter((v) => Math.abs(v) >= 0.4).length;
    if (!have.length || off / have.length > 0.25) continue;
    let start = null;
    c.dm.forEach((v, i) => {
      const on = v != null && v >= 0.4;
      if (on && start == null) start = i;
      if ((!on || i === c.dm.length - 1) && start != null) {
        const a = skyData.t0 + start * skyData.step, b = skyData.t0 + i * skyData.step;
        svg.append(s('rect', { x: X(a), y: 8, width: Math.max(3, X(b) - X(a)), height: 12, rx: 1.5, class: 'tls-dim' }, s('title', null, `${c.id} ${c.target ?? ''}: dimmed`)));
        start = null;
      }
    });
  }
  const head = s('line', { y1: 0, y2: 40, class: 'tls-head' });
  svg.append(s('line', { x1: 0, x2: 1000, y1: 26, y2: 26, class: 'tls-axis' }), head);
  const seek = (e) => { const r = svg.getBoundingClientRect(); onScrub(T0 + Math.max(0, Math.min(1, (e.clientX - r.left) / r.width)) * (T1 - T0)); };
  svg.addEventListener('pointerdown', (e) => { svg.setPointerCapture(e.pointerId); seek(e); });
  svg.addEventListener('pointermove', (e) => { if (e.buttons) seek(e); });
  return { el: svg, set(T) { head.setAttribute('x1', X(T)); head.setAttribute('x2', X(T)); } };
}

export const yearLabel = (T) => {
  const y = Math.floor(T), m = Math.min(11, Math.floor((T - y) * 12));
  return [y, ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][m]];
};

