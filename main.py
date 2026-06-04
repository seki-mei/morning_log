#!/usr/bin/env python3
"""
Morning routine logger + habit tracker.
Serves UI at http://localhost:8787
"""

import csv
import json
from datetime import datetime, date, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from habits_config import HABITS as DEFAULT_HABITS

DATA_DIR     = Path.home() / ".local/share/personal_logs"
CSV_PATH     = DATA_DIR / "morning_log.csv"
HABITS_CSV   = DATA_DIR / "habits.csv"
HABITS_JSON  = DATA_DIR / "habits.json"
SESSION_PATH = DATA_DIR / "session.json"


def _load_habits():
    if HABITS_JSON.exists():
        try:
            return json.loads(HABITS_JSON.read_text())
        except Exception:
            pass
    return list(DEFAULT_HABITS)


HABITS = _load_habits()
STATIC_DIR   = Path(__file__).parent
CSV_HEADERS  = ["date", "woke_up", "out_of_bed", "finished_breakfast", "destination", "notes"]
PORT         = 8787

STATIC_FILES = {
    "/":          ("habits.html",  "text/html; charset=utf-8"),
    "/morning":   ("morning.html", "text/html; charset=utf-8"),
    "/style.css": ("style.css",    "text/css; charset=utf-8"),
    "/app.js":    ("app.js",       "application/javascript; charset=utf-8"),
    "/habits.js": ("habits.js",    "application/javascript; charset=utf-8"),
}


def logical_today():
    return (datetime.now() - timedelta(hours=4)).date()


def ensure_habits_json():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not HABITS_JSON.exists():
        HABITS_JSON.write_text(json.dumps(DEFAULT_HABITS, indent=2))


def ensure_csv():
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not CSV_PATH.exists():
        with CSV_PATH.open("w", newline="") as f:
            csv.writer(f).writerow(CSV_HEADERS)


def ensure_habits_csv():
    HABITS_CSV.parent.mkdir(parents=True, exist_ok=True)
    all_ids = ["date"] + [h["id"] for h in HABITS]

    if not HABITS_CSV.exists():
        with HABITS_CSV.open("w", newline="") as f:
            csv.writer(f).writerow(all_ids)
        return

    with HABITS_CSV.open("r", newline="") as f:
        reader = csv.DictReader(f)
        existing_fields = list(reader.fieldnames or [])
        rows = list(reader)

    new_ids = [h_id for h_id in all_ids if h_id not in existing_fields]
    if not new_ids:
        return

    updated_fields = existing_fields + new_ids
    for row in rows:
        for h_id in new_ids:
            row[h_id] = ""

    with HABITS_CSV.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=updated_fields)
        writer.writeheader()
        writer.writerows(rows)


def load_habits_rows(days=84):
    cutoff = str(logical_today() - timedelta(days=days - 1))
    rows = {}
    if not HABITS_CSV.exists():
        return rows
    with HABITS_CSV.open("r", newline="") as f:
        for row in csv.DictReader(f):
            d = row.get("date", "")
            if d >= cutoff:
                rows[d] = {k: (1 if v == "1" else 0) for k, v in row.items() if k != "date"}
    return rows


def habits_data():
    active = [
        {k: h[k] for k in ("id", "label", "group", "freq", "criterion")}
        for h in HABITS if not h.get("retired", False)
    ]
    return {"habits": active, "rows": load_habits_rows()}


def log_habit(date_str: str, habit_id: str, value: int):
    ensure_habits_csv()
    rows = {}

    with HABITS_CSV.open("r", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        for row in reader:
            rows[row["date"]] = dict(row)

    if date_str not in rows:
        rows[date_str] = {"date": date_str, **{f: "" for f in fieldnames if f != "date"}}

    rows[date_str][habit_id] = "1" if value == 1 else ""

    with HABITS_CSV.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for d in sorted(rows):
            writer.writerow(rows[d])


def load_session():
    try:
        data = json.loads(SESSION_PATH.read_text())
        if data.get("date") != str(date.today()):
            return {}
        return data
    except Exception:
        return {}


def save_session(data: dict):
    SESSION_PATH.write_text(json.dumps({**data, "date": str(date.today())}))


def delete_session():
    SESSION_PATH.unlink(missing_ok=True)


def hhmm(iso: str) -> str:
    return datetime.fromisoformat(iso).strftime("%H:%M")


def append_row(data: dict):
    woke = datetime.fromisoformat(data["woke_up"])
    row = [
        woke.strftime("%Y-%m-%d"),
        woke.strftime("%H:%M"),
        hhmm(data["out_of_bed"]),
        hhmm(data["finished_breakfast"]),
        data.get("destination", ""),
        data.get("notes", ""),
    ]
    with CSV_PATH.open("a", newline="") as f:
        csv.writer(f).writerow(row)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        if self.path == "/session":
            self._respond(200, "application/json", json.dumps(load_session()).encode())
            return

        if self.path == "/habits_data":
            self._respond(200, "application/json", json.dumps(habits_data()).encode())
            return

        if self.path in STATIC_FILES:
            filename, content_type = STATIC_FILES[self.path]
            try:
                self._respond(200, content_type, (STATIC_DIR / filename).read_bytes())
            except FileNotFoundError:
                self._json(404, {"ok": False, "error": f"{filename} not found"})
            return

        self._json(404, {"ok": False, "error": "not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        try:
            data = json.loads(self.rfile.read(length))
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
        elif self.path == "/habits_log":
            try:
                log_habit(data["date"], data["habit_id"], int(data["value"]))
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

    def _respond(self, code: int, content_type: str, body: bytes):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, obj: dict):
        self._respond(code, "application/json", json.dumps(obj).encode())


if __name__ == "__main__":
    ensure_habits_json()
    ensure_csv()
    ensure_habits_csv()
    print(f"Habits  → http://localhost:{PORT}/")
    print(f"Morning → http://localhost:{PORT}/morning")
    print(f"Data:    {DATA_DIR}")
    print(f"Session: {SESSION_PATH}")
    print(f"Static:  {STATIC_DIR}")
    print("Ctrl-C to stop.")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
