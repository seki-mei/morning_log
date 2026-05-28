const STEP_LABELS  = ['Woke up', 'Out of bed', 'Ended breakfast'];
const STEP_ICONS   = ['⏰', '🛏', '🥞', '📊'];
const DESTINATIONS = ['Desk', 'Front door'];
const DUR_LABELS   = ['bed', 'breakfast'];

let state = {
	times: [],
	destination: null,
	notes: '',
	done: false,
};

function fmt(iso) {
	return new Date(iso).toTimeString().slice(0, 8);
}

function fmtDur(ms) {
	const totalSecs = Math.floor(ms / 1000);
	const h = Math.floor(totalSecs / 3600);
	const m = Math.floor((totalSecs % 3600) / 60);
	const s = totalSecs % 60;
	return String(h) + ':' + String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0');
}

function localISO() {
	const d = new Date();
	const off = -d.getTimezoneOffset();
	const sign = off >= 0 ? '+' : '-';
	const pad = n => String(Math.floor(Math.abs(n))).padStart(2, '0');
	return new Date(d - d.getTimezoneOffset() * 60000).toISOString().slice(0, -1)
		+ sign + pad(off / 60) + ':' + pad(off % 60);
}

function render() {
	const app = document.getElementById('app');
	const danger = document.getElementById('dangerZone');

	const step = state.times.length;
	const isLastStep = step === 2;

	// build times table (shared by in-progress and done views)
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
				durContent = fmtDur(new Date(state.times[i + 1]) - new Date(state.times[i]));
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
	if (state.done) {
		timesRows += `<div class="time-row"><span class="label">→</span><span class="val">${state.destination}</span></div>`;
		if (state.notes) timesRows += `<div class="time-row"><span class="label">notes</span><span class="val">${state.notes}</span></div>`;
	}
	const timesHtml = `<div class="logged-times">${timesRows}</div>`;

	const btnLabel = step === 0 ? 'JUST WOKE UP' : step === 1 ? 'NOW OUT OF BED' : 'ENDED BREAKFAST';
	const btnDisabled = isLastStep && !state.destination ? 'disabled' : '';
	const clockLabel = step === 1 ? 'time since waking' : 'time since out of bed';

	const activeHtml = state.done ? '' : `
				<div class="clock-wrap">
							<div class="clock-label">${clockLabel}</div>
										<div class="clock-display" id="clockDisplay">0:00</div>
												</div>
														<div class="dest-label">Where to next?</div>
																<div class="dest-btns">
																			${DESTINATIONS.map(d => `
																							<button class="dest-btn ${state.destination === d ? 'selected' : ''}"
																												onclick="pickDest('${d}')">${d}</button>
																															`).join('')}
																																	</div>
																																			<div class="notes-row">
																																						<label>Notes (optional)</label>
																																									<input type="text" placeholder="anything unusual..." value="${state.notes}"
																																													oninput="state.notes=this.value">
																																															</div>
																																																	<button class="big-btn" onclick="logStep()" ${btnDisabled}>${btnLabel}</button>
																																																		`;

	app.innerHTML = `
				<div class="card">
							<div class="current-step-header">
											<div class="step-number-big">${STEP_ICONS[step]}</div>
														</div>
																			${timesHtml}
																						${activeHtml}
																								</div>`;

	startClock();

	if (state.done) {
		danger.innerHTML = `<button class="ghost-btn red" onclick="resetAll()">Start from scratch</button>`;
	} else {
		danger.innerHTML = step > 0
			? `<button class="ghost-btn red" onclick="resetAll()">↺ Went back to sleep — start over</button>`
			: '';
	}
}

let clockInterval = null;

function startClock() {
	if (clockInterval) { clearInterval(clockInterval); }
	const step = state.times.length;
	if (step < 1 || state.done) { return; }
	const since = new Date(state.times[step - 1]);
	function tick() {
		const el = document.getElementById('clockDisplay');
		if (!el) { clearInterval(clockInterval); return; }
		const ms = Date.now() - since;
		const secs = Math.floor(ms / 1000);
		const m = Math.floor(secs / 60);
		const s = secs % 60;
		el.textContent = `${m}:${String(s).padStart(2, '0')}`;
		const cardDurEl = document.getElementById('cardLiveDur');
		if (cardDurEl) { cardDurEl.textContent = fmtDur(ms); }
		const totalDurEl = document.getElementById('totalLiveDur');
		if (totalDurEl) { totalDurEl.textContent = fmtDur(Date.now() - new Date(state.times[0])); }
	}
	tick();
	clockInterval = setInterval(tick, 1000);
}

async function logStep() {
	const now = localISO();
	if (state.times.length < 2) {
		state.times.push(now);
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
	state = { times: [], destination: null, notes: '', done: false };
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
		woke_up:            state.times[0],
		out_of_bed:         state.times[1],
		finished_breakfast: state.times[2],
		destination:        state.destination,
		notes:              state.notes,
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
		}
	} catch(e) { /* fresh start */ }
	render();
}

document.getElementById('dateLine').textContent =
	new Date().toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });

loadSession();

