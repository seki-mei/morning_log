#!/usr/bin/env python3
"""
Morning routine logger.
Serves a UI at http://localhost:8787
Session persisted to ~/morning_session.json (auto-cleared after save)
"""

import csv
import json
import os
from datetime import datetime, date, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

CSV_PATH = os.path.expanduser("~/morning_log/morning_log.csv")
SESSION_PATH = os.path.expanduser("~/morning_log/session.json")
CSV_HEADERS = ["date", "woke_up", "out_of_bed", "finished_breakfast", "destination", "notes"]
PORT = 8787

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<title>Morning Log</title>
<link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;700&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
<style>
  :root {
    --gvb-bg:       #282828;
    --gvb-red:      #cc241d;
    --gvb-green:    #98971a;
    --gvb-yellow:   #d79921;
    --gvb-blue:     #458588;
    --gvb-purple:   #b16286;
    --gvb-aqua:     #689d6a;
    --gvb-gray:     #a89984;
    --gvb-gray2:    #928374;
    --gvb-red2:     #fb4934;
    --gvb-green2:   #b8bb26;
    --gvb-yellow2:  #fabd2f;
    --gvb-blue2:    #83a598;
    --gvb-purple2:  #d3869b;
    --gvb-aqua2:    #8ec07c;
    --gvb-fg:       #ebdbb2;
    --gvb-bg0_h:    #1d2021;
    --gvb-bg0:      #282828;
    --gvb-bg1:      #3c3836;
    --gvb-bg2:      #504945;
    --gvb-bg3:      #665c54;
    --gvb-bg4:      #7c6f64;
    --gvb-orange:   #d65d0e;
    --gvb-bg0_s:    #32302f;
    --gvb-fg4:      #a89984;
    --gvb-fg3:      #bdae93;
    --gvb-fg2:      #d5c4a1;
    --gvb-fg1:      #ebdbb2;
    --gvb-fg0:      #fbf1c7;
    --gvb-orange2:  #fe8019;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    background: var(--gvb-bg0);
    color: var(--gvb-fg1);
    font-family: 'JetBrains Mono', monospace;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 1.5rem 1rem 4rem;
  }

  header {
    width: 100%;
    max-width: 440px;
    margin-bottom: 1.5rem;
    text-align: center;
  }

  h1 {
    font-family: 'Rajdhani', sans-serif;
    font-weight: 700;
    font-size: 1.6rem;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--gvb-fg2);
  }

  .date-line {
    font-size: 0.68rem;
    color: var(--gvb-fg4);
    margin-top: 0.25rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
  }

  /* ── Step tracker ── */
  .step-track {
    width: 100%;
    max-width: 440px;
    display: flex;
    align-items: stretch;
    margin-bottom: 1.5rem;
    gap: 0;
  }

  .step-node {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    position: relative;
  }

  /* connecting lines */
  .step-node:not(:last-child)::after {
    content: '';
    position: absolute;
    top: 1.05rem;
    left: 50%;
    width: 100%;
    height: 2px;
    background: var(--gvb-bg3);
    z-index: 0;
  }

  .step-node.done:not(:last-child)::after {
    background: var(--gvb-green);
  }

  .step-dot {
    width: 2.1rem;
    height: 2.1rem;
    border-radius: 50%;
    border: 2px solid var(--gvb-bg3);
    background: var(--gvb-bg1);
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: 'Rajdhani', sans-serif;
    font-weight: 700;
    font-size: 0.9rem;
    color: var(--gvb-fg4);
    position: relative;
    z-index: 1;
    transition: all 0.15s;
  }

  .step-node.done .step-dot {
    background: var(--gvb-green);
    border-color: var(--gvb-green2);
    color: var(--gvb-bg0);
  }

  .step-node.active .step-dot {
    background: var(--gvb-aqua);
    border-color: var(--gvb-aqua2);
    color: var(--gvb-bg0);
    box-shadow: 0 0 0 3px rgba(104,157,106,0.22);
  }

  .step-name {
    margin-top: 0.4rem;
    font-size: 0.58rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--gvb-fg4);
    text-align: center;
    line-height: 1.3;
  }

  .step-node.active .step-name { color: var(--gvb-aqua2); }
  .step-node.done .step-name  { color: var(--gvb-green2); }

  .step-time {
    font-size: 0.65rem;
    color: var(--gvb-aqua2);
    margin-top: 0.15rem;
    font-family: 'JetBrains Mono', monospace;
    text-align: center;
  }

  .step-seg {
    position: absolute;
    top: 0.05rem;
    left: 50%;
    width: 100%;
    display: flex;
    justify-content: center;
    align-items: center;
    pointer-events: none;
    z-index: 2;
  }

  .step-seg span {
    font-size: 0.52rem;
    font-family: 'JetBrains Mono', monospace;
    color: var(--gvb-fg4);
    background: var(--gvb-bg0);
    padding: 0 0.25rem;
    white-space: nowrap;
  }

  /* ── Main card ── */
  .card {
    width: 100%;
    max-width: 440px;
    background: var(--gvb-bg1);
    border: 1px solid var(--gvb-bg3);
    border-radius: 3px;
    padding: 1.5rem 1.3rem;
    margin-bottom: 1rem;
  }

  .current-step-header {
    display: flex;
    align-items: center;
    gap: 0.7rem;
    margin-bottom: 1.3rem;
  }

  .step-number-big {
    font-family: 'Rajdhani', sans-serif;
    font-weight: 700;
    font-size: 3rem;
    line-height: 1;
    color: var(--gvb-fg2);
    min-width: 2rem;
  }

  .step-text {
    display: flex;
    flex-direction: column;
  }

  .step-text .label {
    font-size: 0.6rem;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: var(--gvb-fg4);
    margin-bottom: 0.15rem;
  }

  .step-text .title {
    font-family: 'Rajdhani', sans-serif;
    font-weight: 700;
    font-size: 1.5rem;
    letter-spacing: 0.04em;
    color: var(--gvb-fg0);
    line-height: 1.1;
  }

  .logged-times {
    display: flex;
    flex-direction: column;
    gap: 0;
    margin-bottom: 1.3rem;
    border: 1px solid var(--gvb-bg2);
    border-radius: 2px;
    overflow: hidden;
  }

  .time-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.45rem 0.7rem;
    font-size: 0.78rem;
    background: var(--gvb-bg0_s);
    border-bottom: 1px solid var(--gvb-bg2);
  }

  .time-row:last-child { border-bottom: none; }
  .time-row .label { color: var(--gvb-fg4); flex-shrink: 1; min-width: 0; margin-right: 0.6rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .time-row .val { color: var(--gvb-fg4); font-weight: 400; flex-shrink: 0; white-space: nowrap; font-size: 0.72rem; }
  .time-row .dur { font-size: 0.68rem; color: var(--gvb-fg4); margin-left: 0.4rem; }

  .dur-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.45rem 0.7rem;
    font-size: 0.78rem;
    font-family: 'JetBrains Mono', monospace;
    color: var(--gvb-fg4);
    border-bottom: 1px solid var(--gvb-bg2);
    letter-spacing: 0.04em;
    font-weight: 500;
  }
  .dur-row span:last-child { color: var(--gvb-fg1); }
  .dur-row:last-child { border-bottom: none; }
  .logged-times > div:nth-child(odd)  { background: var(--gvb-bg0_s); }
  .logged-times > div:nth-child(even) { background: var(--gvb-bg1); }

  .restored-badge {
    font-size: 0.6rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--gvb-aqua2);
    margin-bottom: 1rem;
    padding: 0.25rem 0.5rem;
    border: 1px solid var(--gvb-aqua);
    border-radius: 2px;
    display: inline-block;
  }

  .big-btn {
    width: 100%;
    padding: 1rem;
    font-family: 'Rajdhani', sans-serif;
    font-weight: 700;
    font-size: 1.15rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    border: 1px solid var(--gvb-fg2);
    border-radius: 2px;
    background: var(--gvb-bg2);
    color: var(--gvb-fg1);
    cursor: pointer;
    transition: filter 0.08s, transform 0.08s;
    -webkit-tap-highlight-color: transparent;
  }

  .big-btn:active {
    filter: brightness(0.90);
    transform: translateY(4px);
  }

  .big-btn:disabled {
    opacity: 0.3;
    cursor: not-allowed;
    transform: none;
  }

  .dest-btns {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.7rem;
    margin-bottom: 1.1rem;
  }

  .dest-btn {
    padding: 0.9rem 0.5rem;
    font-family: 'Rajdhani', sans-serif;
    font-weight: 700;
    font-size: 1rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    border: 1px solid var(--gvb-bg3);
    border-radius: 2px;
    background: var(--gvb-bg2);
    color: var(--gvb-fg3);
    cursor: pointer;
    transition: all 0.1s;
    -webkit-tap-highlight-color: transparent;
  }

  .dest-btn.selected, .dest-btn:active {
    background: var(--gvb-aqua);
    border-color: var(--gvb-aqua2);
    color: var(--gvb-bg0);
  }

  .dest-label {
    font-size: 0.6rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--gvb-fg4);
    margin-bottom: 0.5rem;
  }

  .notes-row { margin-bottom: 1.1rem; }

  .notes-row label {
    display: block;
    font-size: 0.6rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--gvb-fg4);
    margin-bottom: 0.35rem;
  }

  .notes-row input {
    width: 100%;
    padding: 0.5rem 0.65rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    background: var(--gvb-bg0_s);
    border: 1px solid var(--gvb-bg3);
    border-radius: 2px;
    color: var(--gvb-fg1);
    outline: none;
  }

  .notes-row input:focus { border-color: var(--gvb-blue2); }

  .danger-zone {
    width: 100%;
    max-width: 440px;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .ghost-btn {
    width: 100%;
    padding: 0.65rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    letter-spacing: 0.04em;
    border: 1px solid var(--gvb-bg3);
    border-radius: 2px;
    background: transparent;
    color: var(--gvb-fg4);
    cursor: pointer;
    -webkit-tap-highlight-color: transparent;
  }

  .ghost-btn.red { border-color: var(--gvb-red); color: var(--gvb-red2); }
  .ghost-btn:active { opacity: 0.6; }

  .success-card {
    text-align: center;
    padding: 2rem 1.3rem;
  }

  .success-icon { font-size: 2.2rem; margin-bottom: 0.6rem; }

  .success-card h2 {
    font-family: 'Rajdhani', sans-serif;
    font-weight: 700;
    font-size: 1.8rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--gvb-green2);
    margin-bottom: 0.8rem;
  }

  .success-card p {
    font-size: 0.75rem;
    color: var(--gvb-fg4);
    line-height: 1.9;
  }

  .toast {
    position: fixed;
    bottom: 1.5rem;
    left: 50%;
    transform: translateX(-50%) translateY(4rem);
    background: var(--gvb-bg2);
    color: var(--gvb-fg1);
    border: 1px solid var(--gvb-bg4);
    padding: 0.6rem 1.2rem;
    border-radius: 2px;
    font-size: 0.75rem;
    transition: transform 0.25s ease;
    z-index: 100;
    white-space: nowrap;
  }

  .toast.show { transform: translateX(-50%) translateY(0); }
  .toast.error { background: var(--gvb-red); border-color: var(--gvb-red2); color: var(--gvb-fg0); }

  .clock-wrap {
    text-align: center;
    margin-bottom: 1.2rem;
    padding: 0.7rem 0;
    border-top: 1px solid var(--gvb-bg2);
    border-bottom: 1px solid var(--gvb-bg2);
  }

  .clock-label {
    font-size: 0.58rem;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: var(--gvb-fg4);
    margin-bottom: 0.2rem;
  }

  .clock-display {
    font-family: 'Rajdhani', sans-serif;
    font-weight: 700;
    font-size: 2.8rem;
    line-height: 1;
    color: var(--gvb-fg1);
    letter-spacing: 0.06em;
  }

  .clock-display.warn { color: var(--gvb-red2); }
</style>
</head>
<body>

<header>
  <h1>Morning Log</h1>
  <div class="date-line" id="dateLine"></div>
</header>

<div class="step-track" id="stepTrack"></div>
<div id="app"></div>
<div class="danger-zone" id="dangerZone"></div>
<div class="toast" id="toast"></div>

<script>
const STEP_LABELS = ['Woke up', 'Out of bed', 'Ended breakfast'];
const STEP_ICONS  = ['⏰', '🛏', '🍳'];
const STEP_NAMES  = ['Start', 'In bed', 'Breakfast'];
const DESTINATIONS = ['Desk', 'Front door'];

let state = {
  times: [],
  destination: null,
  notes: '',
  done: false,
  restored: false,
};

function fmt(iso) {
  return new Date(iso).toTimeString().slice(0,8);
}

function delta(a, b) {
  const m = Math.round((new Date(b) - new Date(a)) / 60000);
  return m === 0 ? '<1m' : m + 'm';
}

function fmtDur(ms) {
  const totalSecs = Math.floor(ms / 1000);
  const h = Math.floor(totalSecs / 3600);
  const m = Math.floor((totalSecs % 3600) / 60);
  const s = totalSecs % 60;
  return String(h) + ':' + String(m).padStart(2,'0') + ':' + String(s).padStart(2,'0');
}

function renderTrack() {
  const track = document.getElementById('stepTrack');
  if (state.done) { track.innerHTML = ''; return; }
  const step = state.times.length;
  track.innerHTML = STEP_NAMES.map((name, i) => {
    const cls = i < step ? 'done' : i === step ? 'active' : '';
    const check = i < step ? '✓' : (i + 1).toString();
    return `<div class="step-node ${cls}">
      <div class="step-dot">${check}</div>
      <div class="step-name">${name}</div>
    </div>`;
  }).join('');
}

function render() {
  const app = document.getElementById('app');
  const danger = document.getElementById('dangerZone');

  renderTrack();

  if (state.done) {
    const DUR_LABELS_S = ['in bed', 'breakfasting'];
    app.innerHTML = `
      <div class="card success-card">
        <div class="success-icon">📊</div>
        <h2>Logged</h2>
        <div class="logged-times">
          <div class="time-row"><span class="label">${STEP_LABELS[0]}</span><span class="val">${fmt(state.times[0])}</span></div>
          <div class="dur-row"><span>${DUR_LABELS_S[0]}</span><span>${fmtDur(new Date(state.times[1]) - new Date(state.times[0]))}</span></div>
          <div class="time-row"><span class="label">${STEP_LABELS[1]}</span><span class="val">${fmt(state.times[1])}</span></div>
          <div class="dur-row"><span>${DUR_LABELS_S[1]}</span><span>${fmtDur(new Date(state.times[2]) - new Date(state.times[1]))}</span></div>
          <div class="time-row"><span class="label">${STEP_LABELS[2]}</span><span class="val">${fmt(state.times[2])}</span></div>
          <div class="dur-row"><span>Σ</span><span>${fmtDur(new Date(state.times[2]) - new Date(state.times[0]))}</span></div>
          <div class="time-row"><span class="label">→</span><span class="val">${state.destination}</span></div>
          ${state.notes ? `<div class="time-row"><span class="label">notes</span><span class="val">${state.notes}</span></div>` : ''}
        </div>
      </div>`;
    danger.innerHTML = `<button class="ghost-btn red" onclick="resetAll()">Start from scratch</button>`;
    return;
  }

  const step = state.times.length;
  const isLastStep = step === 2;

  const DUR_LABELS = ['in bed', 'breakfasting'];
  let timesRows = '';
  for (let i = 0; i < 3; i++) {
    const t = state.times[i];
    timesRows += `<div class="time-row">
      <span class="label">${STEP_LABELS[i]}</span>
      <span class="val">${t ? fmt(t) : '--:--:--'}</span>
    </div>`;
    if (i < 2) {
      let durContent;
      if (state.times[i] && state.times[i + 1]) {
        durContent = fmtDur(new Date(state.times[i+1]) - new Date(state.times[i]));
      } else if (state.times[i] && !state.times[i + 1] && i === step - 1) {
        durContent = `<span id="cardLiveDur">0:00:00</span>`;
      } else {
        durContent = '--:--:--';
      }
      timesRows += `<div class="dur-row"><span>${DUR_LABELS[i]}</span><span>${durContent}</span></div>`;
    }
  }
  let totalContent;
  if (state.times[0] && state.times[2]) {
    totalContent = fmtDur(new Date(state.times[2]) - new Date(state.times[0]));
  } else if (state.times[0] && !state.times[2]) {
    totalContent = `<span id="totalLiveDur">0:00:00</span>`;
  } else {
    totalContent = '--:--:--';
  }
  timesRows += `<div class="dur-row"><span>Σ</span><span>${totalContent}</span></div>`;
  const timesHtml = `<div class="logged-times">${timesRows}</div>`;

  const restoredBadge = state.restored
    ? `<div class="restored-badge">↺ session restored</div>` : '';

  let destHtml = '';
  let notesHtml = '';
  let btnLabel = '';

  if (!isLastStep) {
    btnLabel = step === 0 ? 'JUST WOKE UP' : 'NOW OUT OF BED';
  } else {
    destHtml = `
      <div class="dest-label">Where to next?</div>
      <div class="dest-btns">
        ${DESTINATIONS.map(d => `
          <button class="dest-btn ${state.destination === d ? 'selected' : ''}"
            onclick="pickDest('${d}')">${d}</button>
        `).join('')}
      </div>`;
    notesHtml = `
      <div class="notes-row">
        <label>Notes (optional)</label>
        <input type="text" placeholder="anything unusual..." value="${state.notes}"
          oninput="state.notes=this.value">
      </div>`;
    btnLabel = 'ENDED BREAKFAST';
  }

  const btnDisabled = isLastStep && !state.destination ? 'disabled' : '';

  const clockHtml = step >= 1
    ? `<div class="clock-wrap">
        <div class="clock-label">${step === 1 ? 'time since waking' : 'time since out of bed'}</div>
        <div class="clock-display" id="clockDisplay">0:00</div>
       </div>`
    : '';

  app.innerHTML = `
    <div class="card">
      ${restoredBadge}
      ${timesHtml}
      ${clockHtml}
      ${destHtml}
      ${notesHtml}
      <div class="current-step-header">
        <div class="step-number-big">${STEP_ICONS[step]}</div>
        <div class="step-text">
          <div class="label">Step ${step + 1} of 3</div>
          <div class="title">${isLastStep ? 'Breakfast done?' : STEP_LABELS[step]}</div>
        </div>
      </div>
      <button class="big-btn" onclick="logStep()" ${btnDisabled}>${btnLabel}</button>
    </div>`;

  startClock();

  danger.innerHTML = step > 0
    ? `<button class="ghost-btn red" onclick="resetAll()">↺ Went back to sleep — start over</button>`
    : '';
}

let clockInterval = null;

function startClock() {
  if (clockInterval) clearInterval(clockInterval);
  const step = state.times.length;
  if (step < 1 || state.done) return;
  const since = new Date(state.times[step - 1]);
  function tick() {
    const el = document.getElementById('clockDisplay');
    if (!el) { clearInterval(clockInterval); return; }
    const ms = Date.now() - since;
    const secs = Math.floor(ms / 1000);
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    el.textContent = `${m}:${String(s).padStart(2,'0')}`;
    el.className = 'clock-display' + (m >= 30 ? ' warn' : '');
    const durEl = document.getElementById('stepLiveDur');
    if (durEl) durEl.textContent = fmtDur(ms);
    const cardDurEl = document.getElementById('cardLiveDur');
    if (cardDurEl) cardDurEl.textContent = fmtDur(ms);
    const totalDurEl = document.getElementById('totalLiveDur');
    if (totalDurEl) {
      const totalMs = Date.now() - new Date(state.times[0]);
      totalDurEl.textContent = fmtDur(totalMs);
    }
  }
  tick();
  clockInterval = setInterval(tick, 1000);
}

async function logStep() {
  const now = new Date().toISOString();
  if (state.times.length < 2) {
    state.times.push(now);
    state.restored = false;
    await persistSession();
    render();
  } else {
    state.times.push(now);
    await saveRow();
  }
}

function pickDest(d) {
  state.destination = d;
  render();
}

async function resetAll() {
  if (clockInterval) { clearInterval(clockInterval); clockInterval = null; }
  state = { times: [], destination: null, notes: '', done: false, restored: false };
  await fetch('/session', { method: 'DELETE' });
  render();
}

function showToast(msg, isError) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast show' + (isError ? ' error' : '');
  setTimeout(() => t.className = 'toast', 2800);
}

async function persistSession() {
  await fetch('/session', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ times: state.times, destination: state.destination, notes: state.notes }),
  });
}

async function saveRow() {
  const payload = {
    woke_up: state.times[0],
    out_of_bed: state.times[1],
    finished_breakfast: state.times[2],
    destination: state.destination,
    notes: state.notes,
  };
  try {
    const r = await fetch('/log', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const j = await r.json();
    if (j.ok) {
      state.done = true;
      render();
      showToast('Saved ✓');
    } else {
      showToast('Save failed: ' + j.error, true);
      state.times.pop();
      render();
    }
  } catch(e) {
    showToast('Could not reach server', true);
    state.times.pop();
    render();
  }
}

async function loadSession() {
  try {
    const r = await fetch('/session');
    const j = await r.json();
    if (j.times && j.times.length > 0) {
      state.times = j.times;
      state.destination = j.destination || null;
      state.notes = j.notes || '';
      state.restored = true;
    }
  } catch(e) { /* fresh start */ }
  render();
}

document.getElementById('dateLine').textContent =
  new Date().toLocaleDateString('en-GB', { weekday:'long', day:'numeric', month:'long', year:'numeric' });

loadSession();
</script>
</body>
</html>
"""


def ensure_csv():
    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, "w", newline="") as f:
            csv.writer(f).writerow(CSV_HEADERS)


def load_session():
    try:
        with open(SESSION_PATH) as f:
            data = json.load(f)
        if data.get("date") != str(date.today()):
            return {}
        return data
    except Exception:
        return {}


def save_session(data: dict):
    data["date"] = str(date.today())
    with open(SESSION_PATH, "w") as f:
        json.dump(data, f)


def delete_session():
    try:
        os.remove(SESSION_PATH)
    except FileNotFoundError:
        pass


def append_row(data: dict):
    def parse_local(iso):
        return datetime.fromisoformat(iso).astimezone()  # converts to system local tz

    def hhmm(iso):
        return parse_local(iso).strftime("%H:%M")

    woke_local = parse_local(data["woke_up"])
    row = [
            woke_local.strftime("%Y-%m-%d"),   # ← now uses local date
            woke_local.strftime("%H:%M"),
            hhmm(data["out_of_bed"]),
            hhmm(data["finished_breakfast"]),
            data.get("destination", ""),
            data.get("notes", ""),
            ]
    with open(CSV_PATH, "a", newline="") as f:
        csv.writer(f).writerow(row)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        if self.path == "/session":
            body = json.dumps(load_session()).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML.encode())

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            data = json.loads(body)
        except Exception as e:
            self._json(500, {"ok": False, "error": str(e)})
            return

        if self.path == "/session":
            save_session(data)
            self._json(200, {"ok": True})
        elif self.path == "/log":
            try:
                append_row(data)
                delete_session()
                self._json(200, {"ok": True})
            except Exception as e:
                self._json(500, {"ok": False, "error": str(e)})
        else:
            self._json(404, {"ok": False, "error": "not found"})

    def do_DELETE(self):
        if self.path == "/session":
            delete_session()
            self._json(200, {"ok": True})
        else:
            self._json(404, {"ok": False, "error": "not found"})

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    ensure_csv()
    print(f"Morning log running → http://0.0.0.0:{PORT}")
    print(f"CSV:     {CSV_PATH}")
    print(f"Session: {SESSION_PATH}")
    print("Ctrl-C to stop.")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
