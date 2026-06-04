'use strict';

let state = null;
const expandedHabits = new Set();

function computeLogicalToday() {
    const d = new Date(Date.now() - 4 * 3600 * 1000);
    return fmtDate(d);
}

function fmtDate(d) {
    return [
        d.getFullYear(),
        String(d.getMonth() + 1).padStart(2, '0'),
        String(d.getDate()).padStart(2, '0'),
    ].join('-');
}

function addDays(dateStr, n) {
    const d = new Date(dateStr + 'T12:00:00');
    d.setDate(d.getDate() + n);
    return fmtDate(d);
}

function weekKey(dateStr) {
    const d = new Date(dateStr + 'T12:00:00');
    const dow = d.getDay();
    d.setDate(d.getDate() + (dow === 0 ? -6 : 1 - dow));
    return fmtDate(d);
}

function isWeekDone(habitId, mondayStr) {
    for (let i = 0; i < 7; i++) {
        const d = addDays(mondayStr, i);
        if (state.rows[d] && state.rows[d][habitId]) return true;
    }
    return false;
}

function computeDots(habitId, freq, today) {
    return Array.from({ length: 7 }, (_, i) => {
        if (freq === 'daily') {
            const d = addDays(today, -i);
            return { done: !!(state.rows[d] && state.rows[d][habitId]) };
        }
        return { done: isWeekDone(habitId, weekKey(addDays(today, -i * 7))) };
    });
}

function computeBar(habitId, freq, today) {
    const count = freq === 'daily' ? 30 : 12;
    return Array.from({ length: count }, (_, i) => {
        if (freq === 'daily') {
            const d = addDays(today, -i);
            return { done: !!(state.rows[d] && state.rows[d][habitId]) };
        }
        return { done: isWeekDone(habitId, weekKey(addDays(today, -i * 7))) };
    });
}


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

function renderHabitRow(habit, today) {
    const { id, label, freq, criterion } = habit;
    const isOpen = expandedHabits.has(id);
    const openCls = isOpen ? ' open' : '';

    const dotsHtml = computeDots(id, freq, today).map((dot, i) => {
        const cls = ['habit-dot', i === 0 && 'today', dot.done && 'done'].filter(Boolean).join(' ');
        if (i === 0) return `<button class="${cls}" data-today-dot="${id}"></button>`;
        return `<span class="${cls}"></span>`;
    }).join('');

    const barHtml = computeBar(id, freq, today)
        .map(s => `<span class="habit-bar-seg${s.done ? ' done' : ''}"></span>`)
        .join('');

    return `<div class="habit-row">
  <div class="habit-label-row">
    <button class="habit-label-toggle" data-accordion="${id}">
      <span class="habit-caret${openCls}">▶</span>
      <span class="habit-name">${label}</span>
    </button>
    <div class="habit-dots${freq === 'weekly' ? ' weekly' : ''}">${dotsHtml}</div>
  </div>
  <div class="habit-bar">${barHtml}</div>
  <div class="habit-accordion${openCls}">
    <div class="habit-criterion">${criterion}</div>
    ${isOpen ? buildHeatmapContent(habit, today) : ''}
  </div>
</div>`;
}

function render() {
    const today = computeLogicalToday();

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
    document.querySelectorAll('[data-today-dot]').forEach(dot => {
        dot.addEventListener('click', e => { e.stopPropagation(); toggleToday(dot.dataset.todayDot); });
    });
    document.querySelectorAll('[data-accordion]').forEach(el => {
        el.addEventListener('click', () => toggleAccordion(el.dataset.accordion));
    });
}

async function toggleToday(habitId) {
    const today = computeLogicalToday();
    if (!state.rows[today]) state.rows[today] = {};
    const newVal = state.rows[today][habitId] ? 0 : 1;
    const res = await fetch('/habits_log', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ date: today, habit_id: habitId, value: newVal }),
    });
    if ((await res.json()).ok) {
        state.rows[today][habitId] = newVal;
        render();
    }
}

function toggleAccordion(habitId) {
    // Close any currently open accordion
    for (const openId of expandedHabits) {
        if (openId === habitId) continue;
        const openToggle = document.querySelector(`[data-accordion="${openId}"]`);
        if (!openToggle) continue;
        const openRow = openToggle.closest('.habit-row');
        openRow.querySelector('.habit-caret').classList.remove('open');
        openRow.querySelector('.habit-accordion').classList.remove('open');
        expandedHabits.delete(openId);
    }

    const toggle = document.querySelector(`[data-accordion="${habitId}"]`);
    const habitRow = toggle.closest('.habit-row');
    const accordion = habitRow.querySelector('.habit-accordion');
    if (expandedHabits.has(habitId)) {
        expandedHabits.delete(habitId);
        habitRow.querySelector('.habit-caret').classList.remove('open');
        accordion.classList.remove('open');
    } else {
        expandedHabits.add(habitId);
        habitRow.querySelector('.habit-caret').classList.add('open');
        accordion.classList.add('open');
        if (!accordion.querySelector('.habit-inline-heatmap')) {
            const habit = state.habits.find(h => h.id === habitId);
            accordion.insertAdjacentHTML('beforeend', buildHeatmapContent(habit, computeLogicalToday()));
        }
    }
}

async function loadHabits() {
    const res = await fetch('/habits_data');
    state = await res.json();
    render();
}

loadHabits();
