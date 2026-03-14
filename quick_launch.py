#!/usr/bin/env python3
"""
Bord — Quick Launcher (bouton bureau macOS)

Lance le backend Python (cockpit_server.py) + le frontend Next.js,
puis ouvre le navigateur sur le Cockpit.
"""

import atexit
import os
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
FRONTEND_DIR = ROOT / "frontend"
DB_PATH = ROOT / "athlete.db"
DASHBOARD_PATH = ROOT / "reports" / "dashboard.html"
BACKEND_PORT = 8765
FRONTEND_PORT = 3000
COCKPIT_URL = f"http://localhost:{FRONTEND_PORT}/cockpit"

processes: list[subprocess.Popen] = []


def cleanup():
    """Arrêter proprement tous les processus enfants."""
    for p in processes:
        try:
            p.terminate()
        except OSError:
            pass
    for p in processes:
        try:
            p.wait(timeout=5)
        except Exception:
            try:
                p.kill()
            except OSError:
                pass


def wait_for(url: str, timeout: int = 30, label: str = "") -> bool:
    """Attendre qu'un URL réponde (max timeout secondes)."""
    for _ in range(timeout * 2):
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except Exception:
            time.sleep(0.5)
    print(f"  Timeout en attendant {label or url}")
    return False


def kill_port(port: int):
    """Libérer un port si occupé (macOS/Linux)."""
    try:
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True, text=True,
        )
        pids = result.stdout.strip().split("\n")
        for pid in pids:
            if pid:
                os.kill(int(pid), signal.SIGTERM)
        if pids and pids[0]:
            time.sleep(1)
    except Exception:
        pass


def ensure_db():
    """Créer la DB démo si elle n'existe pas."""
    if DB_PATH.exists():
        return
    print("  Base de données absente, création de la DB démo...")
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "seed_demo.py")],
        cwd=str(ROOT), check=True,
    )


def ensure_frontend_deps():
    """Installer les deps npm si manquantes."""
    if (FRONTEND_DIR / "node_modules").is_dir():
        return
    print("  Installation des dépendances frontend...")
    subprocess.run(
        ["npm", "install", "--silent"],
        cwd=str(FRONTEND_DIR), check=True,
    )


def main():
    print()
    print("  ╔══════════════════════════════╗")
    print("  ║     B o r d  —  Cockpit      ║")
    print("  ╚══════════════════════════════╝")
    print()

    atexit.register(cleanup)

    # ── Pré-requis ────────────────────────────────────────────
    ensure_db()
    ensure_frontend_deps()

    # ── Libérer les ports ─────────────────────────────────────
    kill_port(BACKEND_PORT)
    kill_port(FRONTEND_PORT)

    # ── Backend Python ────────────────────────────────────────
    print(f"  Backend Python (port {BACKEND_PORT})...")
    backend = subprocess.Popen(
        [
            sys.executable, str(ROOT / "cockpit_server.py"),
            "--dashboard", str(DASHBOARD_PATH),
            "--db", str(DB_PATH),
            "--port", str(BACKEND_PORT),
        ],
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    processes.append(backend)

    if not wait_for(f"http://127.0.0.1:{BACKEND_PORT}/api/artifact",
                    timeout=15, label="backend"):
        print("  Le backend n'a pas demarré.")
        return 1

    print(f"  Backend OK (PID {backend.pid})")

    # ── Frontend Next.js ──────────────────────────────────────
    print(f"  Frontend Next.js (port {FRONTEND_PORT})...")

    # Utiliser le build prod si dispo, sinon dev
    next_bin = str(FRONTEND_DIR / "node_modules" / ".bin" / "next")
    if (FRONTEND_DIR / ".next").is_dir():
        frontend_cmd = [next_bin, "start", "-p", str(FRONTEND_PORT)]
    else:
        frontend_cmd = [next_bin, "dev", "--port", str(FRONTEND_PORT)]

    frontend = subprocess.Popen(
        frontend_cmd,
        cwd=str(FRONTEND_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    processes.append(frontend)

    if not wait_for(f"http://127.0.0.1:{FRONTEND_PORT}",
                    timeout=30, label="frontend"):
        print("  Le frontend n'a pas demarré.")
        return 1

    print(f"  Frontend OK (PID {frontend.pid})")

    # ── Ouvrir le navigateur ──────────────────────────────────
    print()
    print(f"  Bord est pret !")
    print(f"  -> {COCKPIT_URL}")
    print()
    print("  Ctrl+C pour tout arreter.")
    print()

    try:
        subprocess.run(["open", COCKPIT_URL], check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        # Linux
        try:
            subprocess.run(["xdg-open", COCKPIT_URL], check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            pass

    # ── Attendre Ctrl+C ───────────────────────────────────────
    try:
        backend.wait()
    except KeyboardInterrupt:
        print("\n  Arret...")

    return 0


if __name__ == "__main__":
    sys.exit(main())
