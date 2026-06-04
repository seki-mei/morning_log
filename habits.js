'use strict';

/** @type {{ habits: Habit[], rows: Record<string, Record<string, number>> } | null} */
let state = null;

/** @type {Set<string>} */
const expandedHabits = new Set();

/**
 * @typedef {{ id: string, label: string, group: string, freq: 'daily'|'weekly', criterion: string }} Habit
 * @typedef {{ date: string, done: boolean }} DotEntry
 */

/** @returns {string} today's date as YYYY-MM-DD */
function getToday() {
    return fmtDate(new Date());
}

/** @param {Date} d @returns {string} */
function fmtDate(d) {
    return [
        d.getFullYear(),
        String(d.getMonth() + 1).padStart(2, '0'),
        String(d.getDate()).padStart(2, '0'),
    ].join('-');
}

/**
 * @param {string} dateStr YYYY-MM-DD
 * @param {number} n
 * @returns {string}
 */
function addDays(dateStr, n) {
    // T12:00:00 anchors to noon so DST transitions don't shift the date.
    const d = new Date(dateStr + 'T12:00:00');
    d.setDate(d.getDate() + n);
    return fmtDate(d);
}

/** @param {string} dateStr @returns {string} Monday of the ISO week containing dateStr */
function weekKey(dateStr) {
    const d = new Date(dateStr + 'T12:00:00');
    const dow = d.getDay();
    // Sunday (0) is -6 from Monday; Mon–Sat are 1–6, offset is 1–dow.
    d.setDate(d.getDate() + (dow === 0 ? -6 : 1 - dow));
    return fmtDate(d);
}

/**
 * @param {string} habitId
 * @param {string} mondayStr YYYY-MM-DD of the week's Monday
 * @returns {boolean}
 */
function isWeekDone(habitId, mondayStr) {
    for (let i = 0; i < 7; i++) {
        const d = addDays(mondayStr, i);
        if (state.rows[d] && state.rows[d][habitId]) return true;
    }
    return false;
}

/**
 * @param {string} habitId
 * @param {'daily'|'weekly'} freq
 * @param {string} todayStr
 * @param {number} count
 * @returns {DotEntry[]} newest first (index 0 = today/this week)
 */
function computeHistory(habitId, freq, todayStr, count) {
    return Array.from({ length: count }, (_, i) => {
        if (freq === 'daily') {
            const date = addDays(todayStr, -i);
            return { date, done: !!(state.rows[date] && state.rows[date][habitId]) };
        }
        const date = weekKey(addDays(todayStr, -i * 7));
        return { date, done: isWeekDone(habitId, date) };
    });
}

/** @param {string} habitId @param {'daily'|'weekly'} freq @param {string} today @returns {DotEntry[]} */
function computeDots(habitId, freq, today) {
    return computeHistory(habitId, freq, today, 7);
}

/** @param {string} habitId @param {'daily'|'weekly'} freq @param {string} today @returns {DotEntry[]} */
function computeBar(habitId, freq, today) {
    return computeHistory(habitId, freq, today, freq === 'daily' ? 30 : 12);
}

/**
 * @param {Habit} habit
 * @param {string} today YYYY-MM-DD
 * @returns {string} HTML string
 */
function buildHeatmapContent(habit, today) {
    const WEEKS = 26;
    const todayDate = new Date(today + 'T12:00:00');
    const mon = new Date(todayDate);
    const dow = mon.getDay();
    mon.setDate(mon.getDate() + (dow === 0 ? -6 : 1 - dow));

    const cols = [];
    for (let w = 0; w < WEEKS; w++) {
        const days = [];
        for (let d = 0; d < 7; d++) {
            const dt = new Date(mon);
            // Offset from Monday of current week: go back w weeks, then forward d days.
            dt.setDate(dt.getDate() - w * 7 + d);
            const ds = fmtDate(dt);
            const isFuture = dt > todayDate;
            days.push({ ds, done: !isFuture && !!(state.rows[ds] && state.rows[ds][habit.id]) });
        }
        cols.push(days);
    }

    let grid = '<div class="heatmap-grid">';
    for (let w = 0; w < WEEKS; w++)
        for (let d = 0; d < 7; d++) {
            const c = cols[w][d];
            grid += `<div class="heatmap-cell${c.done ? ' done' : ''}" title="${c.ds}"></div>`;
        }
    grid += '</div>';

    return `<div class="habit-inline-heatmap">${grid}</div>`;
}

/**
 * @param {Habit} habit
 * @param {string} today YYYY-MM-DD
 * @returns {string} HTML string
 */
function renderHabitRow(habit, today) {
    const { id, label, freq, criterion } = habit;
    const isOpen = expandedHabits.has(id);

    const dotsHtml = computeDots(id, freq, today).map((dot, i) => {
        const cls = ['habit-dot', i === 0 && 'today', i === 1 && 'yesterday', dot.done && 'done'].filter(Boolean).join(' ');
        // Only today (0) and yesterday (1) are interactive.
        if (i <= 1) return `<button class="${cls}" data-dot-habit="${id}" data-dot-date="${dot.date}"></button>`;
        return `<span class="${cls}"></span>`;
    }).join('');

    const barHtml = computeBar(id, freq, today)
        .map(s => `<span class="habit-bar-seg${s.done ? ' done' : ''}"></span>`)
        .join('');

    return `<div class="habit-row">
  <div class="habit-label-row">
    <button class="habit-label-toggle" data-accordion="${id}">
      <span class="habit-name">${label}</span>
    </button>
    <div class="habit-dots${freq === 'weekly' ? ' weekly' : ''}">${dotsHtml}</div>
  </div>
  <div class="habit-bar">${barHtml}</div>
  <div class="habit-accordion${isOpen ? ' open' : ''}">
    <div class="habit-criterion">${criterion}</div>
    ${isOpen ? buildHeatmapContent(habit, today) : ''}
  </div>
</div>`;
}

function render() {
    const today = getToday();

    const dt = new Date(today + 'T12:00:00');
    document.getElementById('dateLine').textContent =
        dt.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' }).toUpperCase();

    const groups = [];
    const seen = {};
    for (const h of state.habits) {
        if (!seen[h.group]) { seen[h.group] = []; groups.push([h.group, seen[h.group]]); }
        seen[h.group].push(h);
    }

    let html = '<div class="card">';
    for (const [name, habits] of groups) {
        html += `<div class="group-header">${name}</div><div class="group-divider"></div>`;
        for (const h of habits) html += renderHabitRow(h, today);
    }
    html += '</div>';

    document.getElementById('app').innerHTML = html;
    attachHandlers();
}

function attachHandlers() {
    document.querySelectorAll('[data-dot-habit]').forEach(btn => {
        btn.addEventListener('click', e => { e.stopPropagation(); toggleDot(btn.dataset.dotHabit, btn.dataset.dotDate); });
    });
    document.querySelectorAll('[data-accordion]').forEach(el => {
        el.addEventListener('click', () => toggleAccordion(el.dataset.accordion));
    });
}

/**
 * @param {string} habitId
 * @param {string} dateStr YYYY-MM-DD
 */
async function toggleDot(habitId, dateStr) {
    const btn = document.querySelector(`[data-dot-habit="${habitId}"][data-dot-date="${dateStr}"]`);
    if (btn) btn.disabled = true;
    if (!state.rows[dateStr]) state.rows[dateStr] = {};
    const newVal = state.rows[dateStr][habitId] ? 0 : 1;
    try {
        const res = await fetch('/habits_log', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ date: dateStr, habit_id: habitId, value: newVal }),
        });
        if ((await res.json()).ok) {
            state.rows[dateStr][habitId] = newVal;
            render();
        }
    } finally {
        const b = document.querySelector(`[data-dot-habit="${habitId}"][data-dot-date="${dateStr}"]`);
        if (b) b.disabled = false;
    }
}

/** @param {string} habitId */
function toggleAccordion(habitId) {
    // Snapshot the Set before iterating — deleting during for..of skips not-yet-visited entries.
    for (const openId of [...expandedHabits]) {
        if (openId === habitId) continue;
        const openToggle = document.querySelector(`[data-accordion="${openId}"]`);
        if (!openToggle) continue;
        openToggle.closest('.habit-row').querySelector('.habit-accordion').classList.remove('open');
        expandedHabits.delete(openId);
    }

    const toggle = document.querySelector(`[data-accordion="${habitId}"]`);
    const accordion = toggle.closest('.habit-row').querySelector('.habit-accordion');
    if (expandedHabits.has(habitId)) {
        expandedHabits.delete(habitId);
        accordion.classList.remove('open');
    } else {
        expandedHabits.add(habitId);
        accordion.classList.add('open');
        if (!accordion.querySelector('.habit-inline-heatmap')) {
            const habit = state.habits.find(h => h.id === habitId);
            accordion.insertAdjacentHTML('beforeend', buildHeatmapContent(habit, getToday()));
        }
    }
}

async function loadHabits() {
    document.getElementById('app').textContent = 'loading…';
    try {
        const res = await fetch('/habits_data');
        state = await res.json();
        render();
    } catch (e) {
        document.getElementById('app').textContent = `error loading habits: ${e.message}`;
    }
}

loadHabits();
