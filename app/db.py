"""
db.py
MongoDB connection via PyMongo. Exposes a single `get_db()` function
and typed helpers for each collection.
"""

from pymongo import MongoClient, ASCENDING
from pymongo.server_api import ServerApi
from pymongo.errors import ConnectionFailure
from bson import ObjectId
import os


_client = None


def get_client():
    global _client
    if _client is None:
        uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/spitewise")
        _client = MongoClient(uri, server_api=ServerApi('1'))
        # Verify connection at startup
        try:
            _client.admin.command("ping")
        except ConnectionFailure:
            _client = None
            raise
    return _client


def get_db():
    return get_client().get_default_database()


def ensure_indexes():
    """Call once at app startup to create indexes."""
    db = get_db()
    db.users.create_index([("email", ASCENDING)], unique=True)
    db.groups.create_index([("member_ids", ASCENDING)])
    db.transactions.create_index([("group_id", ASCENDING)])


# ── Convenience helpers ────────────────────────────────────────────────────────

def oid(id_str):
    """Convert a string to ObjectId, returning None if invalid."""
    try:
        return ObjectId(id_str)
    except Exception:
        return None