"""
rest_api.py v11 — API REST minimale (Flask) pour supervision.

Sécurité : en-tête  Authorization: Bearer <token>
Variable : BON_API_TOKEN (obligatoire pour démarrer l’API)

Endpoints :
  GET  /health
  GET  /v1/robots
  GET  /v1/robots/<name>
  GET  /v1/dashboard
  GET  /v1/publications?robot=&limit=&offset=
  GET  /v1/scheduler/jobs
  GET  /v1/captcha/stats
  POST /v1/robots/<name>/run  JSON {"command":"post","headless":true}  (sous-processus)
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys
from typing import Optional

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


def create_app(token: Optional[str] = None):
    try:
        from flask import Flask, jsonify, request, abort
    except ImportError as e:
        raise RuntimeError("Installez flask : pip install flask") from e

    app = Flask(__name__)
    expected = (token or os.environ.get("BON_API_TOKEN", "")).strip()
    if not expected:
        raise RuntimeError("BON_API_TOKEN requis pour démarrer l’API")

    @app.before_request
    def _auth():
        if request.path == "/health":
            return None
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            abort(401)
        got = auth[7:].strip()
        if got != expected:
            abort(403)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "service": "bon", "version": 11})

    @app.get("/v1/robots")
    def robots_list():
        from libs.database import get_database
        db = get_database()
        return jsonify({"robots": db.get_all_robots()})

    @app.get("/v1/robots/<name>")
    def robot_one(name: str):
        from libs.database import get_database
        r = get_database().get_robot(name)
        if not r:
            abort(404)
        out = {k: v for k, v in r.items() if "password" not in k.lower()}
        return jsonify(out)

    @app.get("/v1/dashboard")
    def dashboard():
        from libs.database import get_database
        return jsonify(get_database().get_dashboard_stats())

    @app.get("/v1/publications")
    def publications():
        from libs.database import get_database
        robot = request.args.get("robot") or None
        limit = min(int(request.args.get("limit", 50)), 500)
        offset = int(request.args.get("offset", 0))
        rows = get_database().get_publications_paginated(
            limit=limit, offset=offset, robot_name=robot
        )
        return jsonify({"count": len(rows), "items": rows})

    @app.get("/v1/scheduler/jobs")
    def sched_jobs():
        from libs.database import get_database
        return jsonify({"jobs": get_database().scheduler_list_jobs()})

    @app.get("/v1/captcha/stats")
    def captcha_stats():
        from libs.database import get_database
        return jsonify({"stats": get_database().get_captcha_solve_stats(30)})

    @app.post("/v1/robots/<name>/run")
    def robot_run(name: str):
        from libs.database import get_database
        if not get_database().get_robot(name):
            abort(404)
        body = request.get_json(silent=True) or {}
        cmd = (body.get("command") or "post").strip()
        headless = bool(body.get("headless", True))
        argv = [sys.executable, str(REPO_ROOT / "__main__.py"), cmd, "--robot", name]
        if cmd == "post" and headless:
            argv.append("--headless")
        subprocess.Popen(
            argv,
            cwd=str(REPO_ROOT),
            close_fds=sys.platform != "win32",
        )
        return jsonify({"started": True, "command": cmd, "robot": name})

    return app


def run(host: str = "127.0.0.1", port: int = 8765, token: Optional[str] = None):
    app = create_app(token=token)
    app.run(host=host, port=port, threaded=True)
