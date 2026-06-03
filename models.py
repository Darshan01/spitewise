"""
models.py
User model. Thin wrapper around the MongoDB `users` collection.
Flask-Login requires the UserMixin interface.
"""

from flask_login import UserMixin
from bson import ObjectId
from db import get_db


class User(UserMixin):
    def __init__(self, doc):
        self._doc = doc

    # Flask-Login requires get_id() to return a str
    def get_id(self):
        return str(self._doc["_id"])

    @property
    def id(self):
        return str(self._doc["_id"])

    @property
    def email(self):
        return self._doc.get("email", "")

    @property
    def name(self):
        return self._doc.get("name", self.email)

    @property
    def avatar(self):
        return self._doc.get("avatar", "")

    # ── Class-level finders ─────────────────────────────────────────────────

    @classmethod
    def get_by_id(cls, user_id):
        try:
            doc = get_db().users.find_one({"_id": ObjectId(user_id)})
        except Exception:
            return None
        return cls(doc) if doc else None

    @classmethod
    def get_by_email(cls, email):
        doc = get_db().users.find_one({"email": email.lower()})
        return cls(doc) if doc else None

    @classmethod
    def upsert_from_google(cls, google_info):
        """
        Create or update a user from Google OAuth userinfo.
        Returns a User instance.
        """
        email = google_info["email"].lower()
        db = get_db()
        db.users.update_one(
            {"email": email},
            {"$set": {
                "email": email,
                "name": google_info.get("name", email),
                "avatar": google_info.get("picture", ""),
            }},
            upsert=True,
        )
        doc = db.users.find_one({"email": email})
        return cls(doc)

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "avatar": self.avatar,
        }