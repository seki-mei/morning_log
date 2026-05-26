#!/usr/bin/env python3
"""
Morning routine logger.
Serves a UI at http://localhost:8787
Session persisted to ~/morning_log/session.json (auto-cleared after save)
"""

import csv
import json
from datetime import datetime, date
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

CSV_PATH     = Path.home() / "morning_log/morning_log.csv"
SESSION_PATH = Path.home() / "morning_log/session.json"
STATIC_DIR   = Path(__file__).parent
CSV_HEADERS  = ["date", "woke_up", "out_of_bed", "finished_breakfast", "destination", "notes"]
PORT         = 8787

STATIC_FILES = {
    "/":          ("index.html", "text/html; charset=utf-8"),
    "/style.css": ("style.css",  "text/css; charset=utf-8"),
    "/app.js":    ("app.js",     "application/javascript; charset=utf-8"),
}


def ensure_csv():
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not CSV_PATH.exists():
        with CSV_PATH.open("w", newline="") as f:
            csv.writer(f).writerow(CSV_HEADERS)


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
    ensure_csv()
    print(f"Morning log running → http://0.0.0.0:{PORT}")
    print(f"CSV:     {CSV_PATH}")
    print(f"Session: {SESSION_PATH}")
    print(f"Static:  {STATIC_DIR}")
    print("Ctrl-C to stop.")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
