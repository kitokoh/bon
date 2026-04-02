"""
rest_api.py v11 — API REST Flask pour supervision et intégrations (n8n, Make, etc.).

Sécurité : Authorization: Bearer <token>  (sauf /health et /api/v1/health)
Variable : BON_API_TOKEN (obligatoire)

Préfixes supportés : /v1/... et /api/v1/... (alias identiques pour compatibilité documentation / audit).
"""
from __future__ import annotations

import csv
import io
import os
import pathlib
import subprocess
import sys
from typing import Optional

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

_PATHS_PUBLIC = frozenset({"/health", "/api/v1/health"})


def create_app(token: Optional[str] = None):
    try:
        from flask import Flask, Response, abort, jsonify, request, send_file
    except ImportError as e:
        raise RuntimeError("Installez flask : pip install flask") from e

    app = Flask(__name__)
    expected = (token or os.environ.get("BON_API_TOKEN", "")).strip()
    if not expected:
        raise RuntimeError("BON_API_TOKEN requis pour démarrer l’API")

    @app.before_request
    def _auth():
        if request.path in _PATHS_PUBLIC:
            return None
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            abort(401)
        if auth[7:].strip() != expected:
            abort(403)

    def _health():
        return jsonify({"status": "ok", "service": "bon", "version": 11})

    app.add_url_rule("/health", "health", _health, methods=["GET"])
    app.add_url_rule("/api/v1/health", "health_api", _health, methods=["GET"])

    def _robots_list():
        from libs.database import get_database
        return jsonify({"robots": get_database().get_all_robots()})

    app.add_url_rule("/v1/robots", "robots", _robots_list, methods=["GET"])
    app.add_url_rule("/api/v1/robots", "robots_api", _robots_list, methods=["GET"])

    def _robot_one(name: str):
        from libs.database import get_database
        r = get_database().get_robot(name)
        if not r:
            abort(404)
        out = {k: v for k, v in r.items() if "password" not in k.lower()}
        return jsonify(out)

    app.add_url_rule("/v1/robots/<name>", "robot_one", _robot_one, methods=["GET"])
    app.add_url_rule("/api/v1/robots/<name>", "robot_one_api", _robot_one, methods=["GET"])

    def _dashboard():
        from libs.database import get_database
        return jsonify(get_database().get_dashboard_stats())

    app.add_url_rule("/v1/dashboard", "dashboard", _dashboard, methods=["GET"])
    app.add_url_rule("/api/v1/dashboard", "dashboard_api", _dashboard, methods=["GET"])

    def _publications():
        from libs.database import get_database
        robot = request.args.get("robot") or None
        limit = min(int(request.args.get("limit", 50)), 500)
        offset = int(request.args.get("offset", 0))
        rows = get_database().get_publications_paginated(
            limit=limit, offset=offset, robot_name=robot
        )
        return jsonify({"count": len(rows), "items": rows})

    app.add_url_rule("/v1/publications", "publications", _publications, methods=["GET"])
    app.add_url_rule("/api/v1/publications", "publications_api", _publications, methods=["GET"])

    def _publications_export():
        from libs.database import get_database
        fmt = (request.args.get("format") or "csv").strip().lower()
        robot = request.args.get("robot") or None
        db = get_database()
        if fmt == "xlsx":
            try:
                buf = io.BytesIO()
                db.export_publications_xlsx(buf, robot_name=robot)
                buf.seek(0)
                return send_file(
                    buf,
                    as_attachment=True,
                    download_name="bon_publications.xlsx",
                    mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            except ImportError as e:
                return jsonify({"error": str(e)}), 501
        si = io.StringIO()
        rows = db._publication_export_rows(robot)
        fieldnames = [
            "id", "robot_name", "account", "group_url",
            "campaign_name", "variant_id", "status", "created_at", "error_message",
        ]
        w = csv.DictWriter(si, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            row = dict(r)
            w.writerow({k: row.get(k) for k in fieldnames})
        data = "\ufeff" + si.getvalue()
        return Response(
            data.encode("utf-8"),
            mimetype="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": "attachment; filename=bon_publications.csv",
            },
        )

    app.add_url_rule(
        "/v1/publications/export", "pub_export", _publications_export, methods=["GET"]
    )
    app.add_url_rule(
        "/api/v1/publications/export", "pub_export_api", _publications_export, methods=["GET"]
    )

    def _campaigns():
        from libs.database import get_database
        return jsonify({"campaigns": get_database().get_all_campaigns()})

    app.add_url_rule("/v1/campaigns", "campaigns", _campaigns, methods=["GET"])
    app.add_url_rule("/api/v1/campaigns", "campaigns_api", _campaigns, methods=["GET"])

    def _groups():
        from libs.database import get_database
        db = get_database()
        robot = request.args.get("robot") or None
        if robot:
            return jsonify({"groups": db.get_groups_for_robot(robot)})
        return jsonify({"groups": db.get_all_groups()})

    app.add_url_rule("/v1/groups", "groups", _groups, methods=["GET"])
    app.add_url_rule("/api/v1/groups", "groups_api", _groups, methods=["GET"])

    def _errors():
        from libs.database import get_database
        limit = min(int(request.args.get("limit", 50)), 200)
        return jsonify({"errors": get_database().get_recent_errors(limit)})

    app.add_url_rule("/v1/errors", "errors", _errors, methods=["GET"])
    app.add_url_rule("/api/v1/errors", "errors_api", _errors, methods=["GET"])

    def _sched_jobs():
        from libs.database import get_database
        return jsonify({"jobs": get_database().scheduler_list_jobs()})

    app.add_url_rule("/v1/scheduler/jobs", "sched", _sched_jobs, methods=["GET"])
    app.add_url_rule("/api/v1/scheduler/jobs", "sched_api", _sched_jobs, methods=["GET"])

    def _captcha_stats():
        from libs.database import get_database
        days = int(request.args.get("days", 7))
        return jsonify({"stats": get_database().get_captcha_solve_stats(days)})

    app.add_url_rule("/v1/captcha/stats", "captcha", _captcha_stats, methods=["GET"])
    app.add_url_rule("/api/v1/captcha/stats", "captcha_api", _captcha_stats, methods=["GET"])

    def _robot_run(name: str):
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

    app.add_url_rule(
        "/v1/robots/<name>/run", "robot_run", _robot_run, methods=["POST"]
    )
    app.add_url_rule(
        "/api/v1/robots/<name>/run", "robot_run_api", _robot_run, methods=["POST"]
    )

    return app


def run(host: str = "127.0.0.1", port: int = 8765, token: Optional[str] = None):
    app = create_app(token=token)
    app.run(host=host, port=port, threaded=True)
