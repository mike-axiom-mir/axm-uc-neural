#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import mimetypes
import os
import sqlite3
import sys
import threading
import time
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.experiment_controls import read_controls, set_control
from axm_uc.neural_experience_transport import paths as neural_paths, read_jsonl

HTML_PATH = ROOT / "tools" / "uc_neural_dashboard.html"
PRACTICE_APP_ID = 0x41585052
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".svg"}


def _json_file(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _tail(rows: list[dict[str, Any]], amount: int) -> list[dict[str, Any]]:
    return rows[-amount:] if len(rows) > amount else rows


class DashboardState:
    def __init__(self, practice_db: Path | None):
        self.practice_db = practice_db
        self._preview_cache: tuple[float, Path | None] = (0.0, None)

    def _practice(self) -> dict[str, Any]:
        path = self.practice_db
        if path is None or not path.is_file():
            return {
                "attached": False,
                "database": str(path) if path else None,
                "status": "NO_CREATIVE_PRACTICE_DATABASE",
            }
        try:
            connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=1)
            try:
                app_id = connection.execute("PRAGMA application_id").fetchone()[0]
                if app_id != PRACTICE_APP_ID:
                    return {
                        "attached": False,
                        "database": str(path),
                        "status": "NOT_AXM_CREATIVE_PRACTICE",
                    }
                row = connection.execute(
                    "SELECT body FROM sessions ORDER BY rowid DESC LIMIT 1"
                ).fetchone()
                if row is None:
                    return {
                        "attached": False,
                        "database": str(path),
                        "status": "NO_CREATIVE_PRACTICE_SESSION",
                    }
                state = json.loads(row[0])
                return {
                    "attached": True,
                    "database": str(path),
                    "session": state.get("id"),
                    "profile": state.get("profile"),
                    "status": state.get("status"),
                    "trials": state.get("trials"),
                    "active_seconds": state.get("active_seconds"),
                    "max_trials": state.get("max_trials"),
                    "budget_seconds": state.get("budget_seconds"),
                    "current_png": state.get("current_png"),
                }
            finally:
                connection.close()
        except (sqlite3.Error, OSError, json.JSONDecodeError) as exc:
            return {
                "attached": False,
                "database": str(path),
                "status": "HOLD_CREATIVE_PRACTICE_READ",
                "error": str(exc),
            }

    def _control_practice(self, enabled: bool) -> dict[str, Any]:
        practice = self._practice()
        if not practice.get("attached"):
            return practice
        status = practice.get("status")
        session = practice.get("session")
        if status == "closed":
            return practice
        action = "resume" if enabled else "pause"
        if (enabled and status == "active") or (not enabled and status == "paused"):
            return practice
        try:
            from axm_uc.creative_practice import Practice

            with Practice(Path(practice["database"])) as body:
                body.control(str(session), action)
        except Exception as exc:
            return {
                **practice,
                "status": "HOLD_CREATIVE_CONTROL",
                "error": str(exc),
            }
        return self._practice()

    def set_control(self, name: str, value: Any) -> dict[str, Any]:
        controls = set_control(ROOT, name, value)
        practice = self._control_practice(bool(value)) if name == "uc_creative_enabled" else self._practice()
        return {"controls": controls, "creative_practice": practice}

    def status(self) -> dict[str, Any]:
        selected = neural_paths(ROOT)
        controls = read_controls(ROOT)
        events = read_jsonl(selected["events"])
        intake = read_jsonl(selected["intake"])
        start = int(controls.get("neural_link_start_sequence", 0))
        eligible = 0
        latest_sequence = 0
        for row in intake:
            meta = row.get("axm") if isinstance(row.get("axm"), dict) else {}
            sequence = meta.get("sequence")
            if isinstance(sequence, int) and not isinstance(sequence, bool):
                latest_sequence = max(latest_sequence, sequence)
                if sequence > start:
                    eligible += 1

        feeder = _json_file(selected["base"] / "openwaldo-local" / "STATUS.json")
        consumed = 0
        feed_db = selected["base"] / "openwaldo-local" / "feed.sqlite3"
        if feed_db.is_file():
            try:
                connection = sqlite3.connect(f"file:{feed_db}?mode=ro", uri=True, timeout=1)
                try:
                    consumed = int(connection.execute("SELECT COUNT(*) FROM consumed").fetchone()[0])
                finally:
                    connection.close()
            except sqlite3.Error:
                pass

        recent = []
        for row in _tail(events, 24):
            recent.append({
                "sequence": row.get("sequence"),
                "path_id": row.get("path_id"),
                "event": row.get("event"),
                "status": row.get("status"),
                "intake_received": row.get("intake_received"),
            })

        counts: dict[str, int] = {}
        for row in events:
            key = f"{row.get('path_id', 'unknown')}:{row.get('event', 'unknown')}"
            counts[key] = counts.get(key, 0) + 1

        return {
            "schema": "axm.uc-neural-dashboard-status/v1",
            "controls": controls,
            "uc": {
                "coverage": _json_file(selected["coverage"]),
                "event_records": len(events),
                "intake_records": len(intake),
                "latest_sequence": latest_sequence,
                "recent_events": recent,
                "event_counts": counts,
                "creative_practice": self._practice(),
            },
            "neural": {
                "growth": _json_file(selected["neural"]),
                "feeder": feeder,
                "eligible_since_link_boundary": eligible,
                "consumed_records": consumed,
            },
            "preview": self.preview_metadata(),
        }

    def _practice_png(self) -> bytes | None:
        practice = self._practice()
        digest = practice.get("current_png")
        path = self.practice_db
        if not practice.get("attached") or not isinstance(digest, str) or path is None:
            return None
        try:
            connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=1)
            try:
                row = connection.execute("SELECT body FROM blobs WHERE id=?", (digest,)).fetchone()
            finally:
                connection.close()
        except sqlite3.Error:
            return None
        if row and isinstance(row[0], (bytes, bytearray)):
            body = bytes(row[0])
            if body.startswith(b"\x89PNG\r\n\x1a\n"):
                return body
        return None

    def _scan_preview(self) -> Path | None:
        controls = read_controls(ROOT)
        interval = int(controls.get("preview_interval_seconds", 8))
        last_at, cached = self._preview_cache
        if time.monotonic() - last_at < interval:
            return cached
        newest: tuple[float, Path] | None = None
        seen = 0
        roots = [ROOT / "creations", ROOT / ".axm", ROOT / "state" / "neural-experiment"]
        for base in roots:
            if not base.is_dir():
                continue
            for current, dirs, files in os.walk(base):
                dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "openwaldo-local", "__pycache__"}]
                for name in files:
                    seen += 1
                    if seen > 6000:
                        break
                    candidate = Path(current) / name
                    if candidate.suffix.casefold() not in IMAGE_SUFFIXES:
                        continue
                    try:
                        modified = candidate.stat().st_mtime
                    except OSError:
                        continue
                    if newest is None or modified > newest[0]:
                        newest = (modified, candidate)
                if seen > 6000:
                    break
            if seen > 6000:
                break
        selected = newest[1] if newest else None
        self._preview_cache = (time.monotonic(), selected)
        return selected

    def preview_metadata(self) -> dict[str, Any]:
        practice = self._practice()
        if practice.get("attached") and practice.get("current_png"):
            return {
                "kind": "creative-practice-png",
                "label": "Exact current creative-practice PNG",
                "real_pixels": True,
            }
        path = self._scan_preview()
        if path is not None:
            return {
                "kind": "existing-preview",
                "label": f"Newest existing preview: {path.relative_to(ROOT).as_posix()}",
                "real_pixels": True,
            }
        return {
            "kind": "activity-map",
            "label": "Activity map — no native preview is available yet",
            "real_pixels": False,
        }

    def preview(self) -> tuple[bytes, str]:
        body = self._practice_png()
        if body is not None:
            return body, "image/png"
        path = self._scan_preview()
        if path is not None:
            try:
                body = path.read_bytes()
            except OSError:
                body = None
            if body is not None:
                mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
                return body, mime
        return self._activity_svg(), "image/svg+xml; charset=utf-8"

    def _activity_svg(self) -> bytes:
        events = _tail(read_jsonl(neural_paths(ROOT)["events"]), 9)
        rows = []
        for index, event in enumerate(events):
            label = html.escape(f"{event.get('path_id', '?')} · {event.get('event', '?')}")
            received = event.get("intake_received") is True
            width = 180 + min(410, (index + 1) * 36)
            glow = "#73f7ca" if received else "#f2b866"
            rows.append(
                f'<g transform="translate(58 {100 + index * 54})">'
                f'<rect width="{width}" height="31" rx="9" fill="#101a2b" stroke="{glow}" stroke-opacity=".72"/>'
                f'<circle cx="16" cy="15.5" r="5" fill="{glow}"/>'
                f'<text x="31" y="21" fill="#e8f1ff" font-family="system-ui,sans-serif" font-size="14">{label}</text>'
                f'</g>'
            )
        if not rows:
            rows.append('<text x="50%" y="50%" text-anchor="middle" fill="#9fb0c8" font-family="system-ui,sans-serif" font-size="18">No UC experience observed yet</text>')
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="900" height="620" viewBox="0 0 900 620">'
            '<defs><radialGradient id="g"><stop stop-color="#14253e"/><stop offset="1" stop-color="#05080e"/></radialGradient></defs>'
            '<rect width="900" height="620" fill="url(#g)"/>'
            '<text x="50" y="53" fill="#d8e6ff" font-family="system-ui,sans-serif" font-size="23" font-weight="700">UC live activity map</text>'
            '<text x="50" y="78" fill="#788ba8" font-family="system-ui,sans-serif" font-size="13">Diagnostic visualization only — not a rendered UC draft</text>'
            + ''.join(rows)
            + '</svg>'
        )
        return svg.encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    server_version = "AXMExperimentDashboard/1"

    @property
    def state(self) -> DashboardState:
        return self.server.dashboard_state  # type: ignore[attr-defined]

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def _send(self, body: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            try:
                body = HTML_PATH.read_bytes()
            except OSError as exc:
                self._send(str(exc).encode(), "text/plain; charset=utf-8", 500)
                return
            self._send(body, "text/html; charset=utf-8")
            return
        if path == "/api/status":
            body = json.dumps(self.state.status(), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            self._send(body, "application/json; charset=utf-8")
            return
        if path == "/api/preview":
            body, content_type = self.state.preview()
            self._send(body, content_type)
            return
        self._send(b"not found", "text/plain; charset=utf-8", HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/control":
            self._send(b"not found", "text/plain; charset=utf-8", HTTPStatus.NOT_FOUND)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length < 1 or length > 4096:
            self._send(b"invalid body length", "text/plain; charset=utf-8", HTTPStatus.BAD_REQUEST)
            return
        try:
            request = json.loads(self.rfile.read(length))
            if not isinstance(request, dict):
                raise ValueError("body must be an object")
            result = self.state.set_control(str(request.get("name")), request.get("value"))
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self._send(str(exc).encode("utf-8"), "text/plain; charset=utf-8", HTTPStatus.BAD_REQUEST)
            return
        body = json.dumps(result, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self._send(body, "application/json; charset=utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local read-mostly AXM UC/OpenWALDO experiment dashboard")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--practice-db",
        type=Path,
        default=neural_paths(ROOT)["base"] / "creative-practice.sqlite3",
        help="optional AXM creative-practice SQLite cartridge to pause/resume and preview",
    )
    parser.add_argument("--open-browser", action="store_true")
    args = parser.parse_args(argv)
    if args.host not in {"127.0.0.1", "localhost", "::1"}:
        parser.error("dashboard is local-only; bind to loopback")
    if not (1024 <= args.port <= 65535):
        parser.error("--port must be in 1024..65535")

    state = DashboardState(args.practice_db.resolve())
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.dashboard_state = state  # type: ignore[attr-defined]
    url = f"http://127.0.0.1:{args.port}/"
    print(f"AXM experiment dashboard: {url}")
    print("Local-only. Ctrl+C stops the dashboard; it does not stop UC or OpenWALDO.")
    if args.open_browser:
        threading.Timer(0.25, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        print("\nDashboard stopped.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
