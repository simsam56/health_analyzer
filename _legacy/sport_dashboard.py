#!/usr/bin/env python3
"""
Compat wrapper legacy.

Ce script redirige vers `main.py` (PerformOS v3) pour éviter la rupture
avec les anciennes commandes/scripts qui appellent encore sport_dashboard.py.
"""

from main import main as run_v3

if __name__ == "__main__":
    print("ℹ️  sport_dashboard.py est déprécié, redirection vers main.py (v3)…")
    run_v3()
