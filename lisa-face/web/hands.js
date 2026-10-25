/*
 * LISA hand control.
 * Copyright (C) 2026 Sharat. All rights reserved.
 *
 * Watches the webcam for hands (Google MediaPipe hand tracking, running
 * entirely in this page: video never leaves the computer) and turns what
 * the hands do into LISA's controls:
 *
 *   open hand     the sphere leans toward your hand; a fast swipe spins it
 *   pinch         grab and turn the sphere; a quick pinch-and-release taps
 *   fist (hold)   push-to-talk: LISA listens while the fist stays closed
 *   point         your fingertip lights up the neurons it passes over
 *   two pinches   pull the hands apart or together to zoom (and dive in)
 *
 * Gestures are read from the 3D hand skeleton in real-world meters, so they
 * hold up when the hand tilts or turns: a finger is straight or curled by
 * the actual bend at its joints, and a pinch is the real thumb-to-index gap.
 *
 * Publishes window.LisaHands = {status, hands:[{pts, cx, cy, gesture}], since}
 * for the face to draw the hand hologram. Keys: H camera on/off,
 * G calibration view (camera, skeleton, finger states, pinch gap).
 * Once a second it reports what it saw to the server (logs/hands.log), so
 * problems can be diagnosed from what actually happened.
 */
const MP = "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14";
const HS = (window.LisaHands = { status: "", hands: [], since: null });
const ctl = window.LisaControl;
const now = () => performance.now() / 1000;

const PINCH_ON = .035, PINCH_OFF = .055;   // meters between thumb and index tips
const STRAIGHT = .55, CURLED = .15;        // cosine of the bend at a finger's middle joint
const SETTLE = 2;                          // frames a new gesture must hold before it counts

let video = null, tracker = null, running = false, lastVideoT = -1;

// One camera, one face: two open tabs would fight over the webcam and both
// press the talk key. The newest tab claims it; the others step aside.
const tabs = new BroadcastChannel("lisa-hands");
tabs.onmessage = e => {
  if (e.data === "claim" && running) { stopCamera(); HS.status = "in another tab"; }
};

async function start() {
  HS.status = "starting";
  try {
    const { FilesetResolver, HandLandmarker } = await import(`${MP}/vision_bundle.mjs`);
    video = document.createElement("video");
    video.playsInline = true;
    video.muted = true;
    video.srcObject = await navigator.mediaDevices.getUserMedia({
      video: { width: 640, height: 480, facingMode: "user" } });
    await video.play();
    const files = await FilesetResolver.forVisionTasks(`${MP}/wasm`);
    const opts = delegate => ({
      baseOptions: { modelAssetPath: "models/hand_landmarker.task", delegate },
      runningMode: "VIDEO", numHands: 2,
      minHandDetectionConfidence: .5, minHandPresenceConfidence: .5, minTrackingConfidence: .5 });
    try { tracker = await HandLandmarker.createFromOptions(files, opts("GPU")); }
    catch (e) { tracker = await HandLandmarker.createFromOptions(files, opts("CPU")); }
    running = true;
    HS.status = "active";
    tabs.postMessage("claim");          // any older face tab lets go of the camera
    HS.since = window.LisaClock ? window.LisaClock() : null;
    console.info("hand link: active (tracker ready)");
    report("start", {});
    requestAnimationFrame(loop);
  } catch (e) {
    console.warn(`hand link failed: ${e && e.name}: ${e && e.message}`);
    HS.status = e && e.name === "NotAllowedError" ? "camera blocked"
      : e && e.name === "NotFoundError" ? "no camera" : "offline";
    report("failed", { error: `${e && e.name}: ${e && e.message}` });
    stopCamera();
  }
}

function stopCamera() {
  running = false;
  if (video && video.srcObject) video.srcObject.getTracks().forEach(t => t.stop());
  HS.hands = [];
  release();
}

/* ---------------- reading the hand ---------------- */
const sub = (a, b) => [a.x - b.x, a.y - b.y, a.z - b.z];
const len = v => Math.hypot(v[0], v[1], v[2]) || 1e-6;
const cosB = (a, b) => (a[0] * b[0] + a[1] * b[1] + a[2] * b[2]) / (len(a) * len(b));
const FINGERS = [[5, 6, 8], [9, 10, 12], [13, 14, 16], [17, 18, 20]];   // mcp, pip, tip

function read(world) {
  // straightness of each finger: 1 = dead straight, below 0 = folded back
  const bend = FINGERS.map(([m, p, t]) => cosB(sub(world[p], world[m]), sub(world[t], world[p])));
  const gap = len(sub(world[4], world[8]));
  return { bend, gap };
}

function classify(m, wasPinch) {
  const straight = m.bend.map(c => c > STRAIGHT), curled = m.bend.map(c => c < CURLED);
  const pinch = m.gap < (wasPinch ? PINCH_OFF : PINCH_ON);
  if (pinch && !curled[1]) return "pinch";            // middle finger not folded: a real pinch
  if (curled.every(Boolean)) return "fist";
  if (straight[0] && curled[1] && curled[2] && curled[3]) return "point";
  if (straight.filter(Boolean).length >= 3 && m.gap > PINCH_OFF) return "open";
  if (pinch) return "pinch";
  return "none";
}

// screen position for a landmark: mirrored like a mirror, with a little
// extra reach so the screen edges are easy to get to
function toScreen(p) {
  const W = innerWidth, H = innerHeight;
  return [W / 2 + (.5 - p.x) * W * 1.35, H / 2 + (p.y - .5) * H * 1.35];
}

/* per-hand memory, keyed by which hand it is */
const mem = {};
function handState(key) {
  return mem[key] || (mem[key] = { raw: "none", rawN: 0, gesture: "none", since: 0,
    px: 0, py: 0, vx: 0, vy: 0, startX: 0, startY: 0, seen: 0, m: null });
}

let talkSince = null, zoomPrev = 0, gripping = false;   // gripping: a hand holds the sphere
function grip(on) { if (on !== gripping) { gripping = on; ctl.hold(on); } }

/* ---------------- diagnostics ---------------- */
const stats = { frames: 0, withHands: 0, g: {}, actions: {}, last: null };
function count(obj, k) { obj[k] = (obj[k] || 0) + 1; }
function report(event, data) {
  fetch("/hands-log", { method: "POST", headers: { "X-Lisa-Face": "1", "Content-Type": "application/json" },
    body: JSON.stringify({ event, ...data }) }).catch(() => {});
}
setInterval(() => {
  if (!running || !stats.frames) return;
  report("second", { fps: stats.frames, withHands: stats.withHands, gestures: stats.g,
    actions: stats.actions, sample: stats.last, view: { w: innerWidth, h: innerHeight } });
  stats.frames = stats.withHands = 0; stats.g = {}; stats.actions = {};
}, 1000);

/* ---------------- the loop ---------------- */
function loop() {
  if (!running) return;
  requestAnimationFrame(loop);
  if (video.currentTime === lastVideoT) return;
  lastVideoT = video.currentTime;
  const res = tracker.detectForVideo(video, performance.now());
  const t = now();
  const out = [];
  stats.frames++;
  if ((res.landmarks || []).length) stats.withHands++;
  (res.landmarks || []).forEach((lm, i) => {
    const key = (res.handedness && res.handedness[i] && res.handedness[i][0].categoryName) || "h" + i;
    const st = handState(key);
    const world = (res.worldLandmarks && res.worldLandmarks[i]) || lm;
    st.m = read(world);
    const g = classify(st.m, st.gesture === "pinch");
    if (g === st.raw) st.rawN++; else { st.raw = g; st.rawN = 1; }
    const prevG = st.gesture;
    if (st.rawN >= SETTLE && g !== st.gesture) { st.gesture = g; st.since = t; }
    count(stats.g, st.gesture);
    stats.last = { hand: key, raw: g, gesture: st.gesture,
      bend: st.m.bend.map(c => +c.toFixed(2)), gapCm: +(st.m.gap * 100).toFixed(1) };
    const pts = lm.map(toScreen);
    const palm = [0, 5, 9, 13, 17].reduce((a, j) => [a[0] + pts[j][0] / 5, a[1] + pts[j][1] / 5], [0, 0]);
    const pinchPt = [(pts[4][0] + pts[8][0]) / 2, (pts[4][1] + pts[8][1]) / 2];
    const dt = Math.max(1 / 120, t - (st.seen || t));
    const fresh = t - st.seen > .3;
    st.seen = t;
    act(st, prevG, pts, palm, pinchPt, dt, fresh);
    out.push({ pts, cx: palm[0], cy: palm[1], gesture: st.gesture, raw: g, key, pinchPt, m: st.m, lm });
  });
  // two pinching hands: zoom by how far apart they are
  const pinching = out.filter(h => h.gesture === "pinch");
  if (pinching.length === 2) {
    const d = Math.hypot(pinching[0].pinchPt[0] - pinching[1].pinchPt[0],
                         pinching[0].pinchPt[1] - pinching[1].pinchPt[1]);
    if (zoomPrev > 0) ctl.zoomBy(Math.pow(d / zoomPrev, 1.6));
    zoomPrev = d;
    pinching.forEach(h => { h.gesture = "zoom"; });
    grip(false);
  } else zoomPrev = 0;
  // hands that vanished let go of whatever they held
  if (!out.length) release();
  if (!out.some(h => h.gesture === "fist") && talkSince != null) {
    talkSince = null; ctl.talk(false); count(stats.actions, "talk-off");
  }
  if (!out.some(h => h.gesture === "pinch")) grip(false);
  HS.hands = out;
  drawCalib(out);
}

function act(st, prevG, pts, palm, pinchPt, dt, fresh) {
  const W = innerWidth, H = innerHeight, g = st.gesture, t = now();
  if (g === "open") {
    ctl.lean(palm[0] / W * 2 - 1, palm[1] / H * 2 - 1);
    // a fast sideways swipe spins her
    if (!fresh && prevG === "open") {
      const v = (palm[0] - st.px) / dt / W;
      if (Math.abs(v) > 2.2) { ctl.fling(v * 1.6, 0); count(stats.actions, "swipe"); }
    }
    st.px = palm[0]; st.py = palm[1];
  } else if (g === "pinch") {
    if (prevG !== "pinch" || fresh) {
      st.startX = pinchPt[0]; st.startY = pinchPt[1];
      st.px = pinchPt[0]; st.py = pinchPt[1];
      st.vx = st.vy = 0;
      grip(true);
      count(stats.actions, "grab");
    } else {
      const dx = pinchPt[0] - st.px, dy = pinchPt[1] - st.py;
      ctl.rotate(dx * .007, dy * .007);
      st.vx = dx * .007 / dt; st.vy = dy * .007 / dt;
      st.px = pinchPt[0]; st.py = pinchPt[1];
    }
  } else if (prevG === "pinch") {
    // pinch released: a short, still pinch is a tap; a moving one flings
    const moved = Math.hypot(st.px - st.startX, st.py - st.startY);
    if (t - st.since < .5 && moved < 30) { ctl.tap(st.px, st.py); count(stats.actions, "tap"); }
    else ctl.fling(st.vx * .6, st.vy * .6);
    grip(false);
  }
  if (g === "point") ctl.touch(pts[8][0], pts[8][1]);
  if (g === "fist") {
    if (talkSince == null) talkSince = t;
    if (t - talkSince > .3 && !HS.talking) count(stats.actions, "talk-on");
    if (t - talkSince > .3) { ctl.talk(true); HS.talking = true; }
  } else HS.talking = false;
}

function release() {
  grip(false);
  if (talkSince != null) { talkSince = null; ctl.talk(false); }
  HS.talking = false;
  zoomPrev = 0;
}

/* ---------------- calibration view (G) ---------------- */
const calib = document.createElement("canvas");
calib.width = 320; calib.height = 240;
calib.style.cssText = "position:fixed;right:44px;bottom:70px;width:320px;height:240px;" +
  "border:1px solid rgba(120,200,255,.35);border-radius:6px;pointer-events:none;z-index:5";
let calibOn = true;
try { calibOn = localStorage.getItem("lisa_calib") !== "off"; } catch (e) {}
calib.style.display = "none";
document.body.appendChild(calib);
const cg = calib.getContext("2d");
const BONES = [[0, 1], [1, 2], [2, 3], [3, 4], [0, 5], [5, 6], [6, 7], [7, 8], [5, 9], [9, 10], [10, 11],
  [11, 12], [9, 13], [13, 14], [14, 15], [15, 16], [13, 17], [17, 18], [18, 19], [19, 20], [0, 17]];
function drawCalib(hands) {
  calib.style.display = calibOn && running ? "block" : "none";
  if (!calibOn) return;
  const w = 320, h = 240;
  cg.save();
  cg.translate(w, 0); cg.scale(-1, 1);                 // mirrored, like a mirror
  cg.globalAlpha = .55; cg.drawImage(video, 0, 0, w, h); cg.globalAlpha = 1;
  for (const hd of hands) {
    cg.strokeStyle = hd.gesture === "fist" ? "#5aff9a" : "#8fd8ff"; cg.lineWidth = 2;
    cg.beginPath();
    for (const [a, b] of BONES) { cg.moveTo(hd.lm[a].x * w, hd.lm[a].y * h); cg.lineTo(hd.lm[b].x * w, hd.lm[b].y * h); }
    cg.stroke();
  }
  cg.restore();
  cg.fillStyle = "rgba(3,6,12,.7)"; cg.fillRect(0, 0, w, 20 + hands.length * 34);
  cg.font = "12px Consolas, monospace"; cg.fillStyle = "#cfefff";
  cg.fillText(hands.length ? `HANDS ${hands.length}   (G hides this)` : "NO HAND IN VIEW   (G hides this)", 8, 14);
  hands.forEach((hd, i) => {
    const y = 32 + i * 34, f = hd.m.bend.map(c => c > STRAIGHT ? "|" : c < CURLED ? "o" : "/").join(" ");
    cg.fillStyle = hd.gesture === "fist" ? "#5aff9a" : "#ffffff";
    cg.fillText(`${hd.key.toUpperCase()}: ${hd.gesture.toUpperCase()}  (seeing ${hd.raw})`, 8, y);
    cg.fillStyle = "#9fd0e8";
    cg.fillText(`fingers I M R P: ${f}   pinch gap ${(hd.m.gap * 100).toFixed(1)} cm`, 8, y + 15);
  });
}

addEventListener("keydown", e => {
  const k = e.key.toLowerCase();
  if (k === "h" && !Lisa.demo) {
    if (running) { stopCamera(); HS.status = "paused"; } else start();
  }
  if (k === "g") {
    calibOn = !calibOn;
    try { localStorage.setItem("lisa_calib", calibOn ? "on" : "off"); } catch (x) {}
    if (!calibOn) calib.style.display = "none";
  }
});

// start once the settings say gestures are on (not in demo or screenshot mode)
if (!Lisa.demo) {
  fetch("/settings", { cache: "no-store" }).then(r => r.json())
    .then(s => { if (s.gestures !== false) start(); else HS.status = "off"; })
    .catch(() => start());
}
