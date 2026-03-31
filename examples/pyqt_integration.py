"""
examples/pyqt_integration.py — Exemple d'intégration BON dans une application PyQt5/PyQt6
============================================================================================

Montre comment :
  1. Lancer le module BON en subprocess isolé
  2. Lire les logs JSON Lines en temps réel (QThread)
  3. Arrêter proprement le module (SIGTERM cross-platform)
  4. Afficher les événements dans un QTextEdit coloré

Prérequis :
    pip install PyQt5   # ou PyQt6 — adapter les imports ci-dessous

Usage :
    python examples/pyqt_integration.py
"""

import sys
import os
import json
import signal
import pathlib
import subprocess

# ── Adapter selon la version PyQt installée ────────────────────────────────────
try:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout,
        QHBoxLayout, QPushButton, QTextEdit, QLabel, QComboBox
    )
    from PyQt5.QtCore import QThread, pyqtSignal, QTimer
    from PyQt5.QtGui import QColor, QTextCursor, QFont
except ImportError:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout,
        QHBoxLayout, QPushButton, QTextEdit, QLabel, QComboBox
    )
    from PyQt6.QtCore import QThread, pyqtSignal, QTimer
    from PyQt6.QtGui import QColor, QTextCursor, QFont

# Répertoire de logs BON (cross-platform)
if sys.platform == "win32":
    _BON_BASE = pathlib.Path.home() / "AppData" / "Roaming" / "bon"
elif sys.platform == "darwin":
    _BON_BASE = pathlib.Path.home() / "Library" / "Application Support" / "bon"
else:
    _BON_BASE = pathlib.Path.home() / ".config" / "bon"

LOG_FILE  = _BON_BASE / "logs" / "activity.jsonl"
PID_FILE  = _BON_BASE / "logs" / "running.pid"
SESSIONS_DIR = _BON_BASE / "sessions"

# Couleurs par niveau de log
LOG_COLORS = {
    "DEBUG":   "#64748B",
    "INFO":    "#1D4ED8",
    "SUCCESS": "#059669",
    "WARN":    "#D97706",
    "ERROR":   "#DC2626",
}


# ── Thread de lecture des logs ─────────────────────────────────────────────────

class LogWatcher(QThread):
    """Lit activity.jsonl en temps réel et émet chaque nouvelle ligne."""
    new_line = pyqtSignal(dict)

    def __init__(self, log_path: pathlib.Path):
        super().__init__()
        self.log_path = log_path
        self._running = True

    def run(self):
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_path.touch(exist_ok=True)
        with open(self.log_path, "r", encoding="utf-8") as f:
            f.seek(0, 2)  # aller à la fin — ignorer les anciens logs
            while self._running:
                line = f.readline()
                if line.strip():
                    try:
                        self.new_line.emit(json.loads(line))
                    except json.JSONDecodeError:
                        pass
                else:
                    self.msleep(250)

    def stop(self):
        self._running = False
        self.wait(2000)


# ── Fenêtre principale ─────────────────────────────────────────────────────────

class BonWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("BON — Facebook Groups Publisher")
        self.setMinimumSize(800, 500)
        self._process: subprocess.Popen | None = None
        self._log_watcher: LogWatcher | None = None

        self._build_ui()
        self._start_log_watcher()
        self._refresh_sessions()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 12, 12, 12)

        # Ligne 1 : sélecteur de session + boutons
        top = QHBoxLayout()
        top.addWidget(QLabel("Session :"))
        self.session_combo = QComboBox()
        self.session_combo.setMinimumWidth(160)
        top.addWidget(self.session_combo)

        self.btn_post       = QPushButton("▶  Publier (1 image)")
        self.btn_post_multi = QPushButton("▶  Publier (multi-images)")
        self.btn_marketplace = QPushButton("▶  Marketplace")
        self.btn_stop       = QPushButton("⏹  Arrêter")
        self.btn_stop.setEnabled(False)

        for btn in (self.btn_post, self.btn_post_multi, self.btn_marketplace, self.btn_stop):
            top.addWidget(btn)
        top.addStretch()
        layout.addLayout(top)

        # Ligne 2 : log viewer
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFont(QFont("Courier New", 9))
        layout.addWidget(self.log_view)

        # Status bar
        self.status = QLabel("Prêt.")
        layout.addWidget(self.status)

        # Connexions
        self.btn_post.clicked.connect(lambda: self._run("post"))
        self.btn_post_multi.clicked.connect(lambda: self._run("post-multi"))
        self.btn_marketplace.clicked.connect(lambda: self._run("marketplace"))
        self.btn_stop.clicked.connect(self._stop_module)

    def _refresh_sessions(self):
        """Recharge la liste des sessions disponibles."""
        self.session_combo.clear()
        if SESSIONS_DIR.exists():
            sessions = sorted(
                p.stem.replace("_state", "")
                for p in SESSIONS_DIR.glob("*_state.json")
            )
            self.session_combo.addItems(sessions)
        if self.session_combo.count() == 0:
            self.session_combo.addItem("(aucune session — lancez: python -m bon login)")

    def _start_log_watcher(self):
        """Démarre le thread de lecture des logs en arrière-plan."""
        self._log_watcher = LogWatcher(LOG_FILE)
        self._log_watcher.new_line.connect(self._on_log_line)
        self._log_watcher.start()

    def _run(self, command: str):
        """Lance le module BON en subprocess avec la session sélectionnée."""
        session = self.session_combo.currentText()
        if "(aucune" in session:
            self._append_log({"level": "ERROR", "event": "NO_SESSION",
                              "msg": "Créez une session d'abord."})
            return

        # Construire la commande
        python = sys.executable
        cmd = [python, "-m", "bon", command, "--session", session]

        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=pathlib.Path(__file__).parent.parent,  # répertoire du module
        )
        self.btn_stop.setEnabled(True)
        for b in (self.btn_post, self.btn_post_multi, self.btn_marketplace):
            b.setEnabled(False)
        self.status.setText(f"Module en cours — PID {self._process.pid}")
        self._append_log({"level": "INFO", "event": "SUBPROCESS_STARTED",
                          "command": command, "session": session,
                          "pid": self._process.pid})

        # Vérifier la fin du process toutes les 500ms
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._check_process)
        self._poll_timer.start(500)

    def _check_process(self):
        """Vérifie si le subprocess est terminé."""
        if self._process and self._process.poll() is not None:
            code = self._process.returncode
            self._poll_timer.stop()
            self._process = None
            self.btn_stop.setEnabled(False)
            for b in (self.btn_post, self.btn_post_multi, self.btn_marketplace):
                b.setEnabled(True)
            self.status.setText(f"Terminé (code {code}).")
            self._append_log({"level": "SUCCESS" if code == 0 else "WARN",
                              "event": "SUBPROCESS_ENDED", "returncode": code})

    def _stop_module(self):
        """Arrête proprement le module BON (SIGTERM cross-platform)."""
        if not self._process:
            return
        try:
            # Lire le PID depuis le fichier si disponible (plus fiable)
            if PID_FILE.exists():
                pid = int(PID_FILE.read_text().strip())
            else:
                pid = self._process.pid

            if sys.platform == "win32":
                self._process.terminate()  # SIGTERM équivalent sur Windows
            else:
                os.kill(pid, signal.SIGTERM)

            self._append_log({"level": "INFO", "event": "STOP_REQUESTED", "pid": pid})
        except Exception as e:
            self._append_log({"level": "WARN", "event": "STOP_ERROR", "error": str(e)})

    def _on_log_line(self, data: dict):
        """Appelé par LogWatcher pour chaque nouvelle ligne de log."""
        self._append_log(data)

    def _append_log(self, data: dict):
        """Affiche une ligne de log dans le QTextEdit avec coloration."""
        level  = data.get("level", "INFO")
        event  = data.get("event", "")
        ts     = data.get("ts", "")
        color  = LOG_COLORS.get(level, "#1D4ED8")

        # Construire les champs supplémentaires
        extra = {k: v for k, v in data.items()
                 if k not in ("level", "event", "ts")}
        extra_str = "  ".join(f"{k}={v}" for k, v in extra.items())

        line = f"[{ts[-8:] if ts else '--:--:--'}] {level:<7} {event}"
        if extra_str:
            line += f"  {extra_str}"

        cursor = self.log_view.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        fmt = cursor.charFormat()
        fmt.setForeground(QColor(color))
        cursor.setCharFormat(fmt)
        cursor.insertText(line + "\n")
        self.log_view.setTextCursor(cursor)
        self.log_view.ensureCursorVisible()

    def closeEvent(self, event):
        """Nettoyage propre à la fermeture."""
        self._stop_module()
        if self._log_watcher:
            self._log_watcher.stop()
        event.accept()


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BonWindow()
    window.show()
    sys.exit(app.exec())
