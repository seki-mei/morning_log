#!/usr/bin/env python3
"""
Morning routine logger.
Serves a UI at http://localhost:8787
Session persisted to ~/morning_session.json (auto-cleared after save)
"""

import csv
import json
import mimetypes
import os
from datetime import datetime, date, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

CSV_PATH     = os.path.expanduser("~/morning_log/morning_log.csv")
SESSION_PATH = os.path.expanduser("~/morning_log/session.json")
STATIC_DIR   = Path(__file__).parent          # index.html / style.css / app.js live here
CSV_HEADERS  = ["date", "woke_up", "out_of_bed", "finished_breakfast", "destination", "notes"]
PORT         = 8787

# Static files the browser is allowed to fetch
STATIC_FILES = {
        "/":          ("index.html", "text/html; charset=utf-8"),
        "/style.css": ("style.css",  "text/css; charset=utf-8"),
        "/app.js":    ("app.js",     "application/javascript; charset=utf-8"),
        }


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
        return datetime.fromisoformat(iso).astimezone()

    def hhmm(iso):
        return parse_local(iso).strftime("%H:%M")

    woke_local = parse_local(data["woke_up"])
    row = [
            woke_local.strftime("%Y-%m-%d"),
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
            self._respond(200, "application/json", body)
            return

        if self.path in STATIC_FILES:
            filename, content_type = STATIC_FILES[self.path]
            filepath = STATIC_DIR / filename
            try:
                body = filepath.read_bytes()
                self._respond(200, content_type, body)
            except FileNotFoundError:
                self._json(404, {"ok": False, "error": f"{filename} not found"})
            return

        self._json(404, {"ok": False, "error": "not found"})

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
