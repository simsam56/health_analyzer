"""Dépendances partagées pour l'API FastAPI."""

from __future__ import annotations

import sqlite3
from functools import lru_cache
from pathlib import Path

from fastapi import Depends, Header, HTTPException

# Chemin par défaut de la BDD (configurable via env)
DB_PATH = Path("athlete.db")
DASHBOARD_PATH = Path("reports/dashboard.html")
API_TOKEN: str = ""


def get_db() -> sqlite3.Connection:
    """Ouvre une connexion SQLite en lecture seule (WAL mode)."""
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def get_db_rw() -> sqlite3.Connection:
    """Ouvre une connexion SQLite en lecture/écriture."""
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def require_auth(x_performos_token: str = Header(default="")) -> None:
    """Vérifie le token API si configuré."""
    if not API_TOKEN:
        return
    if x_performos_token != API_TOKEN:
        raise HTTPException(status_code=401, detail="unauthorized")


# Cache invalidation flag
_cache_version: int = 0


def invalidate_cache() -> None:
    """Invalide le cache après sync/mise à jour des données."""
    global _cache_version
    _cache_version += 1
    # Clear lru_cache de toutes les fonctions enregistrées
    for fn in _cached_functions:
        fn.cache_clear()


_cached_functions: list = []


def cached(fn):
    """Décorateur : lru_cache avec invalidation globale."""
    wrapped = lru_cache(maxsize=1)(fn)
    _cached_functions.append(wrapped)
    return wrapped
