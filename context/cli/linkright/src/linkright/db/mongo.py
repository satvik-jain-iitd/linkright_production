"""MongoDB client singleton.

Reads connection config from `~/.linkright/config.yaml` (or env).
Lazy-initialized; closed on process exit.
"""
from __future__ import annotations

from typing import Optional

from pymongo import MongoClient
from pymongo.database import Database

from ..config import Config


_client: Optional[MongoClient] = None
_db_name: Optional[str] = None


def get_client() -> MongoClient:
    global _client, _db_name
    if _client is None:
        cfg = Config.load()
        _client = MongoClient(cfg.mongo_uri, serverSelectionTimeoutMS=3000)
        _db_name = cfg.mongo_db
    return _client


def get_db(name: Optional[str] = None) -> Database:
    client = get_client()
    return client[name or _db_name or "linkright"]


def close_client() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


def ping() -> bool:
    """Cheap liveness check. Returns False if Mongo is unreachable."""
    try:
        client = get_client()
        client.admin.command("ping")
        return True
    except Exception:
        return False
