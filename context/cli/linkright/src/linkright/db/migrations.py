"""`linkright init` — bootstrap MongoDB database + filesystem layout.

Idempotent: safe to re-run.
"""
from __future__ import annotations

import logging

from pymongo.errors import CollectionInvalid, OperationFailure

from ..config import Config
from .collections import COLLECTIONS, VECTOR_COLLECTIONS
from .mongo import get_db, ping

logger = logging.getLogger(__name__)


def _ensure_indices(db) -> None:
    for name in COLLECTIONS:
        coll = db[name]
        coll.create_index([("user_id", 1), ("created_at", -1)])
        coll.create_index("updated_at")

    db["jds"].create_index("jd_hash", unique=True)
    db["evaluations"].create_index([("user_id", 1), ("jd_hash", 1)])
    db["applications"].create_index([("user_id", 1), ("status", 1)])
    db["runs"].create_index([("user_id", 1), ("pillar", 1), ("created_at", -1)])
    db["predicted_questions"].create_index("interview_id")
    db["mock_sessions"].create_index("interview_id")
    db["career_stories"].create_index([("user_id", 1), ("title", 1)])
    db["career_stories"].create_index([("user_id", 1), ("tags", 1)])
    db["career_stories"].create_index([("user_id", 1), ("jd_requirement_ids", 1)])
    db["career_stories"].create_index([("user_id", 1), ("last_used_at", -1)])
    db["content_items"].create_index([("user_id", 1), ("status", 1), ("scheduled_for", 1)])


def _ensure_vector_indices(db) -> None:
    """Create Atlas Search / Mongo Search vector indices. Log + skip on unsupported CE."""
    for coll_name, field in VECTOR_COLLECTIONS.items():
        coll = db[coll_name]
        idx = {
            "name": "vector_index",
            "type": "vectorSearch",
            "definition": {
                "fields": [
                    {"type": "vector", "path": field, "numDimensions": 768, "similarity": "cosine"},
                ]
            },
        }
        try:
            coll.create_search_index(idx)
            logger.info("vector_index created on %s.%s", coll_name, field)
        except (OperationFailure, AttributeError, Exception) as e:  # noqa: BLE001
            logger.info(
                "vector_index not created on %s (%s). Python cosine fallback will be used.",
                coll_name, type(e).__name__,
            )


def init(verbose: bool = True) -> dict:
    """Bootstrap ~/.linkright/ dirs + MongoDB collections/indices.

    Returns a status dict with what was done / skipped.
    """
    cfg = Config.load()
    if not CONFIG_saved_(cfg):
        cfg.save()

    for d in (cfg.profile_dir(), cfg.runs_dir(), cfg.work_dir(), cfg.cache_dir()):
        d.mkdir(parents=True, exist_ok=True)

    status = {
        "config_path": str(cfg.__class__.__module__),
        "home": str(cfg.profile_dir().parent),
        "mongo_ok": ping(),
        "collections": [],
        "vector_indices": "attempted",
    }

    if not status["mongo_ok"]:
        status["warning"] = (
            f"MongoDB unreachable at {cfg.mongo_uri}. "
            "Install MongoDB 8 CE and ensure mongod is running on localhost:27017."
        )
        return status

    db = get_db()
    for name in COLLECTIONS:
        try:
            db.create_collection(name)
            status["collections"].append(f"created:{name}")
        except CollectionInvalid:
            status["collections"].append(f"exists:{name}")

    _ensure_indices(db)
    _ensure_vector_indices(db)

    if verbose:
        logger.info("linkright init: %s", status)
    return status


def CONFIG_saved_(cfg: Config) -> bool:
    """Check if config.yaml already exists on disk."""
    from ..config import CONFIG_PATH
    return CONFIG_PATH.exists()
