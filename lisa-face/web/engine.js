/*
 * LISA Face engine.
 * Copyright (C) 2026 Sharat. All rights reserved.
 *
 * Turns LISA's live status into numbers a face can animate. The page
 * loads this file, then once per frame calls Lisa.step(dtMs) and reads:
 *
 *   Lisa.mode     "idle" | "listening" | "thinking" | "speaking"
 *   Lisa.energy   0..1  smoothed loudness of her voice (drive motion with this)
 *   Lisa.wave     Float32Array(64), 0..1  the current shape of her voice
 *   Lisa.raw      the latest signed waveform, or null when she is quiet
 *   Lisa.mic      0..1  listening level (demo only)
 *   Lisa.alert    true when something needs attention
 *   Lisa.usage    plan-usage rows [{label, text, hot}], usually empty
 *   Lisa.name, Lisa.tag ("L.I.S.A."), Lisa.credit
 *
 * Live status streams in from server.py (/stream). Add ?demo to watch a
 * scripted conversation with no voice line, or ?shot=<mode> to freeze one
 * mode for a screenshot (the title turns to "ready" once it is drawn).
 * Sound is played by server.py, not the page. Keys: F fullscreen.
 */
"use strict";

const Lisa = (() => {
  const q = new URLSearchParams(location.search);
  const shot = q.get("shot");
  const demo = !!shot || q.has("demo") || location.protocol === "file:";
  const tagOf = n => n.toUpperCase().split("").join(".") + ".";

  const L = {
    mode: "idle", energy: 0, loud: 0, wave: new Float32Array(64), raw: null,
    mic: 0, alert: false, usage: [], name: "LISA", tag: "L.I.S.A.",
    credit: "Built by Sharat", demo, shot, fx: {},
  };
  let latest = { mode: "idle", loud: 0, wave: null, alert: false,
                 voiceSound: false, usage: {} };

  /* ---------------- live feed ---------------- */
  function connect() {
    // EventSource reconnects on its own if the server restarts
    new EventSource("/stream").onmessage = ev => {
      try { latest = JSON.parse(ev.data); } catch (e) { /* keep the last good one */ }
    };
    fetch("/settings", { cache: "no-store" }).then(r => r.json()).then(s => {
      if (s.name) { L.name = s.name; L.tag = tagOf(s.name); }
      if (typeof s.credit === "string") L.credit = s.credit;
    }).catch(() => {});
  }

  /* ---------------- demo conversation ---------------- */
  const SCRIPT = [["idle", 5.5], ["listening", 3.2], ["thinking", 4.5], ["speaking", 8]];
  const LOOP = SCRIPT.reduce((a, p) => a + p[1], 0);
  let clock = 0;
  function demoStep(s) {
    clock += s;
    let mode = shot || q.get("mode");
    if (!mode) {
      let t = clock % LOOP;
      for (const [m, len] of SCRIPT) { if (t < len) { mode = m; break; } t -= len; }
    }
    const talking = mode === "speaking";
    // syllable-like bursts from two beating rhythms
    const beat = Math.max(0, Math.sin(clock * 7.3) * .55 + Math.sin(clock * 2.3 + 1) * .6 - .1);
    const wave = talking ? Array.from({ length: 64 }, (_, i) =>
      (Math.sin(i * .41 + clock * 11) + .6 * Math.sin(i * 1.3 - clock * 17)
        + .3 * Math.sin(i * 3.1 + clock * 5)) * 7000 * (.2 + beat)) : null;
    latest = { mode, loud: talking ? Math.min(1, beat) : 0, wave,
               alert: false, voiceSound: false, usage: {} };
    L.mic = mode === "listening"
      ? .3 + .5 * Math.abs(Math.sin(clock * 3.1) * Math.sin(clock * .7)) : 0;
  }

  /* ---------------- smoothing ---------------- */
  let ceiling = .05, waveCeil = 300;
  const ease = (s, tau) => 1 - Math.exp(-s / tau);
  function step(dt) {
    const s = Math.max(0, Math.min(.1, dt / 1000));
    if (demo) demoStep(s);
    L.mode = latest.mode || "idle";
    L.alert = !!latest.alert;
    L.loud = latest.loud || 0;
    L.usage = usageRows(latest.usage || {});

    // loudness against a slowly sinking ceiling: soft and loud speech both
    // use the full 0..1 range. Fast to rise, slower to let go.
    ceiling = Math.max(L.loud, .05, ceiling * Math.exp(-s * .7));
    const target = L.loud / ceiling;
    L.energy += (target - L.energy) * ease(s, target > L.energy ? .05 : .32);

    const w = latest.wave;
    L.raw = w && w.length ? w : null;
    if (L.raw) {
      let peak = 0;
      for (const v of w) peak = Math.max(peak, Math.abs(v));
      waveCeil = Math.max(peak, 300, waveCeil * Math.exp(-s * 1.2));
      for (let i = 0; i < 64; i++) {
        const v = Math.min(1, Math.abs(w[Math.floor(i * w.length / 64)]) / waveCeil);
        L.wave[i] += (v - L.wave[i]) * ease(s, .04);
      }
    } else {
      for (let i = 0; i < 64; i++) L.wave[i] *= Math.exp(-s * 7);
    }
  }

  function usageRows(u) {
    const rows = [];
    for (const [label, key] of [["5H", "five_hour"], ["7D", "seven_day"]]) {
      const w = u[key];
      if (!w) continue;
      const pct = w.utilization == null ? null : Math.round(w.utilization * 100);
      const secs = (w.resets_at || 0) - Date.now() / 1000;
      const left = secs <= 0 ? "" : secs < 3600 ? Math.round(secs / 60) + "m"
        : secs < 86400 ? Math.round(secs / 3600) + "h" : Math.round(secs / 86400) + "d";
      rows.push({ label, hot: pct != null && pct >= 80,
                  text: (pct == null ? "--" : pct + "%") + (left ? "  " + left : "") });
    }
    return rows;
  }

  addEventListener("keydown", e => {
    if (e.key.toLowerCase() === "f") {
      document.fullscreenElement ? document.exitFullscreen()
        : document.documentElement.requestFullscreen();
    }
  });

  /* ---------------- drawing helpers ---------------- */
  // soft round light, as a reusable sprite
  L.fx.glow = (rgb, size) => {
    const c = document.createElement("canvas");
    c.width = c.height = size;
    const g = c.getContext("2d"), h = size / 2;
    const grd = g.createRadialGradient(h, h, 0, h, h, h);
    const [r, gr, b] = rgb;
    grd.addColorStop(0, `rgba(${r},${gr},${b},1)`);
    grd.addColorStop(.2, `rgba(${r},${gr},${b},.6)`);
    grd.addColorStop(.55, `rgba(${r},${gr},${b},.12)`);
    grd.addColorStop(1, `rgba(${r},${gr},${b},0)`);
    g.fillStyle = grd;
    g.fillRect(0, 0, size, size);
    return c;
  };

  // Light bleed: the sharp layer, plus blurred low-resolution copies of it,
  // all added on top of the destination.
  const blurA = document.createElement("canvas"), blurB = document.createElement("canvas");
  L.fx.bloom = (dst, src, w, h) => {
    const aw = Math.max(1, w >> 2), ah = Math.max(1, h >> 2);
    const bw = Math.max(1, w >> 3), bh = Math.max(1, h >> 3);
    if (blurA.width !== aw || blurA.height !== ah) { blurA.width = aw; blurA.height = ah; }
    if (blurB.width !== bw || blurB.height !== bh) { blurB.width = bw; blurB.height = bh; }
    const a = blurA.getContext("2d"), b = blurB.getContext("2d");
    a.clearRect(0, 0, aw, ah); a.filter = "blur(2px)"; a.drawImage(src, 0, 0, aw, ah); a.filter = "none";
    b.clearRect(0, 0, bw, bh); b.filter = "blur(3px)"; b.drawImage(src, 0, 0, bw, bh); b.filter = "none";
    const before = dst.globalCompositeOperation;
    dst.globalCompositeOperation = "lighter";
    dst.drawImage(src, 0, 0);
    dst.globalAlpha = .9; dst.drawImage(blurA, 0, 0, w, h);
    dst.globalAlpha = .7; dst.drawImage(blurB, 0, 0, w, h);
    dst.globalAlpha = 1;
    dst.globalCompositeOperation = before;
  };

  // Text that settles letter by letter, in random order, out of noise.
  const NOISE = "01<>/\\|=+*#%ABCDEFHKLMNPRSTVXZ";
  L.fx.decoder = (text, ms) => {
    const at = Array.from(text, () => Math.random() * ms);
    let t = 0;
    return dt => {
      t += dt;
      let out = "";
      for (let i = 0; i < text.length; i++)
        out += t >= at[i] || text[i] === " " ? text[i] : NOISE[Math.random() * NOISE.length | 0];
      return out;
    };
  };

  /* ---------------- frame loop ---------------- */
  L.run = frame => {
    if (shot) {
      for (let i = 0; i < 400; i++) frame(16.7);     // settle into the pinned mode
      setTimeout(() => { document.title = "ready"; }, 400);
    }
    let last = performance.now();
    const loop = now => {
      // a frame's timestamp can predate `last` by a hair; never step backwards
      frame(Math.max(0, Math.min(100, now - last)));
      last = now;
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  };

  L.step = step;
  if (!demo) connect();
  return L;
})();
